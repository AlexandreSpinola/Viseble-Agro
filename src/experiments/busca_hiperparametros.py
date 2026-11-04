"""Busca de hiperparâmetros da LSTM (grade pequena, seed 42, validação).

Varia unidades, dropout, janela (LOOKBACK) e taxa de aprendizado, um fator por
vez a partir da configuração base, e combinações selecionadas. Nada é salvo em models/.

Uso: python -m src.experiments.busca_hiperparametros
Saída: reports/experimentos/hp_busca.csv
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.models import dataset as ds

OUT = Path(__file__).resolve().parents[2] / "reports" / "experimentos"

BASE = dict(units=64, dropout=0.2, lookback=63, lr=1e-3, batch=32)
GRADE = [
    BASE,
    {**BASE, "units": 32}, {**BASE, "units": 128},
    {**BASE, "dropout": 0.0}, {**BASE, "dropout": 0.4},
    {**BASE, "lookback": 21}, {**BASE, "lookback": 126},
    {**BASE, "lr": 3e-4}, {**BASE, "lr": 3e-3},
    {**BASE, "batch": 64},
    {**BASE, "units": 32, "dropout": 0.4},            # candidata enxuta (anti-sobreajuste)
    {**BASE, "units": 32, "dropout": 0.4, "lookback": 126},
]


def rodar(cfg: dict, seed: int = 42) -> dict:
    import keras
    from keras import layers
    from sklearn.preprocessing import StandardScaler
    from src.features.build_features import chronological_split

    keras.utils.set_random_seed(seed)
    ds.LOOKBACK = cfg["lookback"]
    df = pd.read_csv(ds.PROCESSED / "dataset_diario.csv", index_col="date", parse_dates=True)
    sp = chronological_split(df)
    sc = StandardScaler().fit(sp["train"][ds.FEATURES])
    Xtr, ytr, _ = ds.make_sequences(df, sp["train"].index, sc)
    Xva, yva, _ = ds.make_sequences(df, sp["val"].index, sc)
    u = cfg["units"]
    model = keras.Sequential([layers.Input(shape=(cfg["lookback"], len(ds.FEATURES))),
                              layers.LSTM(u, return_sequences=True), layers.Dropout(cfg["dropout"]),
                              layers.LSTM(u // 2), layers.Dropout(cfg["dropout"]),
                              layers.Dense(32, activation="relu"), layers.Dense(3)])
    model.compile(optimizer=keras.optimizers.Adam(cfg["lr"]), loss="mse")
    cbs = [keras.callbacks.EarlyStopping(monitor="val_loss", patience=15, restore_best_weights=True),
           keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=7, verbose=0)]
    t0 = time.time()
    h = model.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=100, batch_size=cfg["batch"], callbacks=cbs, verbose=0)
    pred = model.predict(Xva, verbose=0)
    out = {**cfg, "epocas": len(h.history["loss"]), "tempo_s": round(time.time() - t0, 1),
           "rmse_treino": float(np.sqrt(min(h.history["loss"])))}
    for i, hz in enumerate(ds.HORIZONS):
        e = pred[:, i] - yva[:, i]
        out[f"rmse_{hz}d"] = float(np.sqrt(np.mean(e ** 2)))
        out[f"dir_{hz}d"] = float(np.mean(np.sign(pred[:, i]) == np.sign(yva[:, i])) * 100)
    out["rmse_medio"] = float(np.mean([out[f"rmse_{hz}d"] for hz in ds.HORIZONS]))
    return out


def main():
    linhas = []
    for cfg in GRADE:
        r = rodar(cfg); linhas.append(r); print(r, flush=True)
        pd.DataFrame(linhas).round(4).to_csv(OUT / "hp_busca.csv", index=False)
    ds.LOOKBACK = 63
    print("concluído")


if __name__ == "__main__":
    main()
