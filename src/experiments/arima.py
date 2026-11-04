"""C4: baseline ARIMA sobre o log-preço diário.

Ordem (p, 1, q) escolhida por AIC no TREINO (grade p, q ∈ {0, 1, 2}). Os
parâmetros ficam fixos; para cada data de validação/teste o modelo é aplicado
à série até aquela data (statsmodels `apply`) e a previsão recursiva de 21, 63
e 126 dias úteis é comparada ao realizado, na mesma métrica da LSTM.

Uso:  python -m src.experiments.arima
Saída: reports/experimentos/c4_arima.csv
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

from src.models.dataset import HORIZONS, PROCESSED, TARGET, prepare_splits

OUT = Path(__file__).resolve().parents[2] / "reports" / "experimentos"


def main():
    warnings.filterwarnings("ignore")
    d = prepare_splits()
    df = d["df"]
    logp = np.log(df[TARGET])
    treino = logp.loc[:"2022-06-30"].to_numpy()

    melhor = None
    for p in range(3):
        for q in range(3):
            res = ARIMA(treino, order=(p, 1, q), trend="n").fit()
            if melhor is None or res.aic < melhor[1]:
                melhor = ((p, 1, q), res.aic, res)
    ordem, aic, res = melhor
    print("ordem por AIC no treino:", ordem, "AIC", round(aic, 1), flush=True)

    linhas = []
    for split in ["val", "test"]:
        dates = d[split]["dates"]; y = d[split]["y"]
        pred = np.zeros((len(dates), len(HORIZONS)))
        for i, dt in enumerate(dates):
            hist = logp.loc[:dt].to_numpy()
            r = res.apply(hist)
            fc = r.forecast(steps=max(HORIZONS))
            pred[i] = [fc[h - 1] - hist[-1] for h in HORIZONS]
        for j, h in enumerate(HORIZONS):
            err = pred[:, j] - y[:, j]
            linhas.append({"split": split, "horizonte": f"{h}d", "ordem": str(ordem),
                           "rmse_arima": float(np.sqrt(np.mean(err ** 2))), "mae_arima": float(np.mean(np.abs(err))),
                           "mape_preco_%": float(np.mean(np.abs(np.expm1(err))) * 100),
                           "acerto_direcao_arima_%": float(np.mean(np.sign(pred[:, j]) == np.sign(y[:, j])) * 100),
                           "rmse_naive": float(np.sqrt(np.mean(y[:, j] ** 2)))})
        print(split, "ok", flush=True)
    t = pd.DataFrame(linhas).round(4)
    t.to_csv(OUT / "c4_arima.csv", index=False)
    print(t.to_string(index=False))


if __name__ == "__main__":
    main()
