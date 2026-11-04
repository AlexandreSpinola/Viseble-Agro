"""Previsão da LSTM para uma data de origem + incerteza residual por horizonte.

O motor prescritivo precisa, para uma data t, de:
- ŷ_h: log-retorno previsto para cada horizonte (ponto central da trajetória);
- σ_h: desvio-padrão dos resíduos (ŷ_h − y_h) na validação, usado como
  incerteza da previsão ao construir os cenários de preço.
"""

import json
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from src.models.dataset import (FEATURES, HORIZONS, LOOKBACK, MODELS, PROCESSED,
                                prepare_splits)

SIGMA_FILE = MODELS / "residual_sigma.json"


@lru_cache(maxsize=1)
def load_artifacts() -> tuple["keras.Model", object, pd.DataFrame]:
    import keras
    model = keras.models.load_model(MODELS / "lstm_multihorizonte.keras")
    scaler = joblib.load(MODELS / "scaler.joblib")
    df = pd.read_csv(PROCESSED / "dataset_diario.csv", index_col="date", parse_dates=True)
    return model, scaler, df


def forecast(date, df: pd.DataFrame | None = None, model=None, scaler=None) -> dict[int, float]:
    """ŷ_h para a última data disponível <= `date` (sem olhar o futuro)."""
    if df is None or model is None or scaler is None:
        model, scaler, df = load_artifacts()
    pos = df.index.searchsorted(pd.Timestamp(date), side="right") - 1
    if pos + 1 < LOOKBACK:
        raise ValueError(f"histórico insuficiente antes de {date}")
    window = scaler.transform(df[FEATURES].iloc[pos + 1 - LOOKBACK: pos + 1])
    pred = model.predict(window[None].astype(np.float32), verbose=0)[0]
    return {h: float(pred[i]) for i, h in enumerate(HORIZONS)}


def forecast_batch(dates: pd.DatetimeIndex, df: pd.DataFrame, model, scaler) -> pd.DataFrame:
    """Mesmo que `forecast`, vetorizado para várias datas (backtest)."""
    feat = scaler.transform(df[FEATURES]).astype(np.float32)
    positions = df.index.searchsorted(dates, side="right") - 1
    X = np.stack([feat[p + 1 - LOOKBACK: p + 1] for p in positions])
    pred = model.predict(X, verbose=0)
    return pd.DataFrame(pred, index=dates, columns=[f"y_{h}d" for h in HORIZONS])


def compute_residual_sigma(model=None, data: dict | None = None) -> dict[int, float]:
    """σ_h dos resíduos na VALIDAÇÃO (o teste permanece cego). Salva em models/."""
    if data is None:
        data = prepare_splits()
    if model is None:
        model, _, _ = load_artifacts()
    val = data["val"]
    resid = model.predict(val["X"], verbose=0) - val["y"]
    sigma = {h: float(resid[:, i].std()) for i, h in enumerate(HORIZONS)}
    SIGMA_FILE.write_text(json.dumps(sigma, indent=2))
    return sigma


def residual_sigma() -> dict[int, float]:
    if not SIGMA_FILE.exists():
        return compute_residual_sigma()
    return {int(k): v for k, v in json.loads(SIGMA_FILE.read_text()).items()}
