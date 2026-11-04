"""Preços internacionais de insumos agrícolas (World Bank "Pink Sheet", mensal).

Séries usadas (US$): ureia, DAP, cloreto de potássio (KCl) e petróleo bruto
(proxy de diesel/defensivos). Fertilizantes são oligopólio global e o Brasil
importa a maior parte — choques de custo apertam a margem do cafeicultor e
afetam a oferta futura (ver material AgroSafety, módulos 3 e 4).

Vazamento temporal: preço médio do mês M só é conhecido depois do fechamento
de M — `available_date` = 3 dias úteis após o fim do mês.
"""

from pathlib import Path

import pandas as pd
import requests

URL = ("https://thedocs.worldbank.org/en/doc/"
       "18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx")

COLS = {
    "Urea ": "urea_usd_ton",
    "DAP": "dap_usd_ton",
    "Potassium chloride **": "kcl_usd_ton",
    "Crude oil, average": "crude_usd_bbl",
}

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def fetch_insumos(start: str = "2000-01-01") -> pd.DataFrame:
    xlsx = RAW_DIR / "pinksheet_monthly.xlsx"
    r = requests.get(URL, timeout=180)
    r.raise_for_status()
    xlsx.write_bytes(r.content)

    df = pd.read_excel(xlsx, sheet_name="Monthly Prices", skiprows=4)
    df = df.rename(columns={df.columns[0]: "month"})
    df = df[df["month"].astype(str).str.match(r"\d{4}M\d{2}")]
    df["month"] = pd.to_datetime(df["month"].astype(str), format="%YM%m")

    out = df[["month"] + list(COLS)].rename(columns=COLS)
    for c in COLS.values():
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.set_index("month").sort_index().loc[start:]
    # divulgação: início do mês seguinte (~3 dias úteis após o fim do mês)
    out["available_date"] = out.index + pd.offsets.MonthEnd(0) + pd.offsets.BDay(3)
    return out.reset_index().set_index("available_date")


if __name__ == "__main__":
    df = fetch_insumos()
    dest = RAW_DIR / "insumos_pinksheet.csv"
    df.to_csv(dest)
    print(f"Salvo {len(df)} linhas em {dest}")
    print(df.tail())
