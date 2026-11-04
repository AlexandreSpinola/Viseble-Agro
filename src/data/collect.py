"""Orquestra a coleta de todas as fontes e salva os brutos em data/raw.

Uso (da raiz do projeto, com o venv ativo):
    python -m src.data.collect
"""

from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def main(start: str = "2000-01-01") -> None:
    from src.data.bcb import fetch_bcb_data
    from src.data.cepea import load_cepea_data
    from src.data.market import fetch_market_data

    print("1/3 Yahoo Finance (KC=F, BRL=X)...")
    market = fetch_market_data(start=start)
    market.to_csv(RAW_DIR / "market_yahoo.csv")
    print(f"    {len(market)} linhas -> market_yahoo.csv")

    print("2/3 Banco Central (PTAX, Selic)...")
    macro = fetch_bcb_data(start=start)
    macro.to_csv(RAW_DIR / "macro_bcb.csv")
    print(f"    {len(macro)} linhas -> macro_bcb.csv")

    print("3/7 CEPEA (arábica e robusta, arquivos manuais)...")
    try:
        cepea = load_cepea_data()
        cepea.to_csv(RAW_DIR / "cepea_cafe.csv")
        print(f"    {len(cepea)} linhas -> cepea_cafe.csv")
    except FileNotFoundError as e:
        print(f"    PULADO: {e}")

    from src.data.clima import fetch_clima
    from src.data.cot import fetch_cot
    from src.data.insumos import fetch_insumos

    print("4/7 Clima Open-Meteo (regiões produtoras)...")
    clima = fetch_clima(start=start)
    clima.to_csv(RAW_DIR / "clima_openmeteo.csv")
    print(f"    {len(clima)} linhas -> clima_openmeteo.csv")

    print("5/7 COT/CFTC (posições de fundos, Coffee C)...")
    cot = fetch_cot(start_year=int(start[:4]))
    cot.to_csv(RAW_DIR / "cot_cftc.csv")
    print(f"    {len(cot)} linhas -> cot_cftc.csv")

    print("6/7 Insumos (World Bank Pink Sheet)...")
    insumos = fetch_insumos(start=start)
    insumos.to_csv(RAW_DIR / "insumos_pinksheet.csv")
    print(f"    {len(insumos)} linhas -> insumos_pinksheet.csv")

    from src.data.futures_curve import update_curve

    print("7/7 Curva de futuros ICE (contratos ativos, acumula histórico)...")
    curva = update_curve()
    print(f"    {len(curva)} linhas × {curva.shape[1]} contratos -> ice_curve.csv")

    print("Coleta concluída.")


if __name__ == "__main__":
    main()
