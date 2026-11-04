# Pedidos de experimentos e informações para o TCC

Gerado em 17/09/2026 pelo chat de escrita. Cada item é independente dos demais, salvo indicação. Os resultados devem ser anexados ao `reports/dossie-tecnico.md`, em tabelas no mesmo formato já usado, com a data de execução. Sempre que possível, gravar a figura correspondente em `reports/figures/` com nome descritivo.

---

## Bloco A — Experimentos que fecham a RQ3 (mais baratos, fazer primeiro)

### A1. Sensibilidade à Selic
Rodar o backtest completo (20 datas, 01/07/2024 a 03/02/2026) fixando a taxa de desconto em 8 %, 10 %, 12 %, 13,25 % e 15 % a.a., em vez da Selic vigente. Reportar, por nível: receita líquida média por saca do AgroVisible, da venda imediata e da parcelada; frequência de "armazenar" nas 20 datas; número de datas em que a ação ótima muda em relação ao caso base. Registrar qual Selic vigente foi usada no caso base em cada data.

### A2. Choque de base
Rodar o backtest completo com a base esperada sazonal deslocada em −5 pp e +5 pp, e separadamente com o risco de base dobrado (5,2 / 7,2 / 10,0 pp). Reportar os mesmos indicadores de A1, mais a frequência com que o hedge é escolhido em cada cenário (esperado: nula no caso base; verificar se muda).

### A3. Sensibilidade ao COE
Rodar o benchmark "meta de margem" com COE em 500, 700, 900 e 1 100 R$/sc, e reportar em quantas datas a heurística deixa de coincidir com a venda imediata. Se A6 for implementado, rodar também o AgroVisible com esses valores.

### A4. Consolidar a grade de sensibilidade já rodada
Confirmar e gravar no dossiê a tabela completa da grade λ × armazenagem (12 combinações) com receita média e frequência de armazenar por célula. O dossiê hoje só descreve o efeito em texto.

---

## Bloco B — Amostra e integridade do backtest (RQ2)

### B1. Backtest no período de validação
Aplicar o mesmo protocolo de backtest às datas mensais de 01/07/2022 a 31/12/2023 (safras 2022/23 e 2023/24). Atenção: nesse período, σ residual e base sazonal foram estimados com os próprios dados de validação, o que gera um viés favorável leve. Reportar a mesma tabela por safra (venda imediata, parcelada, média móvel, meta de margem, hedge 6 m, AgroVisible, oráculo) e a tabela consolidada das quatro safras. Indicar explicitamente esse viés na nota da tabela.

### B2. Estatística de comparação
Para o backtest consolidado (teste, e teste+validação se B1 for feito): diferença pareada por data entre AgroVisible e venda imediata, e entre AgroVisible e parcelada. Reportar média, desvio, intervalo de confiança de 95 % por bootstrap (10 000 reamostragens) e p-valor do teste de Wilcoxon pareado. Reportar também a fração do ganho do oráculo capturada por cada estratégia, por data e em média.

### B3. Decomposição do ganho
Para cada data de decisão do AgroVisible, gravar: ação escolhida em k=0, mês efetivo de venda, receita realizada, receita da venda imediata, previsão de 21/63/126 d na data e retorno realizado nesses horizontes. Isso alimenta a análise de "onde acertou e onde errou" da seção de Discussão.

---

## Bloco C — Componente preditivo (RQ1)

### C1. Reexecutar o notebook 03 com o modelo retreinado
As saídas gravadas são do modelo antigo. Reexecutar do zero, confirmar que as métricas batem com a tabela do dossiê (RMSE 0,112 / 0,194 / 0,185) e regravar as figuras: curva de perda treino × validação, previsto × realizado por horizonte, e distribuição dos resíduos.

### C2. Métricas no conjunto de teste
O dossiê só reporta métricas de validação. Reportar a mesma tabela (RMSE, MAE, MAPE, acurácia direcional, LSTM × passeio aleatório × curva de futuros) para o conjunto de teste (417 amostras). Se a LSTM se comportar de forma muito diferente entre validação e teste, isso é material importante para Ameaças à Validade.

### C3. Ablação por grupo de features
Retreinar a LSTM com a mesma configuração e semente removendo, um grupo por vez: (a) retornos e posição vs. média, (b) mercado (vol, spread, base), (c) calendário e Selic, (d) clima, (e) fundos COT, (f) insumos. Reportar RMSE, MAE e acurácia direcional por horizonte na validação, e a variação relativa ao modelo completo. Como cada retreino leva minutos em CPU, seis retreinos são viáveis. Se possível, repetir cada configuração com 3 seeds e reportar média e desvio, porque diferenças pequenas entre grupos podem ser ruído de inicialização.

### C4. Baseline ARIMA (opcional, se sobrar tempo)
ARIMA sobre o log-preço diário, ordem escolhida por AIC no treino, previsão recursiva em 21, 63 e 126 dias para cada data de validação. Reportar na mesma tabela de C2. Se não der tempo, o texto seguirá com passeio aleatório e curva de futuros como baselines e ARIMA será citado como limitação.

### C5. Variabilidade entre seeds do modelo completo
Treinar o modelo completo com seeds 42, 43, 44, 45 e 46 e reportar média e desvio do RMSE por horizonte. Necessário para afirmar se a diferença entre LSTM e curva de futuros é maior que a variabilidade de treino.

---

## Bloco D — Uso do COE no motor

### D1. Decisão de projeto
O TCC vai usar o COE ativamente. Propor e implementar uma das duas formas, e informar qual foi escolhida e por quê:
- (i) somente sinalização: em cada nó, calcular margem sobre COE e classificar o resultado esperado nas faixas do AgroSafety (lucro supernormal / normal / resíduo financeiro / descapitalização / falência) a partir de COE, COT e CTMe;
- (ii) restrição: enquanto houver horizonte, a ação "vender" só é permitida se o preço for ≥ COE × (1 + m), com m = margem mínima configurável (padrão 0 %); no último período a venda é forçada.
Se (ii) for implementada, rodar o backtest com m ∈ {0 %, 10 %, 30 %} e reportar o efeito.

### D2. COE real
Buscar nas planilhas da CONAB (custo de produção, café arábica, Minas Gerais, praças como Guaxupé, Patrocínio, Manhuaçu ou São Sebastião do Paraíso) o COE e o COT por saca para as safras 2022/23 a 2025/26. Gravar em `data/external/` e registrar os valores no dossiê. Substituir o placeholder de 700 R$/sc pelo valor da safra correspondente à data de decisão.

---

## Bloco E — Informações para o texto (sem experimento)

### E1. Fontes dos parâmetros
De onde vieram os 2,50 R$/sc/mês de armazenagem e os 0,2 %/mês de quebra técnica? Se houver documento, tabela de cooperativa ou site, informar para citação. Se foram estimativa, dizer isso.

### E2. Custo operacional de bolsa
Os 10 R$/sc de custo de hedge foram calculados a partir de TOB, emolumentos e taxa de registro do módulo 5 do AgroSafety? Se sim, mostrar a conta. Se não, informar a origem.

### E3. Hiperparâmetros: como foram escolhidos
As unidades (64/32), dropout 0,2, janela de 63 dias e batch 32 foram fixados a priori ou houve busca? Se houve, listar as configurações testadas e as métricas.

### E4. Tempo de execução
Tempo de treino da LSTM em CPU (modelo final), tempo de resolução do motor para uma data (7 camadas × 121 nós) e tempo total do backtest de 20 datas. Vai para a seção de operacionalização.

### E5. Versões
Versões de Python, TensorFlow/Keras, NumPy, pandas e das bibliotecas de coleta (python-bcb, yfinance, cot-reports, openmeteo-requests). Confirmar se o `requirements.txt` está atualizado.

### E6. Figuras necessárias para o TCC
Confirmar quais destas já existem em `reports/figures/` e gerar as que faltam:
1. Série do indicador CEPEA arábica 2005–2026 com os cortes treino/validação/teste sombreados.
2. Curva de perda treino × validação do modelo final.
3. Previsto × realizado por horizonte (validação e teste).
4. Cone de preços do motor para uma data de decisão (mediana e quantis 10/90 por mês).
5. Árvore reduzida com ações ótimas anotadas para uma data de decisão.
6. Gatilho de venda por mês (preço a partir do qual vender é ótimo) para uma data.
7. Receita por data de decisão, todas as estratégias, com as duas safras separadas.
8. Base física vs. futuro em % ao longo do tempo, com a média sazonal sobreposta.
9. Mapas de calor da sensibilidade (λ × armazenagem; Selic × base).
Formato: PDF vetorial ou PNG a 300 dpi, fundo branco, rótulos em português.

---

## Ordem sugerida
A1, A2, A4, C1, C2, E1–E5 (um dia). Depois B1, B2, B3, D2 (um dia). Depois C3, C5, D1 (um a dois dias). C4 por último, se houver tempo.
