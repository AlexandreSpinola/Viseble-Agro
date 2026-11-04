"""Coleta de dados de mercado via Yahoo Finance.

- KC=F : Futuros de Café Arábica (ICE NY, Coffee C), em cents de dólar por libra-peso
- BRL=X: Câmbio USD/BRL (referência intradiária do Yahoo; o PTAX oficial vem do BCB)

Obs.: os contratos de robusta (Londres) não estão mais disponíveis no Yahoo
(RC=F / RM=F delistados). O preço do robusta é obtido do indicador físico
CEPEA/ESALQ (ver cepea.py).
"""

import pandas as pd
import yfinance as yf

TICKERS = {
    "KC=F": "ice_arabica_cents_lb",
    "BRL=X": "usd_brl_yahoo",
}

DEFAULT_START = "2000-01-01"


def fetch_market_data(start: str = DEFAULT_START, end: str | None = None) -> pd.DataFrame:
    """Baixa preços de fechamento dos tickers e retorna um DataFrame diário."""
    frames = []
    for ticker, col in TICKERS.items():
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        close = df["Close"]
        # yfinance pode retornar colunas MultiIndex (Close, ticker)
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        frames.append(close.rename(col))
    out = pd.concat(frames, axis=1)
    out.index.name = "date"
    return out


if __name__ == "__main__":
    from pathlib import Path

    df = fetch_market_data()
    dest = Path(__file__).resolve().parents[2] / "data" / "raw" / "market_yahoo.csv"
    df.to_csv(dest)
    print(f"Salvo {len(df)} linhas em {dest}")
    print(df.tail())
