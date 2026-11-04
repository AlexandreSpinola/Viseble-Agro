"""Treino e avaliação da LSTM multi-horizonte.

Uso:
    python -m src.models.lstm
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.models.dataset import HORIZONS, LOOKBACK, FEATURES, MODELS, prepare_splits

SEED = 42


def build_model(n_features: int = len(FEATURES), lookback: int = LOOKBACK,
                units: int = 32, dropout: float = 0.4) -> "keras.Model":
    import keras
    from keras import layers

    model = keras.Sequential([
        layers.Input(shape=(lookback, n_features)),
        layers.LSTM(units, return_sequences=True),
        layers.Dropout(dropout),
        layers.LSTM(units // 2),
        layers.Dropout(dropout),
        layers.Dense(32, activation="relu"),
        layers.Dense(len(HORIZONS)),
    ])
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse", metrics=["mae"])
    return model


def train(data: dict | None = None, epochs: int = 100, batch_size: int = 32,
          verbose: int = 2) -> tuple["keras.Model", dict, "keras.callbacks.History"]:
    import keras

    keras.utils.set_random_seed(SEED)
    if data is None:
        data = prepare_splits()

    model = build_model()
    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=15, restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=7, verbose=verbose),
    ]
    history = model.fit(
        data["train"]["X"], data["train"]["y"],
        validation_data=(data["val"]["X"], data["val"]["y"]),
        epochs=epochs, batch_size=batch_size, callbacks=callbacks, verbose=verbose,
    )
    model.save(MODELS / "lstm_multihorizonte.keras")
    return model, data, history


def evaluate(model, split: dict, df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Métricas por horizonte vs. dois baselines:
    - ingênuo: passeio aleatório (retorno previsto = 0);
    - curva: previsão implícita no mercado futuro + base sazonal (o que um
      produtor com acesso à B3 já tem de graça; é o baseline relevante).

    Reporta erro no espaço de log-retorno e o erro percentual equivalente no
    preço reconstruído."""
    pred = model.predict(split["X"], verbose=0)
    curva = None
    if df is not None:
        from src.decision.hedge import previsao_implicita
        curva = previsao_implicita(df, split["dates"])
    rows = []
    for i, h in enumerate(HORIZONS):
        y = split["y"][:, i]
        err = pred[:, i] - y
        row = {
            "horizonte": f"{h}d",
            "rmse_ret": float(np.sqrt(np.mean(err ** 2))),
            "mae_ret": float(np.mean(np.abs(err))),
            "rmse_naive": float(np.sqrt(np.mean(y ** 2))),
            "mape_preco_%": float(np.mean(np.abs(np.expm1(err))) * 100),
            "acerto_direcao_%": float(np.mean(np.sign(pred[:, i]) == np.sign(y)) * 100),
        }
        if curva is not None:
            yc = curva[f"y_{h}d"].to_numpy()
            row["rmse_curva"] = float(np.sqrt(np.mean((yc - y) ** 2)))
            row["acerto_direcao_curva_%"] = float(np.mean(np.sign(yc) == np.sign(y)) * 100)
        rows.append(row)
    return pd.DataFrame(rows).set_index("horizonte")


if __name__ == "__main__":
    model, data, history = train()
    print("\nValidação:")
    print(evaluate(model, data["val"], data["df"]).round(4))
