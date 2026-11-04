"""Clima histórico nas principais regiões produtoras (Open-Meteo / ERA5).

Regiões (participação na produção segundo CONAB):
- Arábica: Sul de Minas, Cerrado Mineiro e Mogiana (MG+SP ~85% do arábica)
- Robusta: Espírito Santo (~72% do robusta)

Variáveis diárias: temperatura mínima (risco de geada) e precipitação
(déficit hídrico na floração set-nov e enchimento dez-mar).
"""

import time
from pathlib import Path

import pandas as pd
import requests

REGIONS = {
    "sul_minas": (-21.55, -45.43),    # Varginha
    "cerrado_mg": (-18.94, -46.99),   # Patrocínio
    "mogiana": (-20.54, -47.40),      # Franca
    "es_robusta": (-19.54, -40.63),   # Colatina
}

API = "https://archive-api.open-meteo.com/v1/archive"
DEFAULT_START = "2000-01-01"


def fetch_region(name: str, lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    r = requests.get(API, params={
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "daily": "temperature_2m_min,precipitation_sum",
        "timezone": "America/Sao_Paulo",
    }, timeout=120)
    r.raise_for_status()
    d = r.json()["daily"]
    return pd.DataFrame({
        "date": pd.to_datetime(d["time"]),
        f"tmin_{name}": d["temperature_2m_min"],
        f"prec_{name}": d["precipitation_sum"],
    }).set_index("date")


def fetch_clima(start: str = DEFAULT_START, end: str | None = None) -> pd.DataFrame:
    end = end or str((pd.Timestamp.today() - pd.Timedelta(days=7)).date())  # ERA5 tem ~5 dias de atraso
    frames = []
    for name, (lat, lon) in REGIONS.items():
        frames.append(fetch_region(name, lat, lon, start, end))
        time.sleep(1)  # cortesia com a API gratuita
    return pd.concat(frames, axis=1)


if __name__ == "__main__":
    df = fetch_clima()
    dest = Path(__file__).resolve().parents[2] / "data" / "raw" / "clima_openmeteo.csv"
    df.to_csv(dest)
    print(f"Salvo {len(df)} linhas em {dest}")
    print(df.tail())
