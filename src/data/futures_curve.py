"""Curva de futuros de Café Arábica (ICE NY, Coffee C) por vencimento.

O Yahoo Finance só mantém os contratos ATIVOS (os vencidos são removidos),
então este módulo:
- baixa todos os contratos ativos (meses H, K, N, U, Z dos próximos anos);
- acumula o histórico em data/raw/ice_curve.csv a cada execução, para que
  a curva passada fique preservada para backtests futuros.

Cotação em cents de US$/lb. Conversão para R$/saca em src/features.
Ticker Yahoo: KC + mês + ano(2 dígitos) + .NYB  (ex.: KCU26.NYB = set/2026).
"""

from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
CURVE_FILE = RAW_DIR / "ice_curve.csv"
MESES = {"H": 3, "K": 5, "N": 7, "U": 9, "Z": 12}     # vencimentos do Coffee C


def contratos_ativos(hoje: date | None = None, anos_a_frente: int = 3) -> list[str]:
    hoje = hoje or date.today()
    out = []
    for ano in range(hoje.year, hoje.year + anos_a_frente + 1):
        for cod, mes in MESES.items():
            if date(ano, mes, 1) >= date(hoje.year, hoje.month, 1):
                out.append(f"KC{cod}{ano % 100:02d}")
    return out


def vencimento(contrato: str) -> pd.Timestamp:
    """Mês de vencimento (1º dia) a partir do código, ex.: KCU26 -> 2026-09-01."""
    return pd.Timestamp(year=2000 + int(contrato[3:5]), month=MESES[contrato[2]], day=1)


def fetch_curve(start: str = "2018-01-01") -> pd.DataFrame:
    frames = []
    for c in contratos_ativos():
        try:
            df = yf.download(f"{c}.NYB", start=start, progress=False, auto_adjust=True)
        except Exception:
            continue
        if df is None or len(df) == 0:
            continue
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        frames.append(close.rename(c))
    out = pd.concat(frames, axis=1)
    out.index.name = "date"
    return out


def update_curve(start: str = "2018-01-01") -> pd.DataFrame:
    """Baixa a curva ativa e funde com o histórico salvo (mantém contratos vencidos)."""
    novo = fetch_curve(start)
    if CURVE_FILE.exists():
        antigo = pd.read_csv(CURVE_FILE, index_col="date", parse_dates=True)
        novo = novo.combine_first(antigo)
    novo = novo.sort_index()
    novo = novo[sorted(novo.columns, key=vencimento)]
    novo.to_csv(CURVE_FILE)
    return novo


def curva_na_data(curve: pd.DataFrame, data: pd.Timestamp) -> pd.Series:
    """Preços (cents/lb) dos contratos com cotação na última data <= `data`,
    apenas vencimentos futuros, indexados pelo mês de vencimento."""
    pos = curve.index.searchsorted(pd.Timestamp(data), side="right") - 1
    linha = curve.iloc[pos].dropna()
    linha.index = [vencimento(c) for c in linha.index]
    return linha[linha.index >= pd.Timestamp(data).to_period("M").to_timestamp()].sort_index()


if __name__ == "__main__":
    df = update_curve()
    print(f"Salvo {len(df)} linhas × {df.shape[1]} contratos em {CURVE_FILE}")
    print(curva_na_data(df, df.index[-1]))
