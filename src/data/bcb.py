"""Coleta de séries macroeconômicas oficiais do Banco Central do Brasil (API SGS).

- Série 1  : Taxa de câmbio livre - Dólar americano (venda) - PTAX, diário
- Série 432: Meta Selic definida pelo Copom (% a.a.)
"""

import pandas as pd
from bcb import sgs

SERIES = {
    "ptax_venda": 1,
    "selic_meta": 432,
}

DEFAULT_START = "2000-01-01"


def fetch_bcb_data(start: str = DEFAULT_START, end: str | None = None) -> pd.DataFrame:
    """Baixa as séries do SGS e retorna um DataFrame diário (dias úteis).

    A API do SGS limita consultas de séries diárias a janelas de 10 anos,
    então a busca é feita em blocos de 9 anos e concatenada.
    """
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) if end else pd.Timestamp.today().normalize()

    chunks = []
    chunk_start = start_ts
    while chunk_start <= end_ts:
        chunk_end = min(chunk_start + pd.DateOffset(years=9), end_ts)
        chunks.append(sgs.get(SERIES, start=str(chunk_start.date()), end=str(chunk_end.date())))
        chunk_start = chunk_end + pd.Timedelta(days=1)

    df = pd.concat(chunks)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index.name = "date"
    return df


if __name__ == "__main__":
    from pathlib import Path

    df = fetch_bcb_data()
    dest = Path(__file__).resolve().parents[2] / "data" / "raw" / "macro_bcb.csv"
    df.to_csv(dest)
    print(f"Salvo {len(df)} linhas em {dest}")
    print(df.tail())
