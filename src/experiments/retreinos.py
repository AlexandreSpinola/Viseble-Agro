"""C3 (ablação por grupo de features) e C5 (variabilidade entre seeds).

Cada configuração retreina a LSTM com a mesma arquitetura e o mesmo protocolo
de src/models/lstm.py (early stopping na validação), mudando só o conjunto de
features e/ou a semente. Métricas na validação. Nada é salvo em models/.

Uso:  python -m src.experiments.retreinos
Saída: reports/experimentos/c3_ablacao.csv, c5_seeds.csv
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.models import dataset as ds
from src.models.lstm import build_model
from src.models.predict import forecast_batch  # noqa: F401 (garante import do pacote)

OUT = Path(__file__).resolve().parents[2] / "reports" / "experimentos"

GRUPOS = {
    "a_retornos_ma": ["ret_arabica_1d", "ret_arabica_21d", "ret_robusta_1d", "ret_ice_1d", "ret_ptax_1d",
                      "preco_vs_ma_1m", "preco_vs_ma_3m", "preco_vs_ma_1a", "preco_vs_ma_2a"],
    "b_mercado": ["vol_21d", "spread_arabica_robusta", "base_fisico_futuro_pct"],
    "c_calendario_selic": ["mes_sin", "mes_cos", "bienalidade_alta", "selic_meta"],
    "d_clima": ["chuva_arabica_30d", "chuva_arabica_90d", "tmin_arabica_7d", "geada_30d", "chuva_robusta_90d"],
    "e_cot": ["cot_net_pct_oi", "cot_net_pct_oi_chg4w"],
    "f_insumos": ["indice_troca_urea", "ret_urea_1a", "ret_crude_1a"],
}
FEATURES_COMPLETO = list(ds.FEATURES)


def treinar_avaliar(features: list[str], seed: int, epochs: int = 100) -> dict:
    import keras
    from sklearn.preprocessing import StandardScaler
    from src.features.build_features import chronological_split

    keras.utils.set_random_seed(seed)
    ds.FEATURES = features                       # make_sequences lê o global
    df = pd.read_csv(ds.PROCESSED / "dataset_diario.csv", index_col="date", parse_dates=True)
    splits = chronological_split(df)
    scaler = StandardScaler().fit(splits["train"][features])
    Xtr, ytr, _ = ds.make_sequences(df, splits["train"].index, scaler)
    Xva, yva, _ = ds.make_sequences(df, splits["val"].index, scaler)

    model = build_model(n_features=len(features))
    cbs = [keras.callbacks.EarlyStopping(monitor="val_loss", patience=15, restore_best_weights=True),
           keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=7, verbose=0)]
    t0 = time.time()
    hist = model.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=epochs, batch_size=32, callbacks=cbs, verbose=0)
    dt = time.time() - t0
    pred = model.predict(Xva, verbose=0)
    out = {"seed": seed, "n_features": len(features), "epocas": len(hist.history["loss"]), "tempo_s": round(dt, 1)}
    for i, h in enumerate(ds.HORIZONS):
        err = pred[:, i] - yva[:, i]
        out[f"rmse_{h}d"] = float(np.sqrt(np.mean(err ** 2)))
        out[f"mae_{h}d"] = float(np.mean(np.abs(err)))
        out[f"dir_{h}d"] = float(np.mean(np.sign(pred[:, i]) == np.sign(yva[:, i])) * 100)
    return out


def main(seeds_ablacao=(42, 43, 44), seeds_completo=(42, 43, 44, 45, 46)):
    OUT.mkdir(parents=True, exist_ok=True)
    # --- C5: modelo completo, 5 seeds
    linhas = []
    for s in seeds_completo:
        r = treinar_avaliar(FEATURES_COMPLETO, s); r["config"] = "completo"; linhas.append(r)
        print("C5", r, flush=True)
        pd.DataFrame(linhas).to_csv(OUT / "c5_seeds.csv", index=False)
    completo = pd.DataFrame(linhas)

    # --- C3: remove um grupo por vez, 3 seeds
    linhas = [r for r in completo.to_dict("records") if r["seed"] in seeds_ablacao]
    for nome, grupo in GRUPOS.items():
        feats = [f for f in FEATURES_COMPLETO if f not in grupo]
        for s in seeds_ablacao:
            r = treinar_avaliar(feats, s); r["config"] = f"sem_{nome}"; linhas.append(r)
            print("C3", r, flush=True)
            pd.DataFrame(linhas).to_csv(OUT / "c3_ablacao.csv", index=False)
    ds.FEATURES = FEATURES_COMPLETO
    print("concluído")


if __name__ == "__main__":
    main()
