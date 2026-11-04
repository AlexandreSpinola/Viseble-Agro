"""Gera reports/anexo-experimentos.md a partir dos CSVs de reports/experimentos
e o anexa (substituindo a versão anterior) ao fim de reports/dossie-tecnico.md.

Uso: python -m src.experiments.anexo
"""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HORIZONS = (21, 63, 126)

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "reports" / "experimentos"
DOSSIE = ROOT / "reports" / "dossie-tecnico.md"
ANEXO = ROOT / "reports" / "anexo-experimentos.md"
MARCA = "\n\n<!-- ANEXO-EXPERIMENTOS -->\n"


def md(df: pd.DataFrame, index: bool = False, dec: int = 1) -> str:
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.{dec}f}")
    if index:
        d = d.reset_index()
    cols = list(d.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        out.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join(out)


def rd(nome: str, **kw) -> pd.DataFrame:
    return pd.read_csv(E / f"{nome}.csv", **kw)


def main():
    hoje = date.today().strftime("%d/%m/%Y")
    S = [f"# Anexo: resultados dos experimentos pedidos em `pedidos-para-experimentos.md`\n\nExecutados em {hoje}. Arquivos-fonte em `reports/experimentos/`, figuras em `reports/figures/`. Salvo indicação, o caso base é: armazenagem 2,50 R$/sc/mês, quebra 0,2 %/mês, COE 700 R$/sc, taxa de desconto 10 % a.a., λ = 0, hedge habilitado, 20 datas de decisão mensais de 01/07/2024 a 03/02/2026 (teste cego). **Modelo final: LSTM(32)→LSTM(16), dropout 0,4**, adotado em 04/11/2026 após a busca de hiperparâmetros (Bloco F); todos os blocos abaixo foram reexecutados com ele. A configuração anterior (64 unidades, dropout 0,2) é mantida no Bloco F para comparação. **Nota:** o caso base usa taxa fixa de 10 % a.a."]

    # ---------------- Bloco A
    S.append("\n## Bloco A: RQ3\n\n### A1. Sensibilidade à Selic\n")
    a1 = rd("a1_selic")
    S.append(md(a1))
    vig = rd("a1_selic_vigente_por_data")
    S.append("\nSelic vigente por data (linha \"vigente\"): " + ", ".join(f"{d[:7]}: {v:.2f} %" for d, v in zip(vig.data_decisao, vig["selic_usada_%"])) + ".")
    S.append("\nLeitura: a taxa de desconto entre 8 % e 15 % move a receita do Agro Visible em menos de 5 R$/sc e **não altera nenhuma ação** nas 20 datas. O efeito é maior na venda parcelada (−31 R$/sc), porque ela sempre carrega parte da produção por 6 meses.")

    S.append("\n### A2. Choque de base\n")
    S.append(md(rd("a2_choque_base")))
    S.append("\nLeitura: com λ = 0 a base esperada e o risco de base **não mudam nenhuma decisão**, porque o hedge nunca é competitivo com curva plana (backtest) em backwardation. Com λ > 0 as mudanças de ação vêm da aversão a risco sobre o armazenamento descoberto, não do risco de base. A frequência de hedge é zero em todos os cenários; o hedge só passa a ser escolhido com a curva real por vencimento (recomendação atual, seção 3.4 do dossiê).")

    S.append("\n### A3. Sensibilidade ao COE (benchmark de meta de margem)\n")
    S.append(md(rd("a3_coe")))
    S.append("\nLeitura: com COE ≤ 900 R$/sc a meta de margem (COE·1,3) coincide com a venda imediata em todas as datas do teste, porque o preço nunca esteve abaixo de 1 170 R$/sc. Só com COE = 1 100 a heurística difere em 2 datas. O motor Agro Visible não muda porque o COE não entra na política (ver D1). Com o COE real da CONAB (D2) o quadro no período de validação é diferente: 7 de 18 datas.")

    S.append("\n### A4. Grade λ × armazenagem (12 combinações)\n")
    a4 = rd("a4_grade_lambda_armazenagem")
    S.append(md(a4[["lambda", "armazenagem", "receita_media_R$/sc", "ganho_vs_imediata_%", "vence_imediata_%", "captura_oraculo_%", "desvio_padrao", "freq_armazenar_%"]], dec=2))
    S.append("\nFigura: `reports/figures/09_sensibilidade_lambda_armazenagem_selic.png`.")

    # ---------------- Bloco B
    S.append("\n## Bloco B: amostra e integridade do backtest (RQ2)\n\n### B1. Backtest no período de validação e consolidado por safra\n")
    ps = rd("b1_por_safra")
    ps["safra"] = ps["safra"].map(lambda a: f"{a}/{str(a + 1)[-2:]}")
    S.append(md(ps))
    S.append("\n**Nota de viés:** nas safras 2022/23 e 2023/24 (validação) o σ residual da LSTM e o early stopping foram calibrados com os próprios dados; as estatísticas de base já são só de treino. Há viés favorável leve à LSTM nessas duas safras. A safra 2023/24 da validação tem 6 datas (jul–dez/2023) porque o alvo de 126 dias precisa existir dentro do período.\n\nResumo na validação (18 datas, 01/07/2022 a 05/12/2023):\n")
    r = rd("b1_resumo_validacao"); r.columns = ["estratégia", *r.columns[1:]]
    S.append(md(r, dec=2))
    S.append("\nResumo consolidado, 4 safras (38 datas):\n")
    r = rd("b1_resumo_4_safras"); r.columns = ["estratégia", *r.columns[1:]]
    S.append(md(r, dec=2))

    S.append("\n### B2. Estatística de comparação pareada\n")
    b2 = rd("b2_estatistica_pareada"); S.append(md(b2, dec=3))
    S.append("\nIC 95 % por bootstrap de 10 000 reamostragens da média das diferenças; p-valor do teste de Wilcoxon pareado (zeros divididos). Leitura: " + "; ".join(f"{r.amostra} (n = {int(r.n)}), {r.comparacao}: média {r.media:+.0f} R$/sc, IC [{r.ic95_inf:+.0f}; {r.ic95_sup:+.0f}], p = {r.p_wilcoxon:.3f}" for r in b2.itertuples()) + ". Diferenças com p < 0,05 são significativas a 5 %; os intervalos excluem o zero mas são largos. A fração de datas positivas contra a venda imediata é baixa porque na maioria das datas o motor vende de imediato e a diferença é exatamente zero (mediana nula).\n\nFração do ganho do oráculo capturada, (estratégia − imediata)/(oráculo − imediata), média sobre as datas em que o oráculo supera a imediata em mais de 1 %:\n")
    t = rd("b1_backtest_todos", index_col=0, parse_dates=True)
    est = ["venda_parcelada", "media_movel_3m", "meta_margem_coe", "hedge_ate_o_fim", "lstm_dp"]
    cap = {}
    for nome, bt in [("teste", t[t.periodo == "teste"]), ("teste+validação", t)]:
        m = (bt.oraculo / bt.venda_imediata - 1) > 0.01
        g = bt.loc[m, est].sub(bt.loc[m, "venda_imediata"], axis=0).div(bt.loc[m, "oraculo"] - bt.loc[m, "venda_imediata"], axis=0) * 100
        cap[f"{nome} (n={int(m.sum())})"] = g.mean().round(1)
    S.append(md(pd.DataFrame(cap), index=True))
    S.append("\nPor data: `b2_captura_por_data_teste.csv` e `b2_captura_por_data_teste_validação.csv` (atenção: nesses arquivos a divisão fica instável quando oráculo ≈ imediata; usar a tabela acima).")

    S.append("\n### B3. Decomposição do ganho por data\n")
    b3 = rd("b3_decomposicao", index_col=0)
    b3.index = [d[:10] for d in b3.index]
    cols = ["periodo", "lstm_dp_acao", "lstm_dp_mes_venda", "lstm_dp", "venda_imediata", "oraculo", "ganho_vs_imediata_%", "y_21d", "ret_real_21d", "y_63d", "ret_real_63d", "y_126d", "ret_real_126d"]
    S.append(md(b3[cols].round(3), index=True, dec=3))
    S.append("\nArquivo completo com flags de acerto direcional: `b3_decomposicao.csv`. Leitura (gerada dos dados): maiores ganhos sobre a venda imediata: " + ", ".join(f"{d} ({v:+.1f} %)" for d, v in b3["ganho_vs_imediata_%"].nlargest(6).items()) + "; maiores perdas: " + ", ".join(f"{d} ({v:+.1f} %)" for d, v in b3["ganho_vs_imediata_%"].nsmallest(3).items()) + ". Armazenou em " + str(int((b3.lstm_dp_acao != "VENDER").sum())) + " das " + str(len(b3)) + " datas; dessas, ganhou em " + str(int(((b3.lstm_dp_acao != "VENDER") & (b3["ganho_vs_imediata_%"] > 0)).sum())) + " e perdeu em " + str(int(((b3.lstm_dp_acao != "VENDER") & (b3["ganho_vs_imediata_%"] < 0)).sum())) + ". Os ganhos vêm de previsões de alta de 21 dias corretas em direção, seguidas de reavaliação mensal; as perdas, de previsões de alta em quedas persistentes. Em jul–out/2024 a previsão de 126 dias era próxima de zero ou negativa enquanto o retorno realizado foi de +0,5: a alta foi capturada pela direção de curto prazo e pela política rolante, não pela previsão longa.")

    # ---------------- Bloco C
    S.append("\n## Bloco C: componente preditivo (RQ1)\n\n### C1. Notebook 03 reexecutado com retreino\n\nRetreino do zero (seed 42, CPU) com a configuração final; as métricas de validação coincidem com as da busca de hiperparâmetros (F4, seed 42), confirmando reprodutibilidade. σ residual regravado em `models/residual_sigma.json`. Figuras regravadas: `02_curva_perda.png`, `03_previsto_realizado_validacao.png`, `03_previsto_realizado_teste.png`, `03b_residuos.png`.\n\n### C2. Métricas na validação e no teste\n")
    c2 = rd("c2_metricas_val_teste")
    S.append(md(c2, dec=4))
    def cmp(split, h, a, b):
        r = c2[(c2.split == split) & (c2.horizonte == f"{h}d")].iloc[0]
        return "vence" if r[a] < r[b] else "perde para"
    S.append("\nLeitura (gerada dos dados): na validação a LSTM " + ", ".join(f"{cmp('val', h, 'rmse_ret', 'rmse_naive')} o passeio aleatório em {h} d" for h in HORIZONS)
             + "; e " + ", ".join(f"{cmp('val', h, 'rmse_ret', 'rmse_curva')} a curva de futuros em {h} d" for h in HORIZONS)
             + ". No teste (417 amostras) a LSTM " + ", ".join(f"{cmp('test', h, 'rmse_ret', 'rmse_naive')} o passeio aleatório em {h} d" for h in HORIZONS)
             + "; e " + ", ".join(f"{cmp('test', h, 'rmse_ret', 'rmse_curva')} a curva em {h} d" for h in HORIZONS) + ".")
    S.append("\n### C4. Baseline ARIMA\n")
    c4 = rd("c4_arima")
    S.append(md(c4, dec=4))
    S.append("\nOrdem (1,1,2) escolhida por AIC no treino entre p, q ∈ {0,1,2}; parâmetros fixos, aplicados à série até cada data e previsão recursiva. Leitura: o ARIMA é **indistinguível do passeio aleatório** (RMSE igual até a 3ª casa, acerto direcional ≈ 50 %), como esperado para log-preço diário quase integrado. Serve como confirmação de que o passeio aleatório é o baseline estatístico clássico adequado.")

    S.append("\n### C5. Variabilidade entre seeds (modelo completo)\n")
    c5 = rd("c5_seeds")
    cols5 = ["seed", "epocas", "tempo_s", "rmse_21d", "rmse_63d", "rmse_126d", "dir_21d", "dir_63d", "dir_126d"]
    S.append(md(c5[cols5], dec=4))
    agg = c5[cols5[3:]].agg(["mean", "std"]).T; agg.columns = ["média", "desvio"]
    S.append("\n" + md(agg.round(4), index=True, dec=4))
    S.append(f"\nLeitura: o desvio entre seeds do RMSE é de {agg.loc['rmse_21d','desvio']:.3f} (21 d), {agg.loc['rmse_63d','desvio']:.3f} (63 d) e {agg.loc['rmse_126d','desvio']:.3f} (126 d); médias {agg.loc['rmse_21d','média']:.3f} / {agg.loc['rmse_63d','média']:.3f} / {agg.loc['rmse_126d','média']:.3f}. Comparar com os baselines na validação (C2): toda diferença menor que um desvio entre seeds deve ser tratada como empate.")

    S.append("\n### C3. Ablação por grupo de features\n")
    if (E / "c3_ablacao.csv").exists():
        c3 = rd("c3_ablacao")
        g = c3.groupby("config")[["rmse_21d", "rmse_63d", "rmse_126d", "dir_21d", "dir_63d", "dir_126d"]].agg(["mean", "std"])
        g.columns = [f"{a}_{b}" for a, b in g.columns]
        ordem = ["completo", *[c for c in g.index if c != "completo"]]
        g = g.loc[[o for o in ordem if o in g.index]]
        n = c3.groupby("config").size(); g.insert(0, "n_seeds", n)
        S.append(md(g.round(4), index=True, dec=4))
        base = g.loc["completo"]
        rel = pd.DataFrame({h: (g[f"rmse_{h}_mean"] / base[f"rmse_{h}_mean"] - 1) * 100 for h in ["21d", "63d", "126d"]})
        rel.columns = [f"ΔRMSE {h} vs completo (%)" for h in ["21d", "63d", "126d"]]
        S.append("\nVariação relativa do RMSE médio (3 seeds: 42, 43, 44; positivo = piorou ao remover o grupo):\n")
        S.append(md(rel.round(1), index=True))
        S.append("\nGrupos: (a) retornos e posição vs. média; (b) mercado: vol, spread, base; (c) calendário e Selic; (d) clima; (e) fundos COT; (f) insumos. Leitura (modelo final de 32 un., 3 seeds): (1) o desvio entre seeds do modelo completo é de 18 % do RMSE em 21 d, 7 % em 63 d e 23 % em 126 d, então em 126 d só efeitos acima de ~20 % ficam claramente fora do ruído. (2) Remover **calendário e Selic (c)**, **mercado (b)** ou **retornos e médias móveis (a)** piora o RMSE de 126 d em 38 %, 26 % e 22 % e derruba o acerto direcional de 126 d de 81 % para 61–72 %: são os grupos que carregam o sinal de longo prazo. (3) Clima (d) e fundos COT (e) pioram 126 d em 13 % e 5 % ao serem removidos, dentro ou perto do ruído: contribuição marginal. (4) Remover **insumos (f)** melhora 126 d em 7 %: nesta configuração e com estes hiperparâmetros o grupo não contribuiu; não generalizar. (5) Em 21 d nenhum grupo ajuda (remover qualquer um muda o RMSE em menos de 6 %, para melhor ou para pior). Conclusão para o texto: cinco dos seis grupos contribuem no horizonte de 6 meses, com calendário/Selic, mercado e retornos como essenciais; em 21 d a rede não extrai sinal de nenhum grupo.")
    else:
        S.append("\n*(em execução; ver `reports/experimentos/retreinos.log`)*")

    # ---------------- Bloco D
    S.append("\n## Bloco D: uso do COE no motor\n\n### D1. Decisão de projeto\n\n**Implementadas as duas formas; a forma (ii) fica desligada por padrão.**\n\n- (i) sinalização: `Recomendacao.margem_sobre_coe_pct` já é calculada em toda recomendação. A classificação nas faixas do AgroSafety (lucro supernormal / normal / resíduo / descapitalização / falência) pode ser lida diretamente comparando o preço esperado com COE, COT e CT da tabela D2.\n- (ii) restrição: parâmetro `Custos.margem_min_coe` (padrão `None`). Quando definido, VENDER só é permitido em nós com preço ≥ COE·(1+m) enquanto houver prazo; no último mês a venda é forçada.\n\nPor que (ii) fica desligada: a restrição só muda a decisão quando o preço está abaixo de COE·(1+m), e nesse caso ela força o produtor a carregar o café exatamente quando o modelo prevê queda, o que não é uma política racional de venda, e sim uma regra de sobrevivência. Backtest no teste com COE placeholder:\n")
    S.append(md(rd("d1_restricao_coe")))
    S.append("\nCom COE = 700 ou 1 100 e m até 30 %, nenhuma data do teste tem preço abaixo do gatilho (mínimo de 1 362 R$/sc), então a restrição não atua; a única mudança (COE 1 100, m = 30 %, gatilho 1 430) ocorre em 1 data e melhora 5 R$/sc por acaso.")

    S.append("\n### D2. COE real (CONAB)\n\nArquivo baixado: `data/external/conab_serie_historica_custos_cafe_arabica_2003a2025.xls` (CONAB/DIPAI/SUINF/GECUP, série histórica de custos de produção do café arábica). Extração em `data/external/conab_coe_cot_cafe_arabica_mg.csv`. Correspondência com a nomenclatura AgroSafety: **COE = Custo Variável (A+B+C)**, **COT = Custo Operacional (D+G)**, **CT = Custo Total (H+I)**, todos em R$/saca de 60 kg. As planilhas de MG são de agricultura familiar, cultivo semi-adensado, alta tecnologia, semimecanizado.\n")
    cn = pd.read_csv(ROOT / "data" / "external" / "conab_coe_cot_cafe_arabica_mg.csv")
    cn = cn[cn.ano >= 2021][["municipio", "ano", "COE_custo_variavel_rs_sc", "COT_custo_operacional_rs_sc", "CT_custo_total_rs_sc"]]
    cn.columns = ["município", "ano", "COE", "COT", "CT"]
    S.append(md(cn, dec=2))
    S.append("\nValores usados no motor (Guaxupé, safra = ano da colheita): 2022: 766,34; 2023: 714,29; 2024: 783,79; 2025: 876,06 R$/sc. Guaxupé 2022 e 2023 e Patrocínio 2022 não têm COT/CT na planilha (só o resumo do custo variável). O placeholder de 700 estava dentro da faixa.\n\nBacktest com COE da CONAB por safra (`d2_coe_conab.csv`):\n")
    S.append(md(rd("d2_coe_conab")))
    S.append("\nNo teste nada muda, porque a margem mínima observada sobre o COE foi de " + f"{rd('d2_coe_conab')['margem_sobre_coe_min_%'].iloc[0]:+.0f} %" + ". Na **validação** (" + (lambda v: f"{len(v)} datas, preços de {v.preco_inicial.min():.0f} a {v.preco_inicial.max():.0f}) a meta de margem COE·1,3 passa a diferir da venda imediata em {int((v.meta_margem_coe - v.venda_imediata).abs().gt(1e-6).sum())} de {len(v)} datas, com média de {v.meta_margem_coe.mean():.0f} contra {v.venda_imediata.mean():.0f} R$/sc")(rd("d2_backtest_validacao_coe_conab")) + ".")

    # ---------------- Bloco E
    S.append("\n## Bloco E: informações para o texto\n\n### E1. Fontes dos parâmetros de armazenagem e quebra\n\nOs 2,50 R$/sc/mês e os 0,2 %/mês **foram estimativas do desenvolvimento, sem documento de referência**. Devem ser citados como valores de referência a confirmar com cooperativa. A própria CONAB traz \"Despesas de armazenagem\" na planilha (Guaxupé 2024: 1,74 R$/sc para a safra inteira, dentro do custo de produção), mas isso é o custo do armazém da fazenda, não o de armazém geral por mês. A análise de sensibilidade A4 mostra que a decisão é insensível a esse parâmetro entre 1,5 e 5,0.\n\n### E2. Custo operacional de bolsa\n\nOs 10 R$/sc **não foram calculados a partir de TOB, emolumentos e taxa de registro**. Foram tomados diretamente do exemplo do módulo 5 do AgroSafety (\"Custo Operacional B3: R$ 10,00 por saca – Entrada e Saída\", slides 52 e 73). O material não detalha a composição.\n\n### E3. Hiperparâmetros\n\nA configuração inicial (unidades 64/32, dropout 0,2, janela de 63 dias, batch 32, Adam 1e-3, paciência 15 e 7) foi fixada a priori. A busca do Bloco F (F4: 12 configurações com seed 42; F5: 3 candidatas com 5 seeds em validação e teste) levou à configuração final de 32/16 unidades com dropout 0,4; janela, batch, taxa e paciências ficaram iguais. A janela de 63 dias cobre um trimestre, igual ao horizonte intermediário. A seleção foi feita na validação; o teste permaneceu cego, mas a escolha de arquitetura e o early stopping não são cegos (ameaça interna declarada no TCC).\n\n### E4. Tempos de execução (CPU, Windows 11, TensorFlow sem GPU)\n")
    e4 = rd("e4_tempos")
    S.append(f"- Treino do modelo final (seed 42, {int(c5.loc[c5.seed == 42, "epocas"].iloc[0])} épocas, 3 940 amostras): **{c5.loc[c5.seed == 42, 'tempo_s'].iloc[0]:.0f} s**; retreinos de C5 entre {c5.tempo_s.min():.0f} e {c5.tempo_s.max():.0f} s.\n- Motor de decisão para uma data (7 camadas × 121 nós, com hedge): **{e4.motor_1_data_s.iloc[0] * 1000:.0f} ms**.\n- Backtest de 20 datas com política rolante (≈ 120 resoluções do motor + previsões em lote): **{e4.backtest_20_datas_s.iloc[0]:.1f} s**.\n- Grade de sensibilidade A4 (12 backtests): ~1 min. Retreinos de C3+C5 (23 treinos): ~35 min.")

    S.append("\n### E5. Versões\n\n| Biblioteca | Versão |\n|---|---|\n| Python | 3.13.4 |\n| TensorFlow | 2.21.0 |\n| Keras | 3.15.1 |\n| NumPy | 2.5.2 |\n| pandas | 3.0.5 |\n| scikit-learn | 1.9.0 |\n| SciPy | 1.18.1 |\n| statsmodels | 0.15.0 (adicionado para C4) |\n| networkx | 3.6.1 |\n| matplotlib | 3.11.1 |\n| yfinance | 1.7.0 |\n| cot-reports | 0.1.3 |\n| python-bcb, openmeteo-requests | sem `__version__` exposto; ver `pip freeze` |\n\n`requirements.txt` está sem versões fixadas (pip instala a mais recente). Recomendação: gerar `requirements.lock` com `pip freeze` antes da entrega. `statsmodels` foi adicionado ao ambiente e deve entrar no `requirements.txt`.")

    S.append("\n### E6. Figuras\n\n| # | Figura | Arquivo | Status |\n|---|---|---|---|\n| 1 | Série CEPEA 2005–2026 com cortes | `01_serie_cepea_particao.png` | gerada |\n| 2 | Curva de perda treino × validação | `02_curva_perda.png` | gerada (notebook 03) |\n| 3 | Previsto × realizado por horizonte | `03_previsto_realizado_validacao.png`, `03_previsto_realizado_teste.png`, `03b_residuos.png` | geradas |\n| 4 | Cone de preços (mediana, q10–q90) | `04_cone_precos.png` | gerada (31/08/2026) |\n| 5 | Árvore reduzida com ações | `05_arvore_decisoes.png` | gerada |\n| 6 | Gatilho de venda por mês | `06_gatilho_venda_por_mes.png` | gerada |\n| 7 | Receita por data, safras separadas | `07_receita_por_data_teste.png` | gerada |\n| 8 | Base % com média sazonal | `08_base_fisico_futuro_pct.png` | gerada |\n| 9 | Sensibilidade λ × armazenagem e Selic | `09_sensibilidade_lambda_armazenagem_selic.png` | gerada (mapa de calor + curva de Selic; base não entra porque não altera nada) |\n\nTodas em PNG a 300 dpi, fundo branco, rótulos em português. Além destas, o notebook 05 gera as figuras da simulação por safra.")

    # ---------------- Bloco F: EDA e hiperparâmetros
    S.append("\n## Bloco F: análise exploratória das features e busca de hiperparâmetros\n\n### F1. Correlação de Spearman feature × log-retorno futuro (treino)\n\nArquivo `eda_corr_alvo.csv`; figura `10_corr_features_alvo.png`. Ordenado pelo maior |ρ| entre os horizontes.\n")
    cc = rd("eda_corr_alvo", index_col=0)[["spearman_21d", "spearman_63d", "spearman_126d"]]
    cc = cc.loc[cc.abs().max(axis=1).sort_values(ascending=False).index]
    S.append(md(cc.round(3), index=True, dec=3))
    S.append("\nLeitura: o sinal está em oferta (chuva acumulada 30/90 d, Tmin), base físico×futuro, calendário e Selic, e cresce de 21 para 63/126 d. Retornos diários e de 21 d, posição vs. médias de 1 e 3 meses e volatilidade têm |ρ| < 0,04 em todos os horizontes. `geada_30d` é constante (zero) e foi excluída.")
    S.append("\n### F2. Pares de features com |ρ| > 0,7 (colinearidade)\n")
    S.append(md(rd("eda_pares_colineares").round(3)))
    S.append("\nFigura `11_matriz_corr_features.png`. Clima e calendário medem em parte a mesma coisa (estação); médias de 1 e 2 anos e retorno de 21 d vs. média de 1 mês são quase redundantes.")
    S.append("\n### F3. Importância por permutação na LSTM final (validação)\n\nAumento do RMSE ao embaralhar a feature na janela (média de 3 permutações). Arquivo `eda_importancia_permutacao.csv`; figura `12_importancia_permutacao.png`.\n")
    S.append(md(rd("eda_importancia_permutacao", index_col=0).round(4), index=True, dec=4))
    S.append("\n### F4. Busca de hiperparâmetros (seed 42, validação)\n\nGrade de 12 configurações, um fator por vez a partir da configuração inicial (64 un., dropout 0,2, janela 63, lr 1e-3, batch 32) mais duas candidatas enxutas. Arquivo `hp_busca.csv`.\n")
    hp = rd("hp_busca")[["units", "dropout", "lookback", "lr", "batch", "epocas", "rmse_treino", "rmse_21d", "rmse_63d", "rmse_126d", "rmse_medio", "dir_126d"]].sort_values("rmse_medio")
    S.append(md(hp.round(4), dec=4))
    S.append("\nLeitura: só o tamanho da rede importa de forma consistente; 128 unidades é a pior configuração e 32 a melhor. Janela de 21 ou 126 dias, batch 64 e taxas de 3e-4 ou 3e-3 não ajudam; dropout 0 piora. O RMSE de treino da configuração inicial (0,029) contra 0,047 da enxuta mostra que a redução de capacidade reduz o sobreajuste.")
    S.append("\n### F5. Verificação das candidatas com 5 seeds (42–46), validação e teste\n\nArquivo `hp_seeds.csv`. Média ± desvio entre seeds.\n")
    hs = rd("hp_seeds")
    g = hs.groupby(["units", "dropout", "split"])[["rmse_21d", "rmse_63d", "rmse_126d", "dir_126d"]].agg(["mean", "std"]).round(4)
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    S.append(md(g, index=True, dec=4))
    cvb = hs.groupby("split")[["rmse_curva_21d", "rmse_curva_63d", "rmse_curva_126d", "rmse_naive_21d", "rmse_naive_63d", "rmse_naive_126d"]].first().round(4)
    S.append("\nBaselines nos mesmos conjuntos:\n")
    S.append(md(cvb, index=True, dec=4))
    S.append("\nLeitura: (1) o resultado de seed única (RMSE médio 0,130) foi uma seed favorável; com 5 seeds a rede de 32 un./dropout 0,4 melhora a inicial em 5–8 % em 21 e 63 d e 19 % em 126 d na validação, e 2–8 % no teste, com variância igual ou menor. (2) Em 21 d nenhuma configuração vence o passeio aleatório na validação; em 63 d a curva de futuros segue melhor na validação. No teste a rede enxuta vence a curva nos três horizontes. (3) **Decisão (04/11/2026): a rede enxuta (32 un., dropout 0,4, seed 42) passou a ser o modelo final.** Todos os blocos A–E deste anexo, os notebooks 03–05 e as figuras foram reexecutados com ela. A configuração inicial de 64 unidades fica registrada aqui como ponto de partida da busca.")
    texto = "\n".join(S) + "\n"
    ANEXO.write_text(texto, encoding="utf-8")
    d = DOSSIE.read_text(encoding="utf-8")
    d = d.split(MARCA)[0] + MARCA + texto
    DOSSIE.write_text(d, encoding="utf-8")
    print("anexo gravado:", ANEXO, "| dossiê atualizado")


if __name__ == "__main__":
    main()
