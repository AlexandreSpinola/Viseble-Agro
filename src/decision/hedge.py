"""Hedge de preço com futuros: curva em R$/saca, base esperada e risco de base.

Segue a metodologia do módulo 5 (AgroSafety):
    base = preço físico (CEPEA) − futuro em R$/saca
    preço travado = futuro do vencimento + base esperada − custo operacional
    risco de base = dispersão da variação da base entre a decisão e a venda

Na prática a base em R$ escala com o nível de preço; em PERCENTUAL do futuro
ela é estável (≈ −19% ± 5 pp desde 2015). Por isso modelamos
    físico ≈ futuro_R$ · (1 + b),   b = base percentual, sazonal por mês.

Instrumento: contrato Coffee C (ICE NY) convertido pela PTAX — proxy do ICF da
B3 (cotado em US$/saca e arbitrado com NY). Quando a curva por vencimento não
existe para uma data (contratos vencidos não ficam no Yahoo), usa-se o
primeiro vencimento rolado ("stack-and-roll"), curva plana.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.data.futures_curve import CURVE_FILE, curva_na_data
from src.models.dataset import HORIZONS, PROCESSED, TARGET

LB_POR_SACA = 132.277
BASE_FILE = PROCESSED / "base_stats.json"


def calcular_base_stats(df: pd.DataFrame, desde: str = "2015-01-01", ate: str = "2022-06-30") -> dict:
    """Base percentual média por mês do ano e risco de base (pp) por horizonte.
    Estimado SÓ no período de treino (até `ate`), para o benchmark da curva e o
    motor não olharem validação/teste."""
    d = df.loc[desde:ate]
    b = d["base_fisico_futuro_pct"]
    sazonal = b.groupby(d.index.month).mean()
    risco = {int(h): float((b.shift(-h) - b).dropna().std()) for h in HORIZONS}
    stats = {
        "base_pct_por_mes": {int(m): float(v) for m, v in sazonal.items()},
        "base_pct_media": float(b.mean()),
        "risco_base_pct_por_h": risco,
        "desde": desde, "ate": ate,
    }
    BASE_FILE.write_text(json.dumps(stats, indent=2))
    return stats


def base_stats() -> dict:
    if not BASE_FILE.exists():
        df = pd.read_csv(PROCESSED / "dataset_diario.csv", index_col="date", parse_dates=True)
        return calcular_base_stats(df)
    s = json.loads(BASE_FILE.read_text())
    s["base_pct_por_mes"] = {int(k): v for k, v in s["base_pct_por_mes"].items()}
    s["risco_base_pct_por_h"] = {int(k): v for k, v in s["risco_base_pct_por_h"].items()}
    return s


def risco_base_pct(dias_uteis: int, stats: dict | None = None) -> float:
    """Desvio-padrão (fração) da variação da base num prazo, interpolando os horizontes."""
    s = stats or base_stats()
    hs = [0, *HORIZONS]
    vs = [0.0, *[s["risco_base_pct_por_h"][h] for h in HORIZONS]]
    return float(np.interp(dias_uteis, hs, vs))


def curva_brl(data: pd.Timestamp, ptax: float, curve: pd.DataFrame | None = None) -> pd.Series:
    """Curva de futuros em R$/saca por mês de vencimento, na data. Vazia se não houver."""
    if curve is None:
        if not CURVE_FILE.exists():
            return pd.Series(dtype=float)
        curve = pd.read_csv(CURVE_FILE, index_col="date", parse_dates=True)
    if pd.Timestamp(data) < curve.index[0]:
        return pd.Series(dtype=float)
    cents = curva_na_data(curve, data)
    return cents / 100 * LB_POR_SACA * ptax


def futuro_por_mes(data: pd.Timestamp, ptax: float, front_brl: float, k_max: int,
                   passo_dias: int = 21, curve: pd.DataFrame | None = None) -> np.ndarray:
    """F[m] = futuro (R$/saca) do primeiro vencimento >= mês de venda m (m = 1..k_max).

    Sem curva na data, devolve o primeiro vencimento para todos os meses (curva
    plana = hedge rolado). Índice 0 é o próprio front (venda imediata)."""
    c = curva_brl(data, ptax, curve)
    F = np.full(k_max + 1, front_brl, dtype=float)
    if c.empty:
        return F
    for m in range(1, k_max + 1):
        data_venda = pd.Timestamp(data) + pd.tseries.offsets.BDay(m * passo_dias)
        alvo = data_venda.to_period("M").to_timestamp()
        cands = c[c.index >= alvo]
        F[m] = float(cands.iloc[0]) if len(cands) else float(c.iloc[-1])
    return F


def base_por_mes(data: pd.Timestamp, k_max: int, passo_dias: int = 21,
                 stats: dict | None = None) -> np.ndarray:
    """Base percentual esperada no mês de venda m = 0..k_max (sazonal)."""
    s = stats or base_stats()
    out = np.empty(k_max + 1)
    for m in range(k_max + 1):
        data_venda = pd.Timestamp(data) + pd.tseries.offsets.BDay(m * passo_dias)
        out[m] = s["base_pct_por_mes"][data_venda.month]
    return out


def previsao_implicita(df: pd.DataFrame, dates: pd.DatetimeIndex, stats: dict | None = None) -> pd.DataFrame:
    """Benchmark 'curva': retorno implícito no futuro + base sazonal, por horizonte.
    y_h = ln[ F_t · (1 + b_{t+h}) / P_t ]  (front rolado; sem curva histórica)."""
    s = stats or base_stats()
    F = df.loc[dates, "ice_arabica_brl_sc"].to_numpy()
    P = df.loc[dates, TARGET].to_numpy()
    out = {}
    for h in HORIZONS:
        meses = [(d + pd.tseries.offsets.BDay(h)).month for d in dates]
        b = np.array([s["base_pct_por_mes"][m] for m in meses])
        out[f"y_{h}d"] = np.log(F * (1 + b) / P)
    return pd.DataFrame(out, index=dates)
