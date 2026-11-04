"""Alinhamento temporal e engenharia de features para o MVP.

Junta as fontes brutas (data/raw) num dataset diário único e cria as features
para a LSTM. Alvo do sistema: preço físico do arábica (CEPEA, R$/saca 60 kg),
que é o que o produtor efetivamente recebe.

Uso:
    python -m src.features.build_features
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

# 1 saca = 60 kg = 132.277 lb; preço ICE em cents/lb
LB_POR_SACA = 132.277

TARGET = "cepea_arabica_brl_sc"


def load_aligned(start: str = "2001-11-08") -> pd.DataFrame:
    """Carrega os brutos e alinha num calendário diário de dias úteis.

    Começa por padrão no início da série do robusta, para que todas as
    variáveis existam. Dias sem pregão em alguma fonte são preenchidos com o
    último valor conhecido (ffill) — nunca com valores futuros.
    """
    market = pd.read_csv(RAW / "market_yahoo.csv", index_col="date", parse_dates=True)
    macro = pd.read_csv(RAW / "macro_bcb.csv", index_col="date", parse_dates=True)
    cepea = pd.read_csv(RAW / "cepea_cafe.csv", index_col="date", parse_dates=True)
    clima = pd.read_csv(RAW / "clima_openmeteo.csv", index_col="date", parse_dates=True)
    # COT e insumos são indexados pela data de DIVULGAÇÃO (available_date),
    # não pela data de referência — evita vazamento temporal.
    cot = pd.read_csv(RAW / "cot_cftc.csv", index_col="available_date",
                      parse_dates=True)[["cot_net_noncomm", "cot_net_pct_oi"]]
    insumos = pd.read_csv(RAW / "insumos_pinksheet.csv", index_col="available_date",
                          parse_dates=True).drop(columns=["month"])

    df = cepea.join([market, macro, clima, cot, insumos], how="outer").sort_index()
    df.index.name = "date"  # o join com índices de nomes distintos apaga o nome
    df = df.loc[start:]

    # Features de clima calculadas AQUI, no calendário civil completo — se
    # fossem calculadas após o recorte para dias úteis, a chuva de fins de
    # semana e feriados seria perdida.
    regioes_arabica = ["sul_minas", "cerrado_mg", "mogiana"]
    prec_ar = df[[f"prec_{r}" for r in regioes_arabica]].mean(axis=1)
    tmin_ar = df[[f"tmin_{r}" for r in regioes_arabica]].min(axis=1)
    df["chuva_arabica_30d"] = prec_ar.rolling(30).sum()
    df["chuva_arabica_90d"] = prec_ar.rolling(90).sum()
    df["tmin_arabica_7d"] = tmin_ar.rolling(7).min()
    # geada: Tmin < 3°C no inverno (mai-set); rolling 30d mantém o evento "vivo"
    geada_dia = ((tmin_ar < 3) & df.index.month.isin([5, 6, 7, 8, 9])).astype(int)
    df["geada_30d"] = geada_dia.rolling(30).max()
    df["chuva_robusta_90d"] = df["prec_es_robusta"].rolling(90).sum()
    df = df.drop(columns=[c for c in df.columns if c.startswith(("prec_", "tmin_")) and "_7d" not in c])
    # calendário de referência: dias com indicador CEPEA arábica publicado
    # (dias úteis BR); só depois o ffill preenche pregões ausentes das demais
    # fontes com o último valor conhecido — nunca com valores futuros.
    ref_days = df[TARGET].dropna().index
    df = df.ffill().loc[ref_days]
    return df.dropna()


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Cria as features do MVP a partir do dataset alinhado."""
    out = df.copy()
    price = out[TARGET]

    # --- conversão do futuro ICE para R$/saca (comparável ao físico) ---
    out["ice_arabica_brl_sc"] = out["ice_arabica_cents_lb"] / 100 * LB_POR_SACA * out["ptax_venda"]
    # base/prêmio físico: quanto o preço físico difere do futuro (risco de base)
    out["base_fisico_futuro"] = price - out["ice_arabica_brl_sc"]
    out["base_fisico_futuro_pct"] = out["base_fisico_futuro"] / out["ice_arabica_brl_sc"]

    # --- retornos logarítmicos ---
    for col, name in [(TARGET, "arabica"), ("cepea_robusta_brl_sc", "robusta"),
                      ("ice_arabica_cents_lb", "ice"), ("ptax_venda", "ptax")]:
        out[f"ret_{name}_1d"] = np.log(out[col]).diff()
    out["ret_arabica_21d"] = np.log(price).diff(21)

    # --- médias móveis e posição relativa do preço ---
    for win, name in [(21, "1m"), (63, "3m"), (252, "1a"), (504, "2a")]:
        ma = price.rolling(win).mean()
        out[f"ma_{name}"] = ma
        out[f"preco_vs_ma_{name}"] = price / ma - 1

    # --- volatilidade realizada (21 dias, anualizada) ---
    out["vol_21d"] = out["ret_arabica_1d"].rolling(21).std() * np.sqrt(252)

    # --- spread arábica x robusta (substituição na demanda) ---
    out["spread_arabica_robusta"] = price / out["cepea_robusta_brl_sc"]

    # --- posicionamento de fundos (COT/CFTC) ---
    out["cot_net_pct_oi_chg4w"] = out["cot_net_pct_oi"].diff(20)

    # --- insumos agrícolas (custo de produção / oferta futura) ---
    urea_brl_ton = out["urea_usd_ton"] * out["ptax_venda"]
    # índice de troca (módulo 4 AgroSafety): sacas de café para comprar 1 t de ureia
    out["indice_troca_urea"] = urea_brl_ton / price
    out["ret_urea_1a"] = np.log(out["urea_usd_ton"]).diff(252)
    out["ret_crude_1a"] = np.log(out["crude_usd_bbl"]).diff(252)

    # --- sazonalidade e bienalidade ---
    # ano-safra: começa em julho (colheita). Bienalidade: alternância de carga.
    ano_safra = out.index.year.where(out.index.month >= 7, out.index.year - 1)
    out["mes_sin"] = np.sin(2 * np.pi * out.index.month / 12)
    out["mes_cos"] = np.cos(2 * np.pi * out.index.month / 12)
    # 2020, 2022, 2024... = anos-safra de alta bienalidade (carga cheia) no BR
    out["bienalidade_alta"] = (ano_safra % 2 == 0).astype(int)
    out["ano_safra"] = ano_safra

    return out.dropna()


def chronological_split(df: pd.DataFrame, train_end: str = "2022-06-30",
                        val_end: str = "2024-06-30") -> dict[str, pd.DataFrame]:
    """Partição cronológica estrita (sem vazamento temporal).

    O ciclo de decisão do produtor é limitado pela bienalidade (~2 anos-safra),
    então o teste cobre exatamente 2 safras (~720 dias corridos).

    - treino    : início  -> 2022-06-30 (~17 safras; inclui geada 2021)
    - validação : 2022-07 -> 2024-06-30 (2 safras; early stopping e
                  hiperparâmetros — decisões de treino NÃO podem olhar o teste,
                  senão o backtest deixa de ser cego)
    - teste     : 2024-07 -> fim        (2 safras; reservado ao backtest)
    """
    return {
        "train": df.loc[:train_end],
        "val": df.loc[pd.Timestamp(train_end) + pd.Timedelta(days=1): val_end],
        "test": df.loc[pd.Timestamp(val_end) + pd.Timedelta(days=1):],
    }


def main() -> pd.DataFrame:
    df = add_features(load_aligned())
    dest = PROCESSED / "dataset_diario.csv"
    df.to_csv(dest)
    splits = chronological_split(df)
    for name, part in splits.items():
        print(f"{name:6s}: {part.index.min().date()} a {part.index.max().date()} | {len(part)} linhas")
    print(f"{df.shape[1]} colunas -> {dest}")
    return df


if __name__ == "__main__":
    main()
