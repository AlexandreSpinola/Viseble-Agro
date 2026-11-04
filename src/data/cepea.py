"""Leitura dos indicadores físicos de café do CEPEA/ESALQ.

O site do CEPEA bloqueia downloads automatizados (WAF retorna 403), então as
séries históricas foram baixadas manualmente de
https://www.cepea.esalq.usp.br/br/indicador/cafe.aspx e salvas em data/external/
no padrão:

    cepea-consulta-<frequencia>-<produto>-<ano_inicial>.xls
    ex.: cepea-consulta-diaria-arabica-1986.xls, cepea-consulta-diaria-robusta-2006.xls

A frequência diária vem dividida em mais de um arquivo (limite de download do
site); este módulo lê todos os arquivos de cada produto, concatena e remove
duplicatas.

Formato dos XLS: 3 linhas de metadados, cabeçalho na 4ª linha com colunas
"Data", "À vista R$" e "À vista US$" (valores por saca de 60 kg, decimais com
vírgula). Os arquivos têm uma corrupção estrutural inofensiva que exige
xlrd com ignore_workbook_corruption=True.

Obs.: apesar do "1986" no nome, o indicador arábica inicia em set/1996 e o
robusta em 2001 — é o alcance real das séries do CEPEA.
"""

from pathlib import Path

import pandas as pd

EXTERNAL_DIR = Path(__file__).resolve().parents[2] / "data" / "external"

PRODUTOS = ("arabica", "robusta")


def _to_float(series: pd.Series) -> pd.Series:
    """Converte valores no formato brasileiro ('1.234,56') para float."""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    return pd.to_numeric(
        series.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )


def load_cepea_file(path: Path, prefix: str) -> pd.DataFrame:
    """Lê um XLS do CEPEA e retorna DataFrame com índice de data."""
    df = pd.read_excel(
        path,
        skiprows=3,
        engine="xlrd",
        engine_kwargs={"ignore_workbook_corruption": True},
    )
    df.columns = [str(c).strip().lower() for c in df.columns]
    date_col = next(c for c in df.columns if "data" in c)
    brl_col = next(c for c in df.columns if "r$" in c)
    usd_col = next((c for c in df.columns if "us$" in c), None)

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col], format="%d/%m/%Y", errors="coerce")
    out[f"cepea_{prefix}_brl_sc"] = _to_float(df[brl_col])
    if usd_col:
        out[f"cepea_{prefix}_usd_sc"] = _to_float(df[usd_col])
    return out.dropna(subset=["date"]).set_index("date").sort_index()


def load_cepea_product(produto: str, freq: str = "diaria", external_dir: Path = EXTERNAL_DIR) -> pd.DataFrame:
    """Concatena todos os arquivos de um produto/frequência, sem duplicatas."""
    paths = sorted(external_dir.glob(f"cepea-consulta-{freq}-{produto}-*.xls"))
    if not paths:
        raise FileNotFoundError(f"Nenhum arquivo cepea-consulta-{freq}-{produto}-*.xls em {external_dir}.")
    df = pd.concat([load_cepea_file(p, produto) for p in paths])
    return df[~df.index.duplicated(keep="last")].sort_index()


def load_cepea_data(freq: str = "diaria", external_dir: Path = EXTERNAL_DIR) -> pd.DataFrame:
    """Carrega arábica e robusta e junta num único DataFrame diário."""
    frames = []
    for produto in PRODUTOS:
        try:
            frames.append(load_cepea_product(produto, freq, external_dir))
        except FileNotFoundError as e:
            print(f"[cepea] AVISO: {e}")
    if not frames:
        raise FileNotFoundError("Nenhum arquivo do CEPEA encontrado em data/external/.")
    return pd.concat(frames, axis=1)


if __name__ == "__main__":
    df = load_cepea_data()
    dest = Path(__file__).resolve().parents[2] / "data" / "raw" / "cepea_cafe.csv"
    df.to_csv(dest)
    print(f"Salvo {len(df)} linhas em {dest}")
    print(df.tail())
