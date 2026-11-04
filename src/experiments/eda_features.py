"""Análise exploratória das features: correlação com o alvo por horizonte,
matriz de correlação entre features e importância por permutação na LSTM.

Uso: python -m src.experiments.eda_features
Saída: reports/experimentos/eda_corr_alvo.csv, eda_importancia_permutacao.csv,
       reports/figures/10_corr_features_alvo.png, 11_matriz_corr_features.png,
       12_importancia_permutacao.png
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.models.dataset import FEATURES, HORIZONS, PROCESSED, make_targets, prepare_splits

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "experimentos"
FIG = ROOT / "reports" / "figures"
plt.rcParams.update({"figure.dpi": 300, "savefig.facecolor": "white", "font.size": 8})


def main():
    df = pd.read_csv(PROCESSED / "dataset_diario.csv", index_col="date", parse_dates=True)
    tr = df.loc[:"2022-06-30"]
    y = make_targets(tr)
    feats = [f for f in FEATURES if tr[f].std() > 0]          # geada_30d é constante

    # --- correlação feature × alvo (Pearson e Spearman) no treino
    linhas = []
    for f in feats:
        r = {"feature": f}
        for h in HORIZONS:
            d = pd.concat([tr[f], y[f"y_{h}d"]], axis=1).dropna()
            r[f"pearson_{h}d"] = d.corr().iloc[0, 1]
            r[f"spearman_{h}d"] = d.corr(method="spearman").iloc[0, 1]
        linhas.append(r)
    corr = pd.DataFrame(linhas).set_index("feature")
    corr.round(4).to_csv(OUT / "eda_corr_alvo.csv")

    sp = corr[[f"spearman_{h}d" for h in HORIZONS]]
    sp.columns = [f"{h} d" for h in HORIZONS]
    ordem = sp.abs().max(axis=1).sort_values(ascending=False).index
    fig, ax = plt.subplots(figsize=(7, 7))
    im = ax.imshow(sp.loc[ordem].values, cmap="RdBu_r", vmin=-0.4, vmax=0.4, aspect="auto")
    ax.set_yticks(range(len(ordem))); ax.set_yticklabels(ordem); ax.set_xticks(range(3)); ax.set_xticklabels(sp.columns)
    for i in range(len(ordem)):
        for j in range(3):
            ax.text(j, i, f"{sp.loc[ordem].values[i, j]:+.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="Spearman"); ax.set_title("Correlação de Spearman entre feature e log-retorno futuro (treino)")
    fig.tight_layout(); fig.savefig(FIG / "10_corr_features_alvo.png"); plt.close(fig)

    # --- matriz de correlação entre features
    C = tr[feats].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(C.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(feats))); ax.set_xticklabels(feats, rotation=90); ax.set_yticks(range(len(feats))); ax.set_yticklabels(feats)
    fig.colorbar(im, ax=ax, fraction=0.03); ax.set_title("Matriz de correlação de Spearman entre features (treino)")
    fig.tight_layout(); fig.savefig(FIG / "11_matriz_corr_features.png"); plt.close(fig)
    pares = [(a, b, C.loc[a, b]) for i, a in enumerate(feats) for b in feats[i + 1:] if abs(C.loc[a, b]) > 0.7]
    pd.DataFrame(pares, columns=["f1", "f2", "spearman"]).round(3).to_csv(OUT / "eda_pares_colineares.csv", index=False)

    # --- importância por permutação na LSTM (validação): ΔRMSE ao embaralhar cada feature na janela
    from src.models.predict import load_artifacts
    model, _, _ = load_artifacts()
    d = prepare_splits(); X, yv = d["val"]["X"], d["val"]["y"]
    rng = np.random.default_rng(42)
    base = np.sqrt(np.mean((model.predict(X, verbose=0) - yv) ** 2, axis=0))
    imp = []
    for j, f in enumerate(FEATURES):
        deltas = []
        for _ in range(3):
            Xp = X.copy(); Xp[:, :, j] = Xp[rng.permutation(len(X)), :, j]
            deltas.append(np.sqrt(np.mean((model.predict(Xp, verbose=0) - yv) ** 2, axis=0)) - base)
        m = np.mean(deltas, axis=0)
        imp.append({"feature": f, **{f"delta_rmse_{h}d": m[i] for i, h in enumerate(HORIZONS)},
                    "delta_rmse_medio_%": float(np.mean(m / base) * 100)})
        print(f, np.round(m, 4), flush=True)
    imp = pd.DataFrame(imp).set_index("feature").sort_values("delta_rmse_medio_%", ascending=False)
    imp.round(5).to_csv(OUT / "eda_importancia_permutacao.csv")
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(imp.index[::-1], imp["delta_rmse_medio_%"][::-1], color="#6E3F26")
    ax.axvline(0, color="k", lw=0.6); ax.set_xlabel("aumento médio do RMSE ao permutar a feature (%)")
    ax.set_title("Importância por permutação na LSTM (validação, média dos 3 horizontes)")
    fig.tight_layout(); fig.savefig(FIG / "12_importancia_permutacao.png"); plt.close(fig)
    print("ok")


if __name__ == "__main__":
    main()
