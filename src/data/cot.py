"""Posições de fundos no Coffee C (relatório COT/CFTC, semanal).

Extrai as posições non-commercial (especuladores) e o open interest.
IMPORTANTE (vazamento temporal): o relatório retrata a terça-feira mas é
publicado na sexta — a coluna `available_date` (+3 dias úteis) indica quando a
informação de fato existia para o mercado, e é ela que deve ancorar o merge.
"""

from pathlib import Path

import pandas as pd

DEFAULT_START_YEAR = 2000


def fetch_cot(start_year: int = DEFAULT_START_YEAR, end_year: int | None = None) -> pd.DataFrame:
    import cot_reports as cot

    end_year = end_year or pd.Timestamp.today().year
    frames = []
    for year in range(start_year, end_year + 1):
        try:
            df = cot.cot_year(year=year, cot_report_type="legacy_fut", store_txt=False, verbose=False)
            frames.append(df)
        except Exception as e:  # anos futuros/indisponíveis
            print(f"[cot] {year}: {e}")
    raw = pd.concat(frames)

    cafe = raw[raw["Market and Exchange Names"].str.contains("COFFEE C", case=False, na=False)].copy()
    out = pd.DataFrame({
        "report_date": pd.to_datetime(cafe["As of Date in Form YYYY-MM-DD"]),
        "noncomm_long": pd.to_numeric(cafe["Noncommercial Positions-Long (All)"], errors="coerce"),
        "noncomm_short": pd.to_numeric(cafe["Noncommercial Positions-Short (All)"], errors="coerce"),
        "open_interest": pd.to_numeric(cafe["Open Interest (All)"], errors="coerce"),
    })
    out["cot_net_noncomm"] = out["noncomm_long"] - out["noncomm_short"]
    out["cot_net_pct_oi"] = out["cot_net_noncomm"] / out["open_interest"]
    # divulgação: sexta-feira (~3 dias úteis após a terça de referência)
    out["available_date"] = out["report_date"] + pd.offsets.BDay(3)
    return out.sort_values("report_date").drop_duplicates("report_date").set_index("available_date")


if __name__ == "__main__":
    df = fetch_cot()
    dest = Path(__file__).resolve().parents[2] / "data" / "raw" / "cot_cftc.csv"
    df.to_csv(dest)
    print(f"Salvo {len(df)} linhas em {dest}")
    print(df.tail())
