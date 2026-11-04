"""Relatório técnico em PDF das features atuais da LSTM (reports/relatorio-features.pdf).

Uso: python -m src.experiments.relatorio_features
"""

from datetime import date
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.models.dataset import FEATURES, HORIZONS, LOOKBACK, PROCESSED, TARGET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "relatorio-features.pdf"

GRUPOS = [
    ("Retornos logarítmicos", "Yahoo Finance (KC=F), CEPEA/ESALQ, BCB PTAX", [
        ("ret_arabica_1d", "ln P(t) - ln P(t-1) do indicador CEPEA arábica (R$/sc)", "diária"),
        ("ret_arabica_21d", "ln P(t) - ln P(t-21), retorno de ~1 mês", "diária"),
        ("ret_robusta_1d", "log-retorno diário do indicador CEPEA robusta (R$/sc)", "diária"),
        ("ret_ice_1d", "log-retorno diário do futuro Coffee C (ICE NY, cents/lb)", "diária"),
        ("ret_ptax_1d", "log-retorno diário da PTAX venda", "diária"),
    ]),
    ("Posição do preço vs. médias móveis", "CEPEA/ESALQ", [
        ("preco_vs_ma_1m", "P / média móvel 21 d - 1", "diária"),
        ("preco_vs_ma_3m", "P / média móvel 63 d - 1", "diária"),
        ("preco_vs_ma_1a", "P / média móvel 252 d - 1", "diária"),
        ("preco_vs_ma_2a", "P / média móvel 504 d - 1", "diária"),
    ]),
    ("Mercado", "CEPEA, ICE via Yahoo, BCB", [
        ("vol_21d", "desvio-padrão dos retornos diários em 21 d, anualizado (× raiz(252))", "diária"),
        ("spread_arabica_robusta", "P arábica / P robusta (ambos CEPEA, R$/sc)", "diária"),
        ("base_fisico_futuro_pct", "(P físico - F) / F, com F = ICE cents/lb ÷ 100 × 132,277 × PTAX (R$/sc)", "diária"),
    ]),
    ("Calendário e macro", "calendário; BCB SGS 432", [
        ("mes_sin", "sen(2·pi · mês / 12)", "diária"),
        ("mes_cos", "cos(2·pi · mês / 12)", "diária"),
        ("bienalidade_alta", "dummy = 1 se ano-safra par (2020, 2022, 2024…): carga cheia no Brasil; ano-safra começa em julho", "diária"),
        ("selic_meta", "meta Selic do Copom, % a.a.", "diária (ffill)"),
    ]),
    ("Clima nas regiões produtoras", "Open-Meteo (ERA5): Varginha, Patrocínio, Franca, Colatina", [
        ("chuva_arabica_30d", "precipitação acumulada 30 d, média de Sul de Minas, Cerrado e Mogiana (mm)", "diária, calendário civil"),
        ("chuva_arabica_90d", "idem, 90 d", "diária, calendário civil"),
        ("tmin_arabica_7d", "mínima das temperaturas mínimas em 7 d nas três regiões (°C)", "diária"),
        ("geada_30d", "dummy = 1 se Tmin < 3 °C entre maio e setembro em algum dos últimos 30 d", "diária"),
        ("chuva_robusta_90d", "precipitação acumulada 90 d em Colatina, ES (mm)", "diária, calendário civil"),
    ]),
    ("Posicionamento de fundos (COT/CFTC)", "CFTC via cot-reports, ancorado na data de divulgação", [
        ("cot_net_pct_oi", "(long - short) non-commercial / open interest, Coffee C", "semanal (ffill)"),
        ("cot_net_pct_oi_chg4w", "variação de cot_net_pct_oi em 20 dias úteis", "semanal (ffill)"),
    ]),
    ("Insumos agrícolas", "Banco Mundial Pink Sheet, disponível 3 d.u. após o fim do mês", [
        ("indice_troca_urea", "(ureia US$/t × PTAX) / P arábica: sacas para comprar 1 t de ureia", "mensal (ffill)"),
        ("ret_urea_1a", "ln ureia(t) - ln ureia(t-252)", "mensal (ffill)"),
        ("ret_crude_1a", "ln petróleo(t) - ln petróleo(t-252)", "mensal (ffill)"),
    ]),
]

BRUTOS = [
    ("cepea_cafe.csv", "CEPEA/ESALQ, indicadores de café arábica (tipo 6, bebida dura, posto SP) e robusta (ES). Download manual dos XLS do site (bloqueia scraping); módulo src/data/cepea.py.",
     "diária (dias úteis BR)", [
        ("cepea_arabica_brl_sc", "indicador arábica, R$/saca 60 kg"),
        ("cepea_arabica_usd_sc", "indicador arábica, US$/saca"),
        ("cepea_robusta_brl_sc", "indicador robusta, R$/saca"),
        ("cepea_robusta_usd_sc", "indicador robusta, US$/saca")]),
    ("market_yahoo.csv", "Yahoo Finance via yfinance; fechamento ajustado. KC=F = contrato contínuo Coffee C (ICE NY). BRL=X coletado mas não usado (PTAX oficial substitui).",
     "diária (pregões ICE)", [
        ("ice_arabica_cents_lb", "futuro Coffee C, primeiro vencimento, cents de US$/lb"),
        ("usd_brl_yahoo", "câmbio USD/BRL intradiário Yahoo (não usado)")]),
    ("ice_curve.csv", "Yahoo Finance, contratos individuais KC{H,K,N,U,Z}yy.NYB; acumulado a cada coleta porque o Yahoo descarta vencidos. Módulo src/data/futures_curve.py. Usado só no motor de hedge, não na LSTM.",
     "diária, desde out/2023", [
        ("KC*", "fechamento de cada vencimento, cents/lb (uma coluna por contrato)")]),
    ("macro_bcb.csv", "Banco Central do Brasil, API SGS via python-bcb (séries 1 e 432), em blocos de 9 anos.",
     "diária (PTAX em dias úteis; Selic em calendário civil)", [
        ("ptax_venda", "taxa de câmbio PTAX venda, R$/US$"),
        ("selic_meta", "meta Selic definida pelo Copom, % a.a.")]),
    ("clima_openmeteo.csv", "Open-Meteo Archive API (reanálise ERA5), 4 pontos: Varginha (-21,55; -45,43), Patrocínio (-18,94; -46,99), Franca (-20,54; -47,40), Colatina (-19,54; -40,63). Módulo src/data/clima.py.",
     "diária (calendário civil)", [
        ("tmin_*", "temperatura mínima a 2 m, °C, por região"),
        ("prec_*", "precipitação acumulada no dia, mm, por região")]),
    ("cot_cftc.csv", "CFTC, relatório Commitments of Traders (legacy, futures only) via cot-reports, filtrado em COFFEE C. report_date = terça de referência; available_date = +3 d.u. (sexta de divulgação), usado no merge.",
     "semanal", [
        ("noncomm_long", "contratos comprados por non-commercials (fundos)"),
        ("noncomm_short", "contratos vendidos por non-commercials"),
        ("open_interest", "contratos em aberto"),
        ("cot_net_noncomm", "long - short"),
        ("cot_net_pct_oi", "(long - short) / open interest")]),
    ("insumos_pinksheet.csv", "Banco Mundial, Commodity Markets (Pink Sheet) mensal, planilha CMO-Historical-Data-Monthly.xlsx. month = mês de referência; available_date = 3 d.u. após o fim do mês. DAP e KCl coletados mas não usados.",
     "mensal", [
        ("urea_usd_ton", "ureia, US$/t"),
        ("dap_usd_ton", "fosfato diamônico, US$/t (não usado)"),
        ("kcl_usd_ton", "cloreto de potássio, US$/t (não usado)"),
        ("crude_usd_bbl", "petróleo bruto, média Brent/WTI/Dubai, US$/barril")]),
]
EXTERNAL = [
    ("cepea-consulta-{diaria,mensal,anual}-{arabica,robusta}-{1986,2006}.xls", "XLS originais do CEPEA (origem de cepea_cafe.csv)"),
    ("conab_serie_historica_custos_cafe_arabica_2003a2025.xls", "CONAB/GECUP, série histórica de custos de produção do café arábica por município e ano"),
    ("conab_coe_cot_cafe_arabica_mg.csv", "extração: COE (custo variável), COT (custo operacional) e CT (custo total), R$/saca, Guaxupé, Patrocínio, Manhuaçu, Três Pontas, Franca"),
]


def fmt(v):
    return f"{v:,.0f}".replace(",", ".") if abs(v) >= 1000 else f"{v:.4g}"


def secao_brutos(S, h2, body, small, cell, cellb):
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    S.append(Paragraph("2. Dados brutos coletados (data/raw)", h2))
    S.append(Paragraph("Arquivos como saem da coleta (python -m src.data.collect), antes de qualquer alinhamento ou transformação. "
                       "Período e estatísticas calculados sobre o arquivo atual; n = observações não nulas.", body))
    for arq, fonte, freq, cols in BRUTOS:
        d = pd.read_csv(ROOT / "data" / "raw" / arq)
        dcol = "date" if "date" in d.columns else "available_date"
        dt = pd.to_datetime(d[dcol])
        S.append(Spacer(1, 4))
        S.append(Paragraph(f"<b>{arq}</b> &nbsp;·&nbsp; {len(d)} linhas &nbsp;·&nbsp; {dt.min():%d/%m/%Y} a {dt.max():%d/%m/%Y} &nbsp;·&nbsp; frequência: {freq}", body))
        S.append(Paragraph("Fonte: " + fonte, small))
        data = [[Paragraph(c, cellb) for c in ["Coluna", "Conteúdo", "n", "Média", "Mín.", "Máx."]]]
        num = d.select_dtypes("number")
        for nome, desc in cols:
            sel = [c for c in num.columns if c.startswith(nome[:-1])] if nome.endswith("*") else [nome]
            for c in sel:
                x = num[c].dropna()
                data.append([Paragraph(c, cell), Paragraph(desc, cell), Paragraph(str(len(x)), cell),
                             Paragraph(fmt(x.mean()), cell), Paragraph(fmt(x.min()), cell), Paragraph(fmt(x.max()), cell)])
        t = Table(data, colWidths=[4.2 * cm, 7.3 * cm, 1.3 * cm, 1.6 * cm, 1.6 * cm, 1.6 * cm], repeatRows=1)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (2, 1), (-1, -1), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
        S.append(t)
    S.append(Spacer(1, 6))
    S.append(Paragraph("<b>data/external</b> (arquivos manuais, não gerados pela coleta)", body))
    data = [[Paragraph("Arquivo", cellb), Paragraph("Conteúdo", cellb)]]
    for a, dsc in EXTERNAL:
        data.append([Paragraph(a, cell), Paragraph(dsc, cell)])
    t = Table(data, colWidths=[7.5 * cm, 10 * cm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    S.append(t)
    S.append(Spacer(1, 6))
    from reportlab.platypus import KeepTogether
    S.append(KeepTogether([Paragraph("3. Alinhamento (src/features/build_features.py)", h2), Paragraph("Os brutos são unidos num calendário diário a partir de 08/11/2001 (início do robusta). As features de clima são calculadas ainda no calendário civil. "
                       "Em seguida o dataset é recortado para os dias com indicador CEPEA arábica (dias úteis brasileiros) e as demais fontes são preenchidas com o último valor conhecido (ffill). "
                       "COT e Pink Sheet entram pela data de divulgação, não pela de referência. Depois das médias móveis de 504 dias e dos retornos de 252 dias dos insumos, o dataset efetivo começa em 07/12/2005. "
                       "O futuro ICE é convertido para R$/saca por cents/lb ÷ 100 × 132,277 × PTAX.", body)]))


def main():
    df = pd.read_csv(PROCESSED / "dataset_diario.csv", index_col="date", parse_dates=True)
    assert [f for g in GRUPOS for f, _, _ in g[2]] == list(FEATURES), "lista do relatório difere de dataset.FEATURES"
    treino = df.loc[:"2022-06-30", FEATURES]
    stats = treino.describe().T[["mean", "std", "min", "max"]]

    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=18, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5, leading=13, alignment=TA_LEFT)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10)
    cell = ParagraphStyle("cell", parent=body, fontSize=8, leading=10)
    cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="Agro Visible: dados e features", author="Agro Visible")
    S = []
    S.append(Paragraph("Agro Visible: dados coletados e features da LSTM", h1))
    S.append(Paragraph(f"Relatório técnico gerado em {date.today():%d/%m/%Y} a partir de <b>src/models/dataset.py</b> e <b>src/features/build_features.py</b>. "
                       f"Dataset: <b>data/processed/dataset_diario.csv</b>, {len(df)} linhas (dias úteis com indicador CEPEA), "
                       f"{df.index.min():%d/%m/%Y} a {df.index.max():%d/%m/%Y}.", body))
    S.append(Spacer(1, 8))

    S.append(Paragraph("1. Resumo", h2))
    S.append(Paragraph(
        f"<b>{len(FEATURES)} features</b>, todas estacionárias ou limitadas por construção, organizadas em 7 grupos. "
        f"Entrada da rede: janela de <b>{LOOKBACK} dias úteis</b> × {len(FEATURES)} features. "
        f"Alvo: log-retorno futuro do indicador CEPEA arábica (<b>{TARGET}</b>) em <b>{', '.join(str(h) for h in HORIZONS)} dias úteis</b> "
        f"(cerca de 1, 3 e 6 meses), y<sub>h</sub>(t) = ln P(t+h) - ln P(t). "
        "Normalização: StandardScaler ajustado apenas no treino (até 30/06/2022) e aplicado a validação e teste; não há normalização em janela deslizante. "
        "Não há lags explícitos além dos que a janela de 63 dias fornece. "
        "Alinhamento: calendário de dias úteis do CEPEA; fontes de menor frequência preenchidas com o último valor conhecido (ffill), nunca com valores futuros. "
        "COT e Pink Sheet são ancorados na data de divulgação, não na de referência.", body))

    secao_brutos(S, h2, body, small, cell, cellb)
    S.append(Paragraph("4. Features por grupo", h2))
    for nome, fonte, feats in GRUPOS:
        S.append(Paragraph(f"<b>{nome}</b> &nbsp;·&nbsp; fonte: {fonte}", body))
        data = [[Paragraph("Feature", cellb), Paragraph("Definição", cellb), Paragraph("Frequência", cellb)]]
        for f, d, fr in feats:
            data.append([Paragraph(f"<b>{f}</b>", cell), Paragraph(d, cell), Paragraph(fr, cell)])
        t = Table(data, colWidths=[4.3 * cm, 10.2 * cm, 3.0 * cm], repeatRows=1)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
        S.append(t); S.append(Spacer(1, 6))

    S.append(PageBreak())
    S.append(Paragraph("5. Estatísticas descritivas das features no treino (07/12/2005 a 30/06/2022)", h2))
    S.append(Paragraph("Valores brutos antes da padronização. Média e desvio são os parâmetros do StandardScaler.", small))
    data = [[Paragraph(c, cellb) for c in ["Feature", "Média", "Desvio", "Mín.", "Máx."]]]
    for f in FEATURES:
        r = stats.loc[f]
        data.append([Paragraph(f, cell)] + [Paragraph(f"{v:.4g}", cell) for v in [r["mean"], r["std"], r["min"], r["max"]]])
    t = Table(data, colWidths=[5.5 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                           ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 4)]))
    S.append(t)

    S.append(Paragraph("6. Observações de engenharia", h2))
    for txt in [
        "O alvo é o log-retorno, não o nível de preço: evita que a rede aprenda a não-estacionariedade da série; o preço é reconstruído por P(t+h) = P(t)·exp(y<sub>h</sub> previsto).",
        "A base físico × futuro é modelada em percentual do futuro porque em reais ela escala com o nível de preço.",
        "As features de clima são calculadas no calendário civil completo antes do recorte para dias úteis, para não perder chuva de fins de semana e feriados.",
        "O início efetivo do dataset (dez/2005) decorre das médias móveis de 504 dias e dos retornos de 252 dias dos insumos.",
        "Ablação (reports/experimentos/c3_ablacao.csv): remover mercado ou calendário/Selic piora o erro de 126 dias em 10–12 %; remover retornos/médias móveis, COT ou insumos melhora o erro, o que indica sobreajuste do modelo completo e candidatos a poda.",
        "<b>Achado: geada_30d é constante igual a zero em toda a série</b> (2005–2026). A reanálise ERA5 nos quatro pontos de grade nunca registra Tmin abaixo de 3 °C entre maio e setembro (mínimo de 3,0 °C em 2021); o StandardScaler deixa a coluna com escala 1 e ela não contribui para o modelo. A geada de julho de 2021, que o split de treino deveria conter, não aparece. Correções possíveis: limiar de 5 °C ou anomalia de Tmin em relação à climatologia do dia, ambos a validar na ablação.",
        "Pendentes, discutidos mas não implementados: estoques certificados ICE, estimativas de safra CONAB, balanço USDA/ICO, exportações Cecafé, anomalia climática por fase fenológica e retorno implícito na curva de futuros como feature.",
    ]:
        S.append(Paragraph("• " + txt, body))
    doc.build(S)
    print("gerado:", OUT)


if __name__ == "__main__":
    main()
