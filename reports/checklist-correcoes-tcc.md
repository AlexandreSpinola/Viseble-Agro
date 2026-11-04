# Checklist de correções do TCC (modelo final de 32 unidades)

Criado em 04/11/2026. Marcar `[x]` ao concluir. Fonte dos números: tabelas do anexo do dossiê e CSVs em `reports/experimentos/`. Os parágrafos "Leitura" do anexo não valem como fonte (ver bloco 0).

Legenda: **[EXP]** depende do chat de experimentos ou de execução pelo autor; **[TXT]** só texto.

---

## 0. Dados e dossiê (antes de escrever)

- [x] **[EXP]** (executados em 04/11, 14h23 e 14h31) Notebooks 04 e 05: trocar `taxa_desconto_aa=float(df['selic_meta'].iloc[-1])/100` por `taxa_desconto_aa=0.10` e reexecutar. Verificar: média de `lstm_dp` em `reports/backtest_teste.csv` = 2 186,3; `simulacao_safras.csv` regravado.
- [x] **[EXP]** Bloco D2 (COE CONAB) reexecutado com o modelo de 32 un.: `d2_coe_conab.csv`, `d2_backtest_teste_coe_conab.csv`, `d2_backtest_validacao_coe_conab.csv` com data de 04/11 ou posterior. Esperado: lstm_dp 2 186,3, freq. armazenar 40 %, meta de margem inalterada. Incluir a geração em `src/experiments/rq2_rq3.py` para não se perder de novo.
- [x] **[EXP]** (CSV gerado 04/11; usar medianas: jun −3,2, jul −2,3, nov +2,6, dez +4,3 %) Sazonalidade mensal do preço CEPEA 2015–2026 (média do mês ÷ média do ano, por mês): célula em notebook (02 ou 05) + CSV `reports/experimentos/sazonalidade_mensal.csv` + figura opcional. Números esperados: jun–out 3–4 % abaixo, dez–fev 3–6 % acima.
- [x] **[EXP]** Simulação por safra a 10 % a.a. (04/11): ganhos 0 / +6,0 / 0 / +24,6 %; média por safra +12,3 % (2 cegas) e +7,6 % (4); agregado +14,0 % e +9,2 %. Os 11,9/6,6 % antigos eram a 14 %.
- [ ] **[EXP]** Datas em que a ação muda com λ = 1 (não consta em A2/A4; inferido 8).
- [x] **[EXP]** Atualizar os textos fixos em `src/experiments/anexo.py` que ainda descrevem o modelo antigo: Leitura de B2 (p-valores), B3 (maiores perdas/ganhos), C3 (ablação), E3 ("fixados a priori"). Regerar com `python -m src.experiments.anexo`.
- [x] **[EXP]** Corpo do dossiê: 1.1 (COE "nunca coletado"), tabela 3.1 (COE placeholder "CONAB pendente"), 3.3 ("captura de 45 %" → 49,0/47,3 %), tabela A4 (λ 0,2 → 0,25).
- [ ] **[EXP]** `requirements.txt` com versões fixadas (E5) e `statsmodels` incluído.

## 1. Seção 1: Fontes de dados (`01-fontes.tex`)

- [x] **[TXT]** Linha 23–25: dizer que o indicador de geada (Tmin < 3 °C) nunca é acionado na reanálise ERA5 nos quatro pontos; a geada de julho de 2021 não está representada na feature. Apontar para a ameaça de construção (seção 7) e trabalho futuro (limiar 5 °C ou anomalia de Tmin).
- [x] **[TXT]** Conferir COE "714 a 876" (ok) e demais números contra o dossiê.

## 2. Seção 2: Introdução (`02-introducao.tex`, hoje é o exemplo do template)

- [x] **[TXT]** Escrever: contexto (comercialização do café, bienalidade, volatilidade 2024–2026), problema (quando e quanto vender; heurísticas do produtor), objetivo, RQ1–RQ3, contribuições (pipeline sem vazamento, baseline de curva de futuros, motor MDP com hedge e COE, protocolo de avaliação econômica), organização do texto.
- [x] **[TXT]** Descomentar `\include{secoes/02-introducao}` em `tcc_agrovisible.tex` (linha 288).

## 3. Seção 3: Fundamentação (`03-fundamentacao.tex`)

- [x] **[TXT]** Reler; não há números do modelo. Conferir citações marcadas VERIFICAR.

## 4. Seção 4: Configuração (`04-configuracao.tex`)

- [x] **[TXT]** Quadro `qua:lstm`: LSTM(32, seq) → Dropout 0,4 → LSTM(16) → Dropout 0,4 → Dense(32) → Dense(3). Parada na época 26. Dizer que a configuração foi escolhida por busca (nova subseção) e que a inicial era 64/32, dropout 0,2.
- [x] **[TXT]** Quadro `qua:features`, linha `geada_30d`: marcar como constante zero na amostra (inerte, mantida entre as 26 entradas para rastreabilidade; importância por permutação nula).
- [x] **[TXT]** Nova subseção "Análise exploratória das variáveis": Spearman feature × alvo por horizonte (F1, fig. 10), pares colineares |ρ| > 0,7 (F2, fig. 11), importância por permutação no modelo final (F3, fig. 12). Mensagem: sinal em oferta (chuva, Tmin), base, calendário, Selic e insumos, crescente com o horizonte; retornos diários/21 d, médias de 1–3 m e volatilidade com |ρ| < 0,04.
- [x] **[TXT]** Nova subseção "Busca de hiperparâmetros": grade F4 (12 configurações, seed 42, um fator por vez: unidades 32/64/128, dropout 0/0,2/0,4, janela 21/63/126, lr 3e-4/1e-3/3e-3, batch 32/64) + verificação F5 (3 candidatas × 5 seeds, validação e teste, com baselines). Tabela com média ± desvio. Mensagem: só o tamanho da rede importa; 128 é a pior; dropout 0 piora; RMSE de treino 0,029 (inicial) vs 0,047 (final). Declarar que a seleção foi feita na validação e que o teste permaneceu cego.
- [x] **[TXT]** Protocolo RQ1: acrescentar busca de hiperparâmetros, 5 seeds por candidata, Spearman e permutação. Ablação continua com 3 seeds e o modelo final.
- [x] **[TXT]** Protocolo RQ2: acrescentar a simulação por safra (notebook 05): colheita em 1º de julho, horizonte de 12 meses, política rolante mensal, 4 safras (2 cegas).
- [x] **[TXT]** Parágrafo "Operação em tempo real": política rolante mensal; a cada mês uma nova previsão substitui a anterior; a rede só recebe dados já observados; o produtor recebe gatilho por mês, não data única.
- [x] **[TXT]** Ambiente: "quatro cadernos" → cinco (coleta, variáveis, previsão, decisão, safra); versões (E5): Python 3.13, TensorFlow 2.21, Keras 3.15, NumPy 2.5, pandas 3.0, scikit-learn 1.9, statsmodels 0.15.
- [x] **[TXT]** Tabela de parâmetros: manter 10 % a.a. como caso base; COE CONAB por safra. Conferir.

## 5. Seção 5: Resultados (`05-resultados.tex`)

- [x] **[TXT]** Linha 3: data dos experimentos → 4 de novembro de 2026.
- [x] **[TXT]** Tabela `tab:rq1-metricas`: LSTM val 0,096/0,166/0,128; MAE 0,067/0,145/0,104; MAPE 7,0/15,3/10,8; direção 56,7/74,5/91,7. Teste 0,117/0,206/0,301; MAE 0,085/0,158/0,212; MAPE 8,3/14,7/18,4; direção 63,8/75,8/77,0. Baselines inalterados. Negrito: val 21 d RW/ARIMA, val 63 d curva, val 126 d LSTM; teste LSTM nos três.
- [x] **[TXT]** Parágrafos "três padrões" e "curva de futuros": LSTM perde para RW só em 21 d na validação (no teste 0,117 vs 0,120, empate dentro do desvio entre seeds); vence a curva em 21 e 126 d na validação e nos três horizontes no teste; curva vence só em 63 d na validação.
- [x] **[TXT]** Figura previsto × realizado: conferir a descrição com a figura nova (é série de preço, não dispersão; a alta de 2024 não é prevista em 126 d).
- [x] **[TXT]** Tabela `tab:rq1-seeds`: média 0,105/0,180/0,155; desvio 0,014/0,014/0,030; direção 51,5±9,2 / 60,8±10,4 / 83,1±7,5; seed 42 = 0,096/0,166/0,128 e 56,7/74,5/91,7. Texto: a seed 42 é favorável (≈1 desvio acima da média em 63 e 126 d); reportar sempre média ± desvio. Curva × LSTM em 63 d: 0,010 com seed 42 (< 1 desvio), 0,024 com a média de 5 seeds (robusto).
- [x] **[TXT]** Tabela `tab:rq1-ablacao`: (a) −5,6/+3,7/+22,2; (b) +0,8/+6,2/+25,7; (c) −4,2/+7,2/+37,9; (d) −2,5/+3,0/+13,5; (e) −0,6/+2,2/+5,2; (f) +0,9/+0,1/−7,3. Direção 126 d: completo 81,5; a 71,7; b 65,2; c 61,5; d 77,0; e 73,8; f 83,2.
- [x] **[TXT]** Conclusões da ablação reescritas: desvio entre seeds do completo em 126 d = 23 % do RMSE; só calendário/Selic, mercado e retornos ficam claramente acima do ruído; clima e COT marginais; insumos não contribuem **nesta configuração e com estes hiperparâmetros** (removê-los melhora 7 % em 126 d). Em 21 d nenhum grupo ajuda. Não generalizar.
- [x] **[TXT]** Tabela `tab:rq2-teste`: AgroVis 2 176 / 2 202 / 2 186; M. móvel total 1 982; oráculo 2 332; negrito AgroVis nas duas safras.
- [x] **[TXT]** Texto do backtest: +7,8 % vs imediata, +9,2 % vs parcelada. Safra 2024/25: motor armazenou 4, 3, 2, 1 meses de 30/07 a 25/10/2024 e vendeu entre 1 986 e 2 054 (ganhos 34–40 %); só 1º/07 (venda a 1 362) perdeu a alta; única data em que a parcelada venceu. Junho/2025: único erro (−1,9 %). Safra 2025/26: 2 202 = oráculo. Hedge 6 m −5,7 % (inalterado). Oito armazenagens em 20, sete corretas.
- [x] **[TXT]** Tabela `tab:rq2-4safras`: 2022/23 AgroVis 1 102; 2023/24 944; 2024/25 2 176; 2025/26 2 202; total 1 648; ganho +6,1 %; captura 94,0 %. Demais inalterados.
- [x] **[TXT]** Texto 4 safras: 2022/23 −3,2 %, perdas em 29/09/2022 (−26 %, armazenou 2 meses numa queda), 31/10/2022 (−3 %) e 05/06/2023 (−11 %, 6 meses); 2023/24 armazenou nas 6 datas, +10,7 %. Reescrever "única a superar em todos os agregados" (perde em 2022/23; vence em 3 de 4 safras e no total).
- [x] **[TXT]** Tabela `tab:rq2-oraculo`: AgroVis 49,0 % (teste) / 47,3 % (4 safras).
- [x] **[TXT]** Tabela `tab:rq2-estatistica`: teste vs imediata 157,8 [52,6; 266,7] p = 0,046, 35 %; vs parcelada 184,8 [90,1; 272,9] p = 0,002, 75 %; 4 safras vs imediata 86,0 [24,2; 155,6] p = 0,021, 36,8 %; vs parcelada 136,0 [78,9; 192,2] p < 0,001, 73,7 %. Texto: todas significativas a 5 %; desvio 250; mediana nula continua explicando a baixa fração de datas positivas.
- [x] **[TXT]** Anatomia: 18 armazenagens em 38 datas, 14 corretas, 4 erradas, 20 vendas imediatas. Maiores ganhos: jul–out/2024 e jul–ago/2025. Figura do gatilho (31/08/2026) confere.
- [x] **[TXT]** Nova subseção "Simulação por safra" (notebook 05, 12 meses): 2022/23 vendeu no dia 0 (= imediata); 2023/24 vendeu no mês 7, +3,8 %; 2024/25 vendeu no dia 0 a 1 362 e perdeu a alta (oráculo 2 272, mês 7); 2025/26 vendeu no mês 2, +23,8 % (= oráculo). Médias por safra: 2 cegas +12,3 %, 4 safras +7,6 % (agregado +14,0 / +9,2 %); 2023/24 vendeu no mês 7 a 874 (+6,0 %); 2025/26 2 251 (+24,6 %). Discutir a diferença entre backtest mensal (20 entradas) e simulação (1 entrada por safra).
- [x] **[TXT]** COE: parágrafo mantido; conferir com D2 novo.
- [x] **[TXT]** Tabela `tab:rq3`: Selic 8 % 2 189; 10 % 2 186; 12 % 2 184; 13,25 % 2 182; 15 % 2 180; vigente 2 183; freq. 40 %; armazenagem 1,5 → 2 187, 5,0 → 2 184; base ±5 pp e risco ×2 → 2 186, 0 mudanças; λ 0,25 → 2 187, 30 %, 2 datas; λ 0,5 → 2 030, 5 %, 7 datas; λ 1 → 2 028, 0 %, (8) datas.
- [x] **[TXT]** Parágrafo aversão a risco: até 0,25 receita mantida e frequência 40 → 30 %; em 0,5 colapsa para a imediata (5 %); transição mais abrupta que no modelo inicial porque o σ residual menor faz a penalização dominar antes. Desvio entre datas 269 → 406.
- [x] **[TXT]** Custo computacional: treino 74 s (seeds 45–116 s); motor 2 ms; backtest 0,5 s; grade A4 ~1 min; 23 retreinos ~35 min; busca F4/F5 (tempo em `hp.log`, se quiser citar).

## 6. Seção 6: Discussão (`06-discussao.tex`)

- [x] **[TXT]** Abertura: LSTM perde para RW só em 21 d na validação; perde para a curva só em 63 d; sobreajuste reduzido pela busca; direção 92 % (val) / 77 % (teste) em 126 d.
- [x] **[TXT]** Mecanismo 1 (assimetria): exceções agora set/2022 (−26 %) e jun/2023 (−11 %).
- [x] **[TXT]** Mecanismo 2 (incerteza): λ = 0,25 corta a frequência sem perder receita; λ = 0,5 já elimina o ganho. Reescrever.
- [x] **[TXT]** "Onde a ferramenta falha": trocar a narrativa da safra 2024/25. Falhas a discutir: 1º/07/2024 (previsão negativa de 21 d na véspera da alta; na simulação por safra isso custou a alta inteira), set/2022 e jun/2023 (alta prevista em queda persistente), e a magnitude: em jul–out/2024 o y_126d previsto era ≈0 ou negativo enquanto o realizado foi +0,5; o ganho veio da direção de 21 d e da política rolante, não da previsão longa.
- [x] **[TXT]** Sazonalidade: parágrafo novo com os números do CSV (jun–out abaixo, dez–fev acima); armazenar captura esse ganho estrutural; é por isso que o motor armazena em julho–outubro e vende no verão. Ligar com fig. 06 (gatilho) e com `mes_sin/mes_cos` e `bienalidade_alta` no topo da importância por permutação.
- [x] **[TXT]** Implicações para a pesquisa: "curva supera em dois de três horizontes" → um (63 d). Ranking RMSE × valor econômico ainda vale em 21 d na validação.
- [x] **[TXT]** Implicações para produtores: AgroVis é a melhor estratégia não oráculo em 3 de 4 safras e no total; perde só em 2022/23.
- [x] **[TXT]** Construtores de ferramentas: treino ≈ 1 min; acrescentar diretriz sobre busca de hiperparâmetros enxuta (rede menor generaliza melhor com 3 940 amostras).
- [x] **[TXT]** Usar a EDA: sinal em oferta/base/calendário sustenta a escolha das features; retornos de curto prazo são ruído.

## 7. Seção 7: Ameaças (`07-ameacas.tex`)

- [x] **[TXT]** Conclusão: p = 0,046 / 0,002 / 0,021 / < 0,001; IC largo (+53 a +267); n = 20 e 38 continuam pequenos; fração positiva 35 / 36,8 %.
- [x] **[TXT]** Variabilidade de treino: desvio 0,014/0,014/0,030; curva × LSTM 63 d robusta só na média de 5 seeds; ablação interpretável em 126 d para 3 grupos.
- [x] **[TXT]** Construção: novo parágrafo "Feature de geada inerte" (ERA5 em 4 pontos de grade nunca registra Tmin < 3 °C; a geada de 2021 não está representada; limiar e resolução espacial).
- [x] **[TXT]** Interna, "Seleção do modelo final": reescrever. Houve busca na validação (12 configurações + 5 seeds); a seed 42 é favorável; o σ residual vem da validação. Mitigação: teste cego, média ± desvio reportada, candidatas verificadas também no teste (F5).
- [x] **[TXT]** Interna, "Sobreajuste": RMSE treino 0,047 vs 0,096–0,166; a busca reduziu de 0,029; ablação não mostra mais ganho ao remover grupos (exceto insumos em 126 d).
- [x] **[TXT]** Externa, "Regime de mercado": "a geada de 2021 está no treino" → o período a contém, a feature não.
- [x] **[TXT]** Acrescentar: simulação por safra com 1 decisão/safra é mais sensível à data de entrada que o backtest mensal.

## 8. Seção 8: Conclusão (`08-conclusao.tex`, hoje é o exemplo do template)

- [x] **[TXT]** Síntese por RQ com os números finais.
- [x] **[TXT]** Limitações: 21 d sem valor; seleção na validação; amostra pequena; geada inerte; custos estimados; hedge sem margem; preço regional.
- [x] **[TXT]** Trabalhos futuros: prever excedente sobre a curva; ponderar horizontes; feature de geada (limiar 5 °C / anomalia); features de oferta (estoques ICE, CONAB, USDA); venda parcelada dentro do motor; opções PUT; app móvel; multicultura; avaliação em janela rolante retreinando por safra.
- [x] **[TXT]** Descomentar `\include{secoes/08-conclusao}` (linha 294).

## 9. Fechamento

- [x] **[TXT]** `refbib.bib`: 20 entradas do mapeamento conferidas no JabRef (04/11); AgroSafety = Fontes, R. E. (UFLA/DAE), confirmar ano e título oficial do curso. Os 10 artigos colados pelo autor em 04/11 são fabricados (DOIs apontam para outros trabalhos): não usar.
- [x] **[TXT]** Resumo/abstract com os números finais.
- [x] **[TXT]** Figuras 10–12 incluídas no texto (EDA); conferir legendas de todas as 14.
- [x] **[TXT]** Compilar (`latexmk -pdf -interaction=nonstopmode tcc_agrovisible.tex`), checar listas de figuras/tabelas/quadros, referências cruzadas, "??" e avisos de overfull.
- [ ] **[TXT]** Leitura de ponta a ponta: "Agro Visible" vs "AgroVisible" (padronizar), "23 de setembro", "64 unidades", "quatro cadernos", "125 segundos", "dois minutos".
