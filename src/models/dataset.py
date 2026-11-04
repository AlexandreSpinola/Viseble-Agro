"""Preparação de sequências para a LSTM.

Alvo: log-retorno do preço físico do arábica em múltiplos horizontes
(21, 63 e 126 dias úteis ≈ 1, 3 e 6 meses), a partir dos quais o motor
prescritivo reconstrói trajetórias de preço: P(t+h) = P(t) * exp(y_h).

Prever retornos (e não níveis) evita que a rede aprenda a não-estacionariedade
da série; as features também são todas estacionárias ou limitadas.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
MODELS = ROOT / "models"

TARGET = "cepea_arabica_brl_sc"
HORIZONS = (21, 63, 126)  # dias úteis ~ 1m, 3m, 6m
LOOKBACK = 63             # janela de entrada: ~3 meses

FEATURES = [
    # mercado
    "ret_arabica_1d", "ret_arabica_21d", "ret_robusta_1d", "ret_ice_1d", "ret_ptax_1d",
    "preco_vs_ma_1m", "preco_vs_ma_3m", "preco_vs_ma_1a", "preco_vs_ma_2a",
    "vol_21d", "spread_arabica_robusta", "base_fisico_futuro_pct",
    "mes_sin", "mes_cos", "bienalidade_alta", "selic_meta",
    # clima nas regiões produtoras (choques de oferta)
    "chuva_arabica_30d", "chuva_arabica_90d", "tmin_arabica_7d",
    "geada_30d", "chuva_robusta_90d",
    # posicionamento de fundos (COT/CFTC)
    "cot_net_pct_oi", "cot_net_pct_oi_chg4w",
    # insumos agrícolas (custo de produção)
    "indice_troca_urea", "ret_urea_1a", "ret_crude_1a",
]


def make_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Log-retornos futuros por horizonte: y_h(t) = ln P(t+h) - ln P(t)."""
    logp = np.log(df[TARGET])
    return pd.DataFrame(
        {f"y_{h}d": logp.shift(-h) - logp for h in HORIZONS}, index=df.index
    )


def make_sequences(df: pd.DataFrame, split_index: pd.DatetimeIndex,
                   scaler: StandardScaler) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    """Constrói (X, y, datas) para as datas de um split.

    A janela de ENTRADA (features passadas, já conhecidas na data da previsão)
    é lida do dataset completo e pode cruzar a fronteira do split anterior —
    isso não é vazamento, é o histórico que o modelo teria em produção. Assim
    a primeira previsão do split parte do último preço conhecido, sem perder
    os LOOKBACK-1 primeiros dias.

    O ALVO continua restrito ao split: y usa só preços do próprio split, então
    as últimas max(HORIZONS) datas de cada split são descartadas (alvo
    desconhecido sem olhar o split seguinte).
    """
    y_df = make_targets(df.loc[split_index]).dropna()  # alvo só com preços do próprio split
    feat = pd.DataFrame(scaler.transform(df[FEATURES]), index=df.index, columns=FEATURES)

    X, y, dates = [], [], []
    positions = df.index.get_indexer(y_df.index)
    for pos, date in zip(positions, y_df.index):
        if pos + 1 < LOOKBACK:
            continue  # só acontece no início do treino
        X.append(feat.iloc[pos + 1 - LOOKBACK: pos + 1].to_numpy())
        y.append(y_df.loc[date].to_numpy())
        dates.append(date)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32), pd.DatetimeIndex(dates)


def prepare_splits() -> dict:
    """Carrega o dataset, ajusta o scaler SÓ no treino e janela cada split.

    A janela de entrada usa o histórico completo (pode cruzar a fronteira do
    split); o alvo fica restrito às datas de cada split.
    """
    from src.features.build_features import chronological_split

    df = pd.read_csv(PROCESSED / "dataset_diario.csv", index_col="date", parse_dates=True)
    splits = chronological_split(df)

    scaler = StandardScaler().fit(splits["train"][FEATURES])
    joblib.dump(scaler, MODELS / "scaler.joblib")

    out = {"scaler": scaler, "df": df}
    for name, part in splits.items():
        X, y, dates = make_sequences(df, part.index, scaler)
        out[name] = {"X": X, "y": y, "dates": dates}
    return out
