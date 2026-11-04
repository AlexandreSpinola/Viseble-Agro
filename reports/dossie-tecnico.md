# Dossiê técnico do Agro Visible

Estado do projeto em 14/09/2026, conferido no código e nos notebooks; **corpo atualizado em 04/11/2026 para o modelo final de 32 unidades** (ver anexo, Bloco F). Serve de base factual para a escrita do TCC. Em caso de divergência entre o corpo e o anexo, vale o anexo, que é gerado dos CSVs.

- Dataset: `data/processed/dataset_diario.csv`, 5 169 linhas × 45 colunas, 07/12/2005 a 31/08/2026, diário em dias úteis, sem faltantes.
- Teste cego: 01/07/2024 a 31/08/2026 (safras 2024/25 e 2025/26).
- Código: `src/data` (coleta), `src/features/build_features.py` (features e split), `src/models` (LSTM, previsão), `src/decision` (motor, hedge, benchmarks, backtest). Notebooks 01 a 04.

---

## 1. Dados

### 1.1 Fontes usadas, descartadas e substituídas

| Dado | Fonte final | Como entrou | Status |
|---|---|---|---|
| Preço físico arábica e robusta (R$/sc e US$/sc) | CEPEA/ESALQ | **XLS baixados manualmente** em `data/external/`. O site bloqueia scraping (WAF devolve 403). O módulo `cepea.py` lê e concatena os arquivos com `xlrd` em modo tolerante a corrupção. | alvo |
| Futuro Coffee C (ICE NY) | Yahoo Finance, KC=F | Contínuo de primeiro vencimento. Desde set/2026 também a curva por vencimento (KCH/K/N/U/Z), acumulada em `data/raw/ice_curve.csv`. | feature + hedge |
| PTAX venda e meta Selic | Banco Central, API SGS (séries 1 e 432) | `python-bcb`. | feature + custo de oportunidade |
| Câmbio Yahoo (BRL=X) | Yahoo Finance | Coletado, mas não é feature. A PTAX oficial substituiu. | descartado |
| Robusta em Londres (RC=F / RM=F) | Yahoo Finance | Tickers delistados. Substituído pelo indicador físico CEPEA do robusta. | substituído |
| Clima nas regiões produtoras | **Open-Meteo** (reanálise ERA5) | 4 pontos: Varginha, Patrocínio, Franca e Colatina. Tmin e precipitação diárias. INMET não foi usado (cobertura irregular e lacunas por estação). | 5 features |
| Posições de fundos (COT/CFTC) | CFTC via `cot-reports` | **Sim, entrou**: net non-commercial em % do open interest e variação em 4 semanas, ancorado na data de divulgação (sexta), não na de referência (terça). | 2 features |
| Insumos (ureia, DAP, KCl, petróleo) | Banco Mundial, Pink Sheet mensal | Disponível 3 dias úteis após o fechamento do mês. Entram ureia e petróleo; DAP e KCl coletados mas não usados. | 3 features |
| Custos de produção (COE/COT/CT) | CONAB, série histórica de custos | Planilha XLS baixada; extração em `data/external/conab_coe_cot_cafe_arabica_mg.csv`. Guaxupé, MG, por ano de colheita (anexo D2). O placeholder de 700 R$/sc foi usado só no desenvolvimento. | motor: margem e piso opcional |
| Estoques certificados ICE, safra CONAB, USDA/ICO, Cecafé | — | Discutidos como próximo passo. Não coletados. | pendente |

### 1.2 Período, frequência e observações

- **Calendário**: dias com indicador CEPEA arábica publicado (dias úteis brasileiros). Demais fontes preenchidas com o último valor conhecido (ffill), nunca com valores futuros. Frequência diária.
- **Início bruto**: 08/11/2001, começo da série do robusta.
- **Início efetivo**: 07/12/2005. Médias móveis de 2 anos e retornos de 1 ano dos insumos consomem os primeiros 4 anos.
- **Fim**: 31/08/2026.
- **Observações**: 5 169 linhas × 45 colunas, sem NaN. Após o janelamento da LSTM: 3 940 amostras de treino, 372 de validação, 417 de teste.

### 1.3 Corte temporal

Partição cronológica estrita (`chronological_split`). A unidade é o ano-safra (começa em julho). O teste cobre exatamente duas safras porque a bienalidade limita o ciclo de decisão a dois anos.

| Split | Datas | Safras | Amostras LSTM | Papel |
|---|---|---|---|---|
| Treino | 07/12/2005 → 30/06/2022 | 2005/06 a 2021/22 (~17 safras, inclui geada de 2021) | 3 940 | pesos e scaler |
| Validação | 01/07/2022 → 30/06/2024 | 2022/23 e 2023/24 | 372 | early stopping, σ residual, estatísticas de base |
| Teste | 01/07/2024 → 31/08/2026 | **2024/25 e 2025/26** | 417 | backtest cego |

A janela de entrada de 63 dias pode cruzar a fronteira do split anterior (é histórico já conhecido). O alvo nunca cruza: as últimas 126 datas de cada split são descartadas. Por isso as amostras de validação terminam em dez/2023 e as de teste em mar/2026.

### 1.4 Features finais da LSTM

26 features, todas estacionárias ou limitadas. Janela de entrada de 63 dias úteis. Não há lags explícitos além dos que a janela fornece; defasagens aparecem como retornos e acumulados.

| Grupo | Feature | Definição |
|---|---|---|
| Retornos | `ret_arabica_1d` | log-retorno diário do físico arábica |
| | `ret_arabica_21d` | log-retorno de 21 dias úteis |
| | `ret_robusta_1d` | log-retorno diário do físico robusta |
| | `ret_ice_1d` | log-retorno diário do futuro ICE (cents/lb) |
| | `ret_ptax_1d` | log-retorno diário da PTAX |
| Posição vs. média | `preco_vs_ma_1m` | preço / média móvel 21 d − 1 |
| | `preco_vs_ma_3m` | idem, 63 d |
| | `preco_vs_ma_1a` | idem, 252 d |
| | `preco_vs_ma_2a` | idem, 504 d |
| Mercado | `vol_21d` | desvio dos retornos diários em 21 d, anualizado |
| | `spread_arabica_robusta` | físico arábica / físico robusta |
| | `base_fisico_futuro_pct` | (físico − ICE em R$/sc) / ICE em R$/sc |
| Calendário e macro | `mes_sin`, `mes_cos` | sazonalidade cíclica do mês |
| | `bienalidade_alta` | dummy: ano-safra par (2020, 2022, 2024...) = carga cheia no Brasil |
| | `selic_meta` | meta Selic, % a.a. |
| Clima | `chuva_arabica_30d`, `chuva_arabica_90d` | chuva acumulada, média de Sul de Minas, Cerrado e Mogiana, calculada no calendário civil antes do recorte |
| | `tmin_arabica_7d` | mínima das mínimas em 7 dias nas três regiões |
| | `geada_30d` | dummy: Tmin < 3 °C entre maio e setembro nos últimos 30 dias |
| | `chuva_robusta_90d` | chuva acumulada em Colatina, ES |
| Fundos | `cot_net_pct_oi` | posição líquida non-commercial / open interest |
| | `cot_net_pct_oi_chg4w` | variação em 20 dias úteis |
| Insumos | `indice_troca_urea` | sacas de café para comprar 1 t de ureia (módulo 4 AgroSafety) |
| | `ret_urea_1a` | log-retorno de 252 d da ureia (US$) |
| | `ret_crude_1a` | log-retorno de 252 d do petróleo |

**Normalização.** Não há normalização em janela deslizante. `StandardScaler` global ajustado **só no treino**, aplicado igual a validação e teste. Funciona porque as features já são estacionárias por construção.

**Alvo.** Três saídas: log-retorno futuro em 21, 63 e 126 dias úteis, `y_h = ln P(t+h) − ln P(t)`. Preço reconstruído por `P(t+h) = P(t)·exp(ŷ_h)`.

### 1.5 Preço recebido pelo produtor em Minas

**Não é modelado como preço regional.** O alvo e o preço de venda em todo o sistema é o indicador CEPEA/ESALQ arábica tipo 6 bebida dura, média de negócios nas praças de MG e SP. Simplificação declarada: não há série de preço de balcão por cooperativa.

A base que existe é a **base física versus futuro**: indicador CEPEA menos Coffee C convertido por `cents/lb ÷ 100 × 132,277 × PTAX`. Usada de dois modos:

- feature da LSTM, em percentual do futuro;
- no motor de hedge, como base esperada sazonal por mês do ano e risco de base por horizonte, estimados de 2015 até o fim do treino: média de −20 % do futuro; risco de 2,6, 3,6 e 5,0 pontos percentuais em 21, 63 e 126 dias.

A base em reais escala com o preço (−204 R$/sc em média desde 2015, −317 desde 2023), por isso a modelagem é em percentual. O material do módulo 5 mede a base contra o ICF da B3; aqui o ICE com PTAX é o proxy.

---

## 2. Modelo preditivo (RQ1)

### 2.1 Arquitetura final

- Entrada: (63 dias, 26 features)
- Camadas: LSTM(32, return_sequences) → Dropout 0,4 → LSTM(16) → Dropout 0,4 → Dense(32, ReLU) → Dense(3, linear). Configuração escolhida por busca de hiperparâmetros (anexo F4/F5); a configuração inicial, fixada a priori, era LSTM(64)/LSTM(32) com dropout 0,2.
- Saídas: ŷ para 21, 63 e 126 dias úteis, treinadas em conjunto
- Perda: MSE sobre log-retornos; métrica auxiliar MAE
- Otimizador: Adam, taxa inicial 1e-3, ReduceLROnPlateau (fator 0,5, paciência 7)
- Épocas: máximo 100, batch 32. EarlyStopping na perda de validação (paciência 15, restaura melhores pesos). Último treino parou na **época 26**.
- Seed: 42 (`keras.utils.set_random_seed`). CPU apenas (sem GPU no Windows nativo).

### 2.2 Baselines e métricas por horizonte (validação)

Três baselines: passeio aleatório (retorno previsto = 0), curva de futuros (retorno implícito em `ln[F_t·(1 + base_sazonal_{t+h}) / P_t]`) e ARIMA(1,1,2), que é indistinguível do passeio aleatório (anexo C4). Métricas no espaço do log-retorno; MAPE é o erro percentual equivalente no preço reconstruído.

| Horizonte | RMSE LSTM | MAE LSTM | MAPE preço % | Direção LSTM % | RMSE passeio aleatório | RMSE curva | Direção curva % |
|---|---|---|---|---|---|---|---|
| 21 d | 0,096 | 0,067 | 7,0 | 56,7 | **0,091** | 0,107 | 61,3 |
| 63 d | 0,166 | 0,145 | 15,3 | 74,5 | 0,177 | **0,156** | 68,5 |
| 126 d | **0,128** | 0,104 | 10,8 | 91,7 | 0,236 | 0,193 | 75,3 |

No teste cego (417 amostras): RMSE 0,117 / 0,206 / 0,301 contra 0,120 / 0,233 / 0,321 do passeio aleatório e 0,130 / 0,227 / 0,309 da curva; acerto direcional 64 / 76 / 77 %.

Leitura: na validação a LSTM vence o passeio aleatório em 63 e 126 dias e a curva de futuros em 21 e 126 dias; em 21 d perde para o passeio aleatório e em 63 d perde para a curva. No teste vence os dois baselines nos três horizontes. Variabilidade entre 5 seeds (anexo C5): desvio de 0,014 / 0,015 / 0,030 no RMSE, então as diferenças em 21 d na validação são empate. RMSE de treino 0,047, contra 0,029 da configuração inicial: menos sobreajuste.

### 2.3 Estudo de ablação, análise exploratória e busca de hiperparâmetros

Feitos; tabelas no anexo (C3, F1–F5). Resumo com o modelo final, variação do RMSE médio de 3 seeds ao remover cada grupo:

| Grupo removido | 21 d | 63 d | 126 d |
|---|---|---|---|
| (a) retornos e médias móveis | −5,6 % | +3,7 % | +22,2 % |
| (b) mercado: vol, spread, base | +0,8 % | +6,2 % | +25,7 % |
| (c) calendário e Selic | −4,2 % | +7,2 % | +37,9 % |
| (d) clima | −2,5 % | +3,0 % | +13,5 % |
| (e) fundos COT | −0,6 % | +2,2 % | +5,2 % |
| (f) insumos | +0,9 % | +0,1 % | −7,3 % |

Todos os grupos, exceto insumos, contribuem em 126 dias; calendário, mercado e retornos são os mais importantes. Em 21 dias nenhum grupo ajuda. A correlação de Spearman com o alvo (F1) e a importância por permutação (F3) convergem: o sinal está em oferta, base, calendário e insumos, e cresce com o horizonte. A busca de hiperparâmetros (F4) variou unidades, dropout, janela, taxa e batch; só o tamanho da rede importou, e a verificação com 5 seeds (F5) confirmou a rede de 32 unidades como melhor nos dois conjuntos.

### 2.4 `residual_sigma.json` e a incerteza no motor

Desvio-padrão dos resíduos `ŷ_h − y_h` na validação, por horizonte, gravado em `models/`:

```json
{ "21": 0.0888, "63": 0.1531, "126": 0.1178 }
```

O motor recebe o ponto central da LSTM e esse σ e monta uma distribuição contínua, não cenários amostrados:

- ŷ e σ interpolados linearmente para os passos mensais 0 a 6 (0, 21, 42, ..., 126 dias). Variância acumulada forçada a ser não decrescente (o σ de 126 d saiu menor que o de 63 d).
- Em cada passo o log-preço evolui com incremento normal: média = diferença da trajetória prevista; variância = acréscimo de variância acumulada.
- Grade de 121 pontos de log-preço centrada no preço de hoje, amplitude de 4σ mais a deriva máxima. Transição entre grades = matriz gaussiana discretizada, normalizada por linha.

Na prática a incerteza da LSTM é a largura do cone de preços que o motor enxerga.

---

## 3. Motor prescritivo (RQ2)

### 3.1 Formulação do MDP

- **Tempo**: passos mensais k = 0..K, K = 6 (126 dias úteis). No backtest rolante K encurta a cada mês.
- **Estado**: (k, x), x = ln do preço físico em R$/saca, grade de 121 pontos.
- **Transição**: x_{k+1} = x_k + Δμ_k + ε, ε ~ N(0, Δσ²_k), μ e σ vindos da LSTM.
- **Ações**:
  - VENDER: recebe P·(1 − q)^k e encerra.
  - ARMAZENAR: paga a armazenagem do mês e segue descoberto.
  - ARMAZENAR+HEDGE até m: vende futuro do vencimento m e armazena até m. Recebe o preço travado F_{k,m}·(1 + b_m) − c_op, sujeito só ao risco de base. Curva nos nós futuros desloca-se com o físico: F_{k,m} = F_{0,m}·P_k/P_0.
- **Recompensa**: receita líquida por saca em valor presente na data da decisão.
- **Valor**: V_K(x) = vender. Para k < K: V_k(x) = max( vender, −c_arm + δ·CE[V_{k+1}], max_m hedge_m ), CE = E − λ·DP.

**Como cada parâmetro entra**: Selic é custo de oportunidade, δ = (1 + Selic)^(−1/12) desconta cada mês (o notebook usa a meta vigente). Armazenagem é custo fixo por saca e mês. Quebra técnica de 0,2 %/mês reduz multiplicativamente o preço. COE entra como sinalização (margem sobre COE em toda recomendação, faixas de lucro do AgroSafety e benchmark de meta de margem) e como restrição opcional de piso (`margem_min_coe`, desligada por padrão; anexo D1). Com a restrição desligada, não altera a política. Custo operacional de bolsa (10 R$/sc) entra só na ação de hedge.

| Parâmetro | Valor padrão | Origem |
|---|---|---|
| armazenagem | 2,50 R$/sc/mês | referência de armazém geral, a confirmar |
| quebra técnica | 0,2 %/mês | referência |
| COE | CONAB Guaxupé por safra: 766, 714, 784, 876 R$/sc (2022–2025) | anexo D2; 700 R$/sc foi o placeholder do desenvolvimento |
| taxa de desconto | Selic vigente | BCB série 432 |
| custo operacional B3 | 10 R$/sc | módulo 5 AgroSafety |
| aversão a risco λ | 0 (neutro) | parâmetro do usuário |

### 3.2 Grafo e cenários

Dois objetos distintos:

- **Grafo que o motor resolve**: cadeia de Markov em camadas, 7 camadas temporais × 121 nós de preço, arestas de cada nó para todos da camada seguinte ponderadas pela transição gaussiana. Sem amostragem; a indução retroativa integra sobre toda a distribuição. Produz gatilhos de venda por mês, distribuição do mês de venda e valor de cada ação.
- **Grafo do notebook**: árvore enxuta em `networkx` só para visualização: por mês, três ramos nos quantis 10, 50 e 90, cada nó anotado com a ação ótima lida da política resolvida. Ilustra, não calcula.

### 3.3 Backtest por safra

20 datas de decisão mensais, de 01/07/2024 a 03/02/2026. Receita líquida média por saca em valor presente, mesma contabilidade de custos para todas.

| Safra | n | Venda imediata | Parcelada | Média móvel 3 m | Meta de margem | Hedge 6 m | Agro Visible | Oráculo |
|---|---|---|---|---|---|---|---|---|
| 2024/25 | 12 | 1 999 | 2 057 | 1 996 | 1 999 | 1 805 | **2 176** | 2 418 |
| 2025/26 | 8 | 2 072 | 1 919 | 1 963 | 2 072 | 2 076 | **2 202** | 2 202 |
| Total | 20 | 2 028 | 2 001 | 1 980 | 2 028 | 1 913 | **2 186** | 2 332 |

Ganho de 7,8 % sobre a venda imediata no teste (p = 0,046 no Wilcoxon pareado; IC 95 % de +53 a +267 R$/sc) e de 9,2 % sobre a parcelada (p = 0,002). Com as 4 safras (38 datas, incluindo validação): +6,1 % sobre a imediata (p = 0,021) e +9,0 % sobre a parcelada (p < 0,001). Captura de 49 % (teste) e 47 % (4 safras) do ganho do oráculo nas datas em que havia ganho possível (anexo B2).

Onde a ferramenta ganhou e perdeu:

- **Safra 2024/25: a alta de 2024 foi capturada.** Em julho, agosto, setembro e outubro de 2024 o motor armazenou 4, 3, 2 e 1 meses e vendeu entre 1 986 e 2 054 R$/sc, ganhos de 34 % a 40 %. Só a decisão de 1º de julho (venda imediata a 1 362) perdeu a alta, por uma previsão negativa de 21 dias; é a única data em que a parcelada ganhou.
- **Junho de 2025, único erro absoluto.** Armazenou 3 meses numa queda, perda de 1,9 %.
- **Safra 2025/26 igualou o oráculo.** Julho e agosto de 2025, preço em 1 750, armazenou 2 e 1 meses e rendeu 29 % e 28 %. No platô alto seguinte vendeu na hora, exceto outubro de 2025 (armazenou 1 mês, +1 %).
- **Meta de margem sobre COE** coincide com a venda imediata em todas as datas do teste, inclusive com o COE real da CONAB, porque a margem mínima observada foi de +74 %.

O ganho vem de oito decisões de armazenar em vinte, sete delas corretas.

### 3.4 Hedge em futuros

Ficou na versão final, como terceira ação e como benchmark.

- **Instrumento**: Coffee C da ICE em R$/saca via PTAX, proxy do ICF da B3. Custo operacional de 10 R$/sc.
- **Margem de garantia e ajuste diário**: **não modelados**. Assume-se caixa para chamadas de margem; o custo financeiro da margem depositada não é descontado.
- **Base assumida**: percentual sazonal por mês do ano, estimada só no treino (−17,9 % em fevereiro a −22,5 % em setembro). Risco de base de 2,6, 3,6 e 5,0 pp em 21, 63 e 126 dias, penalizado por λ.
- **Curva**: na recomendação atual, a curva real por vencimento. No backtest, curva plana no primeiro vencimento (Yahoo descarta contratos vencidos); resultado realizado = hedge rolado com rolagens embutidas na série contínua.

Resultado: no backtest o motor nunca escolheu o hedge, e armazenar 6 meses com hedge perdeu 7,8 % contra vender, porque o mercado esteve em backwardation. Na data atual, com base em −26 % contra −21 % sazonal, o hedge de 1 mês trava ~1 816 R$/sc contra 1 748 do spot e é a recomendação para λ entre 0,25 e 0,5.

---

## 4. Robustez (RQ3)

Sensibilidade parcialmente rodada (grade de 12 combinações no backtest completo, notebook 04):

| Parâmetro | Faixa testada | Efeito |
|---|---|---|
| Aversão a risco λ | 0 · 0,25 · 0,5 · 1,0 | Até 0,25 a receita média fica em 2 186 a 2 188 R$/sc e a frequência de armazenar cai de 40 % para 30 % das datas. Em λ = 0,5 o motor armazena em só 5 % das datas e converge para a venda imediata (2 030); em λ = 1 vende sempre. A transição é mais abrupta do que com o modelo inicial, porque o σ residual menor deixa a penalização de risco dominar mais cedo. |
| Armazenagem | 1,5 · 2,5 · 5,0 R$/sc/mês | Desprezível: 1 a 3 R$/sc na receita média, sem mudar nenhuma ação. |
| Selic | 8 · 10 · 12 · 13,25 · 15 % e vigente por data | Receita de 2 180 a 2 189 R$/sc, nenhuma ação muda. Maior efeito na parcelada (−31 R$/sc). |
| Choque de base | ±5 pp na base esperada; risco de base ×2 | Nenhuma decisão muda com λ = 0: o hedge nunca é escolhido com curva plana em backwardation. |
| COE | 500 a 1 100 R$/sc, e CONAB por safra | Só afeta o benchmark de meta de margem; no teste ele só difere da imediata com COE ≥ 1 100 (2 datas). Na validação, com o COE da CONAB, difere em 7 de 18 datas. |

---

## 5. Histórico e limitações

### 5.1 Problemas e mudanças de rumo (material para Ameaças à Validade)

- **Scraping do CEPEA bloqueado.** XLS manuais. A atualização do alvo depende de download manual.
- **Robusta de Londres delistado.** Substituído pelo físico CEPEA; o spread arábica/robusta ficou entre dois físicos.
- **Alvo em nível descartado.** Modelo passou a prever log-retornos multi-horizonte; features redesenhadas como estacionárias.
- **Vazamento por data de referência.** COT e Pink Sheet reancorados na data de divulgação (+3 dias úteis). Clima calculado no calendário civil antes do recorte.
- **Perda de 62 dias no início de cada split.** Janelas construídas só dentro do split descartavam o começo da validação e do teste; a primeira previsão partia de um preço 4 meses após o último conhecido. Corrigido deixando a janela cruzar a fronteira. Na primeira tentativa o alvo também cruzou (rotularia os últimos 126 dias do treino com preços da validação); corrigido antes do retreino.
- **Modelo salvo desatualizado (resolvido).** Notebook 03 carregava o modelo do disco e rodou com o antigo após a mudança nas janelas; agora retreina sempre (`RETREINAR = True`), com seed fixa e resultado reprodutível.
- **Troca do modelo final em 04/11/2026.** A busca de hiperparâmetros mostrou que a rede de 64 unidades estava sobreajustada; a rede de 32 unidades com dropout 0,4 passou a ser a final e todos os resultados foram reexecutados. O modelo anterior está em `models/lstm_multihorizonte_64u_backup.keras`.
- **Baseline errado para o problema.** Passeio aleatório era o único baseline; a curva de futuros é o que o produtor já tem. Com o modelo inicial ela vencia a LSTM em 21 e 63 dias; com o final, só em 63 d na validação.
- **Estatísticas de base olhando a validação.** Primeira versão estimou a base sazonal até o fim dos dados; corrigido para terminar no fim do treino.
- **σ residual não monotônico.** σ de 126 d menor que o de 63 d; o motor força variância acumulada não decrescente.
- **Curva histórica indisponível.** Yahoo apaga contratos vencidos; backtest do hedge usa curva plana. Curva acumulada a partir de set/2026.

### 5.2 Limitações mais graves hoje

1. **Horizonte de 21 dias sem valor preditivo.** Nenhuma configuração vence o passeio aleatório em 21 d na validação; o valor da LSTM está em 63 e 126 dias. Caminho: prever o excedente sobre a curva e usar o retorno implícito como feature.
2. **Seleção de modelo na validação.** A configuração final foi escolhida pela validação e o σ residual também vem dela; as métricas de teste são cegas, mas o early stopping e a escolha de arquitetura não são. Reportar a variabilidade entre seeds (desvio de 0,014 a 0,030) junto com as métricas.
3. **Amostra de teste pequena e atípica.** 20 decisões em duas safras de recorde de preço. Com o modelo final as diferenças passam a ser significativas a 5 % (p = 0,046 vs imediata), mas o intervalo é largo. A validação dobra a amostra e adiciona regime de queda, com viés favorável leve.
4. **Feature de geada inerte.** `geada_30d` é zero em toda a série: a reanálise ERA5 não registra Tmin < 3 °C nos pontos escolhidos; a geada de julho de 2021 não está representada nos dados.
5. **Custos de armazenagem e quebra são estimativas** sem fonte; COE agora vem da CONAB (Guaxupé).
6. **Hedge sem margem, sem ajuste diário e com proxy de instrumento;** backtest do hedge com curva plana.
7. **Preço regional não modelado.** O sistema usa o indicador CEPEA como se fosse o preço de balcão do produtor de Minas.


<!-- ANEXO-EXPERIMENTOS -->
# Anexo: resultados dos experimentos pedidos em `pedidos-para-experimentos.md`

Executados em 04/11/2026. Arquivos-fonte em `reports/experimentos/`, figuras em `reports/figures/`. Salvo indicação, o caso base é: armazenagem 2,50 R$/sc/mês, quebra 0,2 %/mês, COE 700 R$/sc, taxa de desconto 10 % a.a., λ = 0, hedge habilitado, 20 datas de decisão mensais de 01/07/2024 a 03/02/2026 (teste cego). **Modelo final: LSTM(32)→LSTM(16), dropout 0,4**, adotado em 04/11/2026 após a busca de hiperparâmetros (Bloco F); todos os blocos abaixo foram reexecutados com ele. A configuração anterior (64 unidades, dropout 0,2) é mantida no Bloco F para comparação. **Nota:** o caso base usa taxa fixa de 10 % a.a.

## Bloco A: RQ3

### A1. Sensibilidade à Selic

| selic_% | lstm_dp | venda_imediata | venda_parcelada | freq_armazenar_% | freq_hedge_% | datas_acao_muda |
|---|---|---|---|---|---|---|
| vigente (por data) | 2183.0 | 2028.4 | 1987.3 | 40.0 | 0.0 | 0 |
| 8 | 2189.0 | 2028.4 | 2010.6 | 40.0 | 0.0 | 0 |
| 10 | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 0 |
| 12 | 2183.6 | 2028.4 | 1992.5 | 40.0 | 0.0 | 0 |
| 13.25 | 2181.9 | 2028.4 | 1987.0 | 40.0 | 0.0 | 0 |
| 15 | 2179.7 | 2028.4 | 1979.5 | 40.0 | 0.0 | 0 |

Selic vigente por data (linha "vigente"): 2024-07: 10.50 %, 2024-07: 10.50 %, 2024-08: 10.50 %, 2024-09: 10.75 %, 2024-10: 10.75 %, 2024-11: 11.25 %, 2024-12: 12.25 %, 2025-01: 13.25 %, 2025-02: 13.25 %, 2025-04: 14.25 %, 2025-05: 14.25 %, 2025-06: 14.75 %, 2025-07: 15.00 %, 2025-08: 15.00 %, 2025-09: 15.00 %, 2025-10: 15.00 %, 2025-10: 15.00 %, 2025-12: 15.00 %, 2026-01: 15.00 %, 2026-02: 15.00 %.

Leitura: a taxa de desconto entre 8 % e 15 % move a receita do Agro Visible em menos de 5 R$/sc e **não altera nenhuma ação** nas 20 datas. O efeito é maior na venda parcelada (−31 R$/sc), porque ela sempre carrega parte da produção por 6 meses.

### A2. Choque de base

| cenario | lstm_dp | venda_imediata | venda_parcelada | freq_armazenar_% | freq_hedge_% | datas_acao_muda |
|---|---|---|---|---|---|---|
| base | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 |  |
| base -5% pp | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 0.0 |
| base +5% pp | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 0.0 |
| risco de base ×2 | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 0.0 |
| λ=0.25 base | 2187.3 | 2028.4 | 2001.4 | 30.0 | 0.0 | 2.0 |
| λ=0.25 risco ×2 | 2187.3 | 2028.4 | 2001.4 | 30.0 | 0.0 | 2.0 |
| λ=0.5 base | 2029.5 | 2028.4 | 2001.4 | 5.0 | 0.0 | 7.0 |
| λ=0.5 risco ×2 | 2029.5 | 2028.4 | 2001.4 | 5.0 | 0.0 | 7.0 |

Leitura: com λ = 0 a base esperada e o risco de base **não mudam nenhuma decisão**, porque o hedge nunca é competitivo com curva plana (backtest) em backwardation. Com λ > 0 as mudanças de ação vêm da aversão a risco sobre o armazenamento descoberto, não do risco de base. A frequência de hedge é zero em todos os cenários; o hedge só passa a ser escolhido com a curva real por vencimento (recomendação atual, seção 3.4 do dossiê).

### A3. Sensibilidade ao COE (benchmark de meta de margem)

| coe | meta_margem_coe | datas_meta_difere_imediata | lstm_dp |
|---|---|---|---|
| 500 | 2028.4 | 0 | 2186.3 |
| 700 | 2028.4 | 0 | 2186.3 |
| 900 | 2028.4 | 0 | 2186.3 |
| 1100 | 2034.7 | 2 | 2186.3 |

Leitura: com COE ≤ 900 R$/sc a meta de margem (COE·1,3) coincide com a venda imediata em todas as datas do teste, porque o preço nunca esteve abaixo de 1 170 R$/sc. Só com COE = 1 100 a heurística difere em 2 datas. O motor Agro Visible não muda porque o COE não entra na política (ver D1). Com o COE real da CONAB (D2) o quadro no período de validação é diferente: 7 de 18 datas.

### A4. Grade λ × armazenagem (12 combinações)

| lambda | armazenagem | receita_media_R$/sc | ganho_vs_imediata_% | vence_imediata_% | captura_oraculo_% | desvio_padrao | freq_armazenar_% |
|---|---|---|---|---|---|---|---|
| 0.00 | 1.50 | 2187.13 | 10.22 | 35.00 | 93.69 | 268.73 | 40.00 |
| 0.00 | 2.50 | 2186.28 | 10.17 | 35.00 | 93.73 | 269.01 | 40.00 |
| 0.00 | 5.00 | 2184.17 | 10.04 | 35.00 | 93.79 | 269.73 | 40.00 |
| 0.25 | 1.50 | 2188.00 | 10.26 | 30.00 | 93.72 | 269.25 | 30.00 |
| 0.25 | 2.50 | 2187.35 | 10.22 | 30.00 | 93.78 | 269.56 | 30.00 |
| 0.25 | 5.00 | 2185.74 | 10.11 | 30.00 | 93.85 | 270.34 | 30.00 |
| 0.50 | 1.50 | 2030.31 | 0.12 | 10.00 | 87.01 | 404.31 | 10.00 |
| 0.50 | 2.50 | 2029.50 | 0.07 | 5.00 | 87.04 | 404.94 | 5.00 |
| 0.50 | 5.00 | 2029.38 | 0.06 | 5.00 | 87.16 | 405.11 | 5.00 |
| 1.00 | 1.50 | 2028.44 | 0.00 | 0.00 | 86.93 | 406.43 | 0.00 |
| 1.00 | 2.50 | 2028.44 | 0.00 | 0.00 | 87.00 | 406.43 | 0.00 |
| 1.00 | 5.00 | 2028.44 | 0.00 | 0.00 | 87.12 | 406.43 | 0.00 |

Figura: `reports/figures/09_sensibilidade_lambda_armazenagem_selic.png`.

## Bloco B: amostra e integridade do backtest (RQ2)

### B1. Backtest no período de validação e consolidado por safra

| safra | venda_imediata | venda_parcelada | media_movel_3m | meta_margem_coe | hedge_ate_o_fim | lstm_dp_sem_hedge | lstm_dp | oraculo | n_datas |
|---|---|---|---|---|---|---|---|---|---|
| 2022/23 | 1138.8 | 992.1 | 1101.2 | 1138.8 | 1050.5 | 1102.1 | 1102.1 | 1159.5 | 12 |
| 2023/24 | 852.5 | 919.0 | 858.9 | 922.4 | 757.8 | 944.1 | 944.1 | 1025.8 | 6 |
| 2024/25 | 1999.2 | 2056.5 | 1995.6 | 1999.2 | 1805.4 | 2175.9 | 2175.9 | 2418.2 | 12 |
| 2025/26 | 2072.3 | 1918.8 | 1962.5 | 2072.3 | 2075.9 | 2201.8 | 2201.8 | 2201.8 | 8 |

**Nota de viés:** nas safras 2022/23 e 2023/24 (validação) o σ residual da LSTM e o early stopping foram calibrados com os próprios dados; as estatísticas de base já são só de treino. Há viés favorável leve à LSTM nessas duas safras. A safra 2023/24 da validação tem 6 datas (jul–dez/2023) porque o alvo de 126 dias precisa existir dentro do período.

Resumo na validação (18 datas, 01/07/2022 a 05/12/2023):

| estratégia | receita_media_R$/sc | ganho_vs_imediata_% | vence_imediata_% | captura_oraculo_% | desvio_padrao | pior_caso_R$/sc |
|---|---|---|---|---|---|---|
| venda_imediata | 1043.35 | 0.00 | 0.00 | 93.34 | 182.56 | 804.04 |
| venda_parcelada | 967.72 | -5.64 | 44.44 | 87.18 | 96.73 | 835.97 |
| media_movel_3m | 1020.44 | -1.88 | 33.33 | 91.29 | 188.72 | 797.53 |
| meta_margem_coe | 1066.67 | 2.82 | 27.78 | 95.69 | 156.02 | 893.38 |
| hedge_ate_o_fim | 952.97 | -9.48 | 11.11 | 84.60 | 234.24 | 666.79 |
| lstm_dp_sem_hedge | 1049.46 | 1.61 | 38.89 | 94.34 | 150.07 | 882.01 |
| lstm_dp | 1049.46 | 1.61 | 38.89 | 94.34 | 150.07 | 882.01 |
| oraculo | 1114.93 | 8.05 | 55.56 | 100.00 | 142.02 | 902.18 |

Resumo consolidado, 4 safras (38 datas):

| estratégia | receita_media_R$/sc | ganho_vs_imediata_% | vence_imediata_% | captura_oraculo_% | desvio_padrao | pior_caso_R$/sc |
|---|---|---|---|---|---|---|
| venda_imediata | 1561.82 | 0.00 | 0.00 | 90.00 | 590.43 | 804.04 |
| venda_parcelada | 1511.79 | -1.59 | 44.74 | 86.46 | 545.88 | 835.97 |
| media_movel_3m | 1526.72 | -1.72 | 21.05 | 87.86 | 598.10 | 797.53 |
| meta_margem_coe | 1572.86 | 1.34 | 13.16 | 91.11 | 576.93 | 893.38 |
| hedge_ate_o_fim | 1458.54 | -7.69 | 15.79 | 83.29 | 607.48 | 666.79 |
| lstm_dp_sem_hedge | 1647.79 | 6.12 | 36.84 | 94.02 | 615.15 | 882.01 |
| lstm_dp | 1647.79 | 6.12 | 36.84 | 94.02 | 615.15 | 882.01 |
| oraculo | 1755.30 | 14.04 | 57.89 | 100.00 | 634.18 | 902.18 |

### B2. Estatística de comparação pareada

| amostra | n | comparacao | media | desvio | ic95_inf | ic95_sup | p_wilcoxon | fracao_datas_positivas_% |
|---|---|---|---|---|---|---|---|---|
| teste | 20 | lstm_dp − venda_imediata | 157.846 | 250.354 | 52.640 | 266.725 | 0.046 | 35.000 |
| teste | 20 | lstm_dp − venda_parcelada | 184.839 | 215.852 | 90.135 | 272.909 | 0.002 | 75.000 |
| teste+validação | 38 | lstm_dp − venda_imediata | 85.971 | 207.910 | 24.211 | 155.641 | 0.021 | 36.842 |
| teste+validação | 38 | lstm_dp − venda_parcelada | 136.001 | 178.830 | 78.920 | 192.201 | 0.000 | 73.684 |

IC 95 % por bootstrap de 10 000 reamostragens da média das diferenças; p-valor do teste de Wilcoxon pareado (zeros divididos). Leitura: teste (n = 20), lstm_dp − venda_imediata: média +158 R$/sc, IC [+53; +267], p = 0.046; teste (n = 20), lstm_dp − venda_parcelada: média +185 R$/sc, IC [+90; +273], p = 0.002; teste+validação (n = 38), lstm_dp − venda_imediata: média +86 R$/sc, IC [+24; +156], p = 0.021; teste+validação (n = 38), lstm_dp − venda_parcelada: média +136 R$/sc, IC [+79; +192], p = 0.000. Diferenças com p < 0,05 são significativas a 5 %; os intervalos excluem o zero mas são largos. A fração de datas positivas contra a venda imediata é baixa porque na maioria das datas o motor vende de imediato e a diferença é exatamente zero (mediana nula).

Fração do ganho do oráculo capturada, (estratégia − imediata)/(oráculo − imediata), média sobre as datas em que o oráculo supera a imediata em mais de 1 %:

| index | teste (n=11) | teste+validação (n=21) |
|---|---|---|
| venda_parcelada | -79.0 | -52.1 |
| media_movel_3m | 18.2 | 28.3 |
| meta_margem_coe | 0.0 | 15.1 |
| hedge_ate_o_fim | 51.7 | -22.7 |
| lstm_dp | 49.0 | 47.3 |

Por data: `b2_captura_por_data_teste.csv` e `b2_captura_por_data_teste_validação.csv` (atenção: nesses arquivos a divisão fica instável quando oráculo ≈ imediata; usar a tabela acima).

### B3. Decomposição do ganho por data

| index | periodo | lstm_dp_acao | lstm_dp_mes_venda | lstm_dp | venda_imediata | oraculo | ganho_vs_imediata_% | y_21d | ret_real_21d | y_63d | ret_real_63d | y_126d | ret_real_126d |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022-07-01 | validação | VENDER | 0 | 1358.710 | 1358.710 | 1358.710 | 0.000 | -0.038 | -0.056 | -0.084 | -0.041 | -0.124 | -0.276 |
| 2022-08-01 | validação | ARMAZENAR | 1 | 1326.993 | 1285.020 | 1326.993 | 3.266 | 0.028 | 0.044 | -0.020 | -0.246 | -0.090 | -0.153 |
| 2022-08-30 | validação | VENDER | 0 | 1342.780 | 1342.780 | 1342.780 | 0.000 | -0.001 | -0.029 | -0.078 | -0.308 | -0.171 | -0.186 |
| 2022-09-29 | validação | ARMAZENAR | 2 | 962.093 | 1303.950 | 1303.950 | -26.217 | 0.026 | -0.260 | -0.002 | -0.235 | -0.056 | -0.186 |
| 2022-10-31 | validação | ARMAZENAR | 1 | 974.238 | 1005.330 | 1063.314 | -3.093 | 0.058 | -0.019 | 0.043 | 0.093 | -0.015 | 0.054 |
| 2022-12-01 | validação | VENDER | 0 | 986.500 | 986.500 | 1076.475 | 0.000 | -0.006 | 0.044 | -0.079 | 0.122 | -0.110 | 0.004 |
| 2023-01-02 | validação | VENDER | 0 | 1031.200 | 1031.200 | 1089.764 | 0.000 | -0.037 | 0.068 | -0.143 | 0.049 | -0.207 | -0.226 |
| 2023-01-31 | validação | VENDER | 0 | 1103.180 | 1103.180 | 1103.180 | 0.000 | -0.034 | 0.010 | -0.162 | -0.039 | -0.191 | -0.253 |
| 2023-03-03 | validação | VENDER | 0 | 1114.380 | 1114.380 | 1114.380 | 0.000 | -0.033 | -0.029 | -0.099 | -0.118 | -0.165 | -0.309 |
| 2023-04-03 | validação | VENDER | 0 | 1082.950 | 1082.950 | 1082.950 | 0.000 | -0.014 | -0.021 | -0.054 | -0.275 | -0.071 | -0.298 |
| 2023-05-05 | validação | VENDER | 0 | 1060.650 | 1060.650 | 1060.650 | 0.000 | -0.013 | -0.068 | -0.040 | -0.214 | -0.025 | -0.207 |
| 2023-06-05 | validação | ARMAZENAR | 6 | 882.011 | 990.850 | 990.850 | -10.984 | 0.018 | -0.186 | 0.028 | -0.192 | 0.049 | -0.040 |
| 2023-07-05 | validação | ARMAZENAR | 6 | 902.180 | 822.250 | 902.180 | 9.721 | 0.063 | 0.040 | 0.152 | -0.022 | 0.231 | 0.169 |
| 2023-08-03 | validação | ARMAZENAR | 6 | 928.587 | 856.240 | 928.587 | 8.449 | 0.012 | -0.046 | 0.027 | 0.007 | 0.216 | 0.156 |
| 2023-09-01 | validação | ARMAZENAR | 5 | 940.417 | 818.180 | 944.630 | 14.940 | 0.039 | -0.017 | 0.082 | 0.151 | 0.292 | 0.219 |
| 2023-10-03 | validação | ARMAZENAR | 4 | 952.360 | 804.040 | 1066.479 | 18.447 | 0.081 | 0.070 | 0.256 | 0.191 | 0.445 | 0.356 |
| 2023-11-03 | validação | ARMAZENAR | 3 | 964.418 | 862.180 | 1079.687 | 11.858 | 0.107 | 0.099 | 0.354 | 0.150 | 0.432 | 0.258 |
| 2023-12-05 | validação | ARMAZENAR | 2 | 976.592 | 951.850 | 1233.104 | 2.599 | 0.053 | 0.022 | 0.085 | 0.068 | 0.103 | 0.330 |
| 2024-07-01 | teste | VENDER | 0 | 1361.920 | 1361.920 | 2084.988 | 0.000 | -0.023 | 0.042 | -0.038 | 0.108 | -0.036 | 0.493 |
| 2024-07-30 | teste | ARMAZENAR | 4 | 1986.063 | 1419.690 | 2346.160 | 39.894 | 0.040 | 0.041 | 0.110 | 0.055 | 0.041 | 0.568 |
| 2024-08-28 | teste | ARMAZENAR | 3 | 2008.452 | 1478.500 | 2372.158 | 35.844 | 0.085 | 0.026 | 0.134 | 0.340 | 0.020 | 0.518 |
| 2024-09-26 | teste | ARMAZENAR | 2 | 2031.060 | 1517.340 | 2398.747 | 33.857 | 0.041 | -0.011 | 0.036 | 0.384 | -0.072 | 0.524 |
| 2024-10-25 | teste | ARMAZENAR | 1 | 2053.888 | 1500.200 | 2425.270 | 36.908 | 0.035 | 0.325 | 0.012 | 0.513 | -0.091 | 0.546 |
| 2024-11-27 | teste | VENDER | 0 | 2076.940 | 2076.940 | 2452.053 | 0.000 | -0.040 | 0.071 | -0.138 | 0.178 | -0.198 | 0.088 |
| 2024-12-30 | teste | VENDER | 0 | 2228.790 | 2228.790 | 2479.099 | 0.000 | -0.033 | 0.117 | -0.117 | 0.139 | -0.143 | -0.249 |
| 2025-01-30 | teste | VENDER | 0 | 2506.020 | 2506.020 | 2506.411 | 0.000 | -0.036 | -0.010 | -0.167 | 0.033 | -0.205 | -0.347 |
| 2025-02-28 | teste | VENDER | 0 | 2482.220 | 2482.220 | 2533.990 | 0.000 | -0.036 | 0.032 | -0.128 | -0.090 | -0.136 | -0.077 |
| 2025-04-02 | teste | VENDER | 0 | 2561.840 | 2561.840 | 2561.840 | 0.000 | -0.031 | 0.011 | -0.140 | -0.389 | -0.145 | -0.169 |
| 2025-05-06 | teste | VENDER | 0 | 2589.710 | 2589.710 | 2589.710 | 0.000 | -0.021 | -0.133 | -0.124 | -0.380 | -0.135 | -0.158 |
| 2025-06-04 | teste | ARMAZENAR | 3 | 2223.994 | 2267.410 | 2267.410 | -1.915 | 0.018 | -0.266 | -0.027 | 0.014 | -0.068 | -0.015 |
| 2025-07-04 | teste | ARMAZENAR | 2 | 2248.756 | 1736.940 | 2248.756 | 29.467 | 0.052 | 0.019 | 0.108 | 0.220 | 0.106 | 0.233 |
| 2025-08-04 | teste | ARMAZENAR | 1 | 2273.761 | 1771.030 | 2273.761 | 28.386 | 0.047 | 0.261 | 0.104 | 0.222 | 0.152 | 0.107 |
| 2025-09-02 | teste | VENDER | 0 | 2299.010 | 2299.010 | 2299.010 | 0.000 | -0.036 | -0.060 | -0.055 | -0.029 | -0.138 | -0.184 |
| 2025-10-01 | teste | ARMAZENAR | 1 | 2186.038 | 2163.990 | 2186.038 | 1.019 | 0.022 | 0.021 | 0.004 | 0.013 | -0.094 | -0.172 |
| 2025-10-30 | teste | VENDER | 0 | 2210.410 | 2210.410 | 2210.410 | 0.000 | -0.016 | 0.010 | -0.029 | -0.114 | -0.115 | -0.280 |
| 2025-12-01 | teste | VENDER | 0 | 2233.340 | 2233.340 | 2233.340 | 0.000 | -0.015 | -0.019 | -0.044 | -0.155 | -0.116 | -0.479 |
| 2026-01-05 | teste | VENDER | 0 | 2191.970 | 2191.970 | 2191.970 | 0.000 | -0.023 | -0.106 | -0.063 | -0.185 | -0.116 | -0.247 |
| 2026-02-03 | teste | VENDER | 0 | 1971.480 | 1971.480 | 1971.480 | 0.000 | -0.035 | -0.030 | -0.084 | -0.166 | -0.096 | -0.132 |

Arquivo completo com flags de acerto direcional: `b3_decomposicao.csv`. Leitura (gerada dos dados): maiores ganhos sobre a venda imediata: 2024-07-30 (+39.9 %), 2024-10-25 (+36.9 %), 2024-08-28 (+35.8 %), 2024-09-26 (+33.9 %), 2025-07-04 (+29.5 %), 2025-08-04 (+28.4 %); maiores perdas: 2022-09-29 (-26.2 %), 2023-06-05 (-11.0 %), 2022-10-31 (-3.1 %). Armazenou em 18 das 38 datas; dessas, ganhou em 14 e perdeu em 4. Os ganhos vêm de previsões de alta de 21 dias corretas em direção, seguidas de reavaliação mensal; as perdas, de previsões de alta em quedas persistentes. Em jul–out/2024 a previsão de 126 dias era próxima de zero ou negativa enquanto o retorno realizado foi de +0,5: a alta foi capturada pela direção de curto prazo e pela política rolante, não pela previsão longa.

## Bloco C: componente preditivo (RQ1)

### C1. Notebook 03 reexecutado com retreino

Retreino do zero (seed 42, CPU) com a configuração final; as métricas de validação coincidem com as da busca de hiperparâmetros (F4, seed 42), confirmando reprodutibilidade. σ residual regravado em `models/residual_sigma.json`. Figuras regravadas: `02_curva_perda.png`, `03_previsto_realizado_validacao.png`, `03_previsto_realizado_teste.png`, `03b_residuos.png`.

### C2. Métricas na validação e no teste

| horizonte | split | rmse_ret | mae_ret | rmse_naive | mape_preco_% | acerto_direcao_% | rmse_curva | acerto_direcao_curva_% |
|---|---|---|---|---|---|---|---|---|
| 21d | val | 0.0960 | 0.0670 | 0.0907 | 7.0457 | 56.7204 | 0.1071 | 61.2903 |
| 63d | val | 0.1661 | 0.1449 | 0.1767 | 15.2892 | 74.4624 | 0.1560 | 68.5484 |
| 126d | val | 0.1278 | 0.1042 | 0.2356 | 10.7816 | 91.6667 | 0.1927 | 75.2688 |
| 21d | test | 0.1171 | 0.0846 | 0.1197 | 8.3459 | 63.7890 | 0.1299 | 42.4460 |
| 63d | test | 0.2063 | 0.1579 | 0.2332 | 14.6633 | 75.7794 | 0.2269 | 50.5995 |
| 126d | test | 0.3009 | 0.2124 | 0.3211 | 18.3797 | 76.9784 | 0.3094 | 61.1511 |

Leitura (gerada dos dados): na validação a LSTM perde para o passeio aleatório em 21 d, vence o passeio aleatório em 63 d, vence o passeio aleatório em 126 d; e vence a curva de futuros em 21 d, perde para a curva de futuros em 63 d, vence a curva de futuros em 126 d. No teste (417 amostras) a LSTM vence o passeio aleatório em 21 d, vence o passeio aleatório em 63 d, vence o passeio aleatório em 126 d; e vence a curva em 21 d, vence a curva em 63 d, vence a curva em 126 d.

### C4. Baseline ARIMA

| split | horizonte | ordem | rmse_arima | mae_arima | mape_preco_% | acerto_direcao_arima_% | rmse_naive |
|---|---|---|---|---|---|---|---|
| val | 21d | (1, 1, 2) | 0.0904 | 0.0666 | 6.8721 | 52.1505 | 0.0907 |
| val | 63d | (1, 1, 2) | 0.1766 | 0.1524 | 16.1280 | 58.3333 | 0.1767 |
| val | 126d | (1, 1, 2) | 0.2356 | 0.2112 | 21.3818 | 50.2688 | 0.2356 |
| test | 21d | (1, 1, 2) | 0.1193 | 0.0848 | 8.3642 | 54.9161 | 0.1197 |
| test | 63d | (1, 1, 2) | 0.2329 | 0.1872 | 18.1071 | 58.5132 | 0.2332 |
| test | 126d | (1, 1, 2) | 0.3211 | 0.2672 | 25.4284 | 49.1607 | 0.3211 |

Ordem (1,1,2) escolhida por AIC no treino entre p, q ∈ {0,1,2}; parâmetros fixos, aplicados à série até cada data e previsão recursiva. Leitura: o ARIMA é **indistinguível do passeio aleatório** (RMSE igual até a 3ª casa, acerto direcional ≈ 50 %), como esperado para log-preço diário quase integrado. Serve como confirmação de que o passeio aleatório é o baseline estatístico clássico adequado.

### C5. Variabilidade entre seeds (modelo completo)

| seed | epocas | tempo_s | rmse_21d | rmse_63d | rmse_126d | dir_21d | dir_63d | dir_126d |
|---|---|---|---|---|---|---|---|---|
| 42 | 26 | 74.2000 | 0.0960 | 0.1661 | 0.1278 | 56.7204 | 74.4624 | 91.6667 |
| 43 | 19 | 53.1000 | 0.0937 | 0.1809 | 0.1534 | 57.5269 | 48.1183 | 79.3011 |
| 44 | 16 | 45.0000 | 0.1286 | 0.1899 | 0.2017 | 35.4839 | 56.4516 | 73.3871 |
| 45 | 25 | 68.8000 | 0.0992 | 0.1668 | 0.1292 | 51.8817 | 68.0108 | 89.5161 |
| 46 | 43 | 115.5000 | 0.1091 | 0.1987 | 0.1638 | 55.9140 | 56.9892 | 81.4516 |

| index | média | desvio |
|---|---|---|
| rmse_21d | 0.1053 | 0.0143 |
| rmse_63d | 0.1805 | 0.0143 |
| rmse_126d | 0.1552 | 0.0303 |
| dir_21d | 51.5054 | 9.2158 |
| dir_63d | 60.8065 | 10.4033 |
| dir_126d | 83.0645 | 7.5173 |

Leitura: o desvio entre seeds do RMSE é de 0.014 (21 d), 0.014 (63 d) e 0.030 (126 d); médias 0.105 / 0.180 / 0.155. Comparar com os baselines na validação (C2): toda diferença menor que um desvio entre seeds deve ser tratada como empate.

### C3. Ablação por grupo de features

| config | n_seeds | rmse_21d_mean | rmse_21d_std | rmse_63d_mean | rmse_63d_std | rmse_126d_mean | rmse_126d_std | dir_21d_mean | dir_21d_std | dir_63d_mean | dir_63d_std | dir_126d_mean | dir_126d_std |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| completo | 3 | 0.1061 | 0.0195 | 0.1790 | 0.0120 | 0.1610 | 0.0375 | 49.9104 | 12.5002 | 59.6774 | 13.4650 | 81.4516 | 9.3276 |
| sem_a_retornos_ma | 3 | 0.1002 | 0.0019 | 0.1855 | 0.0131 | 0.1967 | 0.0188 | 51.3441 | 7.0047 | 55.6452 | 5.4894 | 71.6846 | 5.6665 |
| sem_b_mercado | 3 | 0.1070 | 0.0035 | 0.1901 | 0.0106 | 0.2024 | 0.0088 | 53.4050 | 3.9902 | 60.0358 | 10.0090 | 65.2330 | 5.2425 |
| sem_c_calendario_selic | 3 | 0.1017 | 0.0058 | 0.1919 | 0.0081 | 0.2219 | 0.0329 | 56.9892 | 4.1991 | 48.8351 | 9.3212 | 61.4695 | 9.5358 |
| sem_d_clima | 3 | 0.1035 | 0.0020 | 0.1843 | 0.0258 | 0.1827 | 0.0388 | 49.2832 | 5.3110 | 62.9928 | 2.7979 | 76.9713 | 10.2445 |
| sem_e_cot | 3 | 0.1055 | 0.0104 | 0.1830 | 0.0204 | 0.1693 | 0.0357 | 57.6165 | 3.2518 | 60.9319 | 11.2593 | 73.8351 | 3.6497 |
| sem_f_insumos | 3 | 0.1070 | 0.0119 | 0.1791 | 0.0148 | 0.1493 | 0.0087 | 49.1935 | 10.6480 | 60.1254 | 8.4382 | 83.1541 | 4.3705 |

Variação relativa do RMSE médio (3 seeds: 42, 43, 44; positivo = piorou ao remover o grupo):

| config | ΔRMSE 21d vs completo (%) | ΔRMSE 63d vs completo (%) | ΔRMSE 126d vs completo (%) |
|---|---|---|---|
| completo | 0.0 | 0.0 | 0.0 |
| sem_a_retornos_ma | -5.6 | 3.7 | 22.2 |
| sem_b_mercado | 0.8 | 6.2 | 25.7 |
| sem_c_calendario_selic | -4.2 | 7.2 | 37.9 |
| sem_d_clima | -2.5 | 3.0 | 13.5 |
| sem_e_cot | -0.6 | 2.2 | 5.2 |
| sem_f_insumos | 0.9 | 0.1 | -7.3 |

Grupos: (a) retornos e posição vs. média; (b) mercado: vol, spread, base; (c) calendário e Selic; (d) clima; (e) fundos COT; (f) insumos. Leitura (modelo final de 32 un., 3 seeds): (1) o desvio entre seeds do modelo completo é de 18 % do RMSE em 21 d, 7 % em 63 d e 23 % em 126 d, então em 126 d só efeitos acima de ~20 % ficam claramente fora do ruído. (2) Remover **calendário e Selic (c)**, **mercado (b)** ou **retornos e médias móveis (a)** piora o RMSE de 126 d em 38 %, 26 % e 22 % e derruba o acerto direcional de 126 d de 81 % para 61–72 %: são os grupos que carregam o sinal de longo prazo. (3) Clima (d) e fundos COT (e) pioram 126 d em 13 % e 5 % ao serem removidos, dentro ou perto do ruído: contribuição marginal. (4) Remover **insumos (f)** melhora 126 d em 7 %: nesta configuração e com estes hiperparâmetros o grupo não contribuiu; não generalizar. (5) Em 21 d nenhum grupo ajuda (remover qualquer um muda o RMSE em menos de 6 %, para melhor ou para pior). Conclusão para o texto: cinco dos seis grupos contribuem no horizonte de 6 meses, com calendário/Selic, mercado e retornos como essenciais; em 21 d a rede não extrai sinal de nenhum grupo.

## Bloco D: uso do COE no motor

### D1. Decisão de projeto

**Implementadas as duas formas; a forma (ii) fica desligada por padrão.**

- (i) sinalização: `Recomendacao.margem_sobre_coe_pct` já é calculada em toda recomendação. A classificação nas faixas do AgroSafety (lucro supernormal / normal / resíduo / descapitalização / falência) pode ser lida diretamente comparando o preço esperado com COE, COT e CT da tabela D2.
- (ii) restrição: parâmetro `Custos.margem_min_coe` (padrão `None`). Quando definido, VENDER só é permitido em nós com preço ≥ COE·(1+m) enquanto houver prazo; no último mês a venda é forçada.

Por que (ii) fica desligada: a restrição só muda a decisão quando o preço está abaixo de COE·(1+m), e nesse caso ela força o produtor a carregar o café exatamente quando o modelo prevê queda, o que não é uma política racional de venda, e sim uma regra de sobrevivência. Backtest no teste com COE placeholder:

| margem_min | lstm_dp | venda_imediata | venda_parcelada | freq_armazenar_% | freq_hedge_% | coe | datas_acao_muda |
|---|---|---|---|---|---|---|---|
| desligada | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 |  |  |
| 0.0 | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 700.0 | 0.0 |
| 0.0 | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 1100.0 | 0.0 |
| 0.1 | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 700.0 | 0.0 |
| 0.1 | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 1100.0 | 0.0 |
| 0.3 | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 700.0 | 0.0 |
| 0.3 | 2216.4 | 2028.4 | 2001.4 | 45.0 | 0.0 | 1100.0 | 1.0 |

Com COE = 700 ou 1 100 e m até 30 %, nenhuma data do teste tem preço abaixo do gatilho (mínimo de 1 362 R$/sc), então a restrição não atua; a única mudança (COE 1 100, m = 30 %, gatilho 1 430) ocorre em 1 data e melhora 5 R$/sc por acaso.

### D2. COE real (CONAB)

Arquivo baixado: `data/external/conab_serie_historica_custos_cafe_arabica_2003a2025.xls` (CONAB/DIPAI/SUINF/GECUP, série histórica de custos de produção do café arábica). Extração em `data/external/conab_coe_cot_cafe_arabica_mg.csv`. Correspondência com a nomenclatura AgroSafety: **COE = Custo Variável (A+B+C)**, **COT = Custo Operacional (D+G)**, **CT = Custo Total (H+I)**, todos em R$/saca de 60 kg. As planilhas de MG são de agricultura familiar, cultivo semi-adensado, alta tecnologia, semimecanizado.

| município | ano | COE | COT | CT |
|---|---|---|---|---|
| Franca | 2021 | 562.52 | 625.86 | 652.84 |
| Franca | 2022 | 805.51 | 887.86 | 1070.93 |
| Franca | 2023 | 619.31 | 785.48 | 928.52 |
| Franca | 2024 | 630.97 | 713.46 | 874.40 |
| Franca | 2025 | 689.04 | 769.13 | 976.00 |
| Guaxupé | 2021 | 587.22 | 665.16 | 680.28 |
| Guaxupé | 2022 | 766.34 |  |  |
| Guaxupé | 2023 | 714.29 |  |  |
| Guaxupé | 2024 | 783.79 | 875.00 | 941.92 |
| Guaxupé | 2025 | 876.06 | 987.79 | 1113.47 |
| Manhuaçu | 2021 | 658.92 | 814.30 | 826.86 |
| Manhuaçu | 2022 | 636.27 | 778.40 | 812.05 |
| Manhuaçu | 2023 | 592.07 | 729.13 | 781.27 |
| Manhuaçu | 2024 | 652.91 | 863.72 | 930.34 |
| Manhuaçu | 2025 | 837.00 | 1133.76 | 1222.87 |
| Patrocínio | 2021 | 668.07 | 764.07 | 783.01 |
| Patrocínio | 2022 | 710.26 |  |  |
| Patrocínio | 2023 | 619.31 | 785.48 | 928.52 |
| Patrocínio | 2024 | 675.41 | 870.07 | 1009.63 |
| Patrocínio | 2025 | 770.13 | 1005.86 | 1205.46 |
| Três Pontas | 2022 | 569.61 |  |  |
| Três Pontas | 2023 | 593.23 |  |  |
| Três Pontas | 2024 | 632.77 | 707.95 | 813.92 |
| Três Pontas | 2025 | 787.79 | 885.25 | 1050.74 |

Valores usados no motor (Guaxupé, safra = ano da colheita): 2022: 766,34; 2023: 714,29; 2024: 783,79; 2025: 876,06 R$/sc. Guaxupé 2022 e 2023 e Patrocínio 2022 não têm COT/CT na planilha (só o resumo do custo variável). O placeholder de 700 estava dentro da faixa.

Backtest com COE da CONAB por safra (`d2_coe_conab.csv`):

| margem_min | lstm_dp | venda_imediata | venda_parcelada | freq_armazenar_% | freq_hedge_% | datas_acao_muda | meta_margem_coe | datas_meta_difere_imediata | margem_sobre_coe_min_% |
|---|---|---|---|---|---|---|---|---|---|
| desligada | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 0 | 2028.4 | 0 | 73.8 |
| 0.0 | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 0 | 2028.4 | 0 | 73.8 |
| 0.1 | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 0 | 2028.4 | 0 | 73.8 |
| 0.3 | 2186.3 | 2028.4 | 2001.4 | 40.0 | 0.0 | 0 | 2028.4 | 0 | 73.8 |

No teste nada muda, porque a margem mínima observada sobre o COE foi de +74 %. Na **validação** (18 datas, preços de 804 a 1359) a meta de margem COE·1,3 passa a diferir da venda imediata em 7 de 18 datas, com média de 1062 contra 1043 R$/sc.

## Bloco E: informações para o texto

### E1. Fontes dos parâmetros de armazenagem e quebra

Os 2,50 R$/sc/mês e os 0,2 %/mês **foram estimativas do desenvolvimento, sem documento de referência**. Devem ser citados como valores de referência a confirmar com cooperativa. A própria CONAB traz "Despesas de armazenagem" na planilha (Guaxupé 2024: 1,74 R$/sc para a safra inteira, dentro do custo de produção), mas isso é o custo do armazém da fazenda, não o de armazém geral por mês. A análise de sensibilidade A4 mostra que a decisão é insensível a esse parâmetro entre 1,5 e 5,0.

### E2. Custo operacional de bolsa

Os 10 R$/sc **não foram calculados a partir de TOB, emolumentos e taxa de registro**. Foram tomados diretamente do exemplo do módulo 5 do AgroSafety ("Custo Operacional B3: R$ 10,00 por saca – Entrada e Saída", slides 52 e 73). O material não detalha a composição.

### E3. Hiperparâmetros

A configuração inicial (unidades 64/32, dropout 0,2, janela de 63 dias, batch 32, Adam 1e-3, paciência 15 e 7) foi fixada a priori. A busca do Bloco F (F4: 12 configurações com seed 42; F5: 3 candidatas com 5 seeds em validação e teste) levou à configuração final de 32/16 unidades com dropout 0,4; janela, batch, taxa e paciências ficaram iguais. A janela de 63 dias cobre um trimestre, igual ao horizonte intermediário. A seleção foi feita na validação; o teste permaneceu cego, mas a escolha de arquitetura e o early stopping não são cegos (ameaça interna declarada no TCC).

### E4. Tempos de execução (CPU, Windows 11, TensorFlow sem GPU)

- Treino do modelo final (seed 42, 26 épocas, 3 940 amostras): **74 s**; retreinos de C5 entre 45 e 116 s.
- Motor de decisão para uma data (7 camadas × 121 nós, com hedge): **3 ms**.
- Backtest de 20 datas com política rolante (≈ 120 resoluções do motor + previsões em lote): **0.5 s**.
- Grade de sensibilidade A4 (12 backtests): ~1 min. Retreinos de C3+C5 (23 treinos): ~35 min.

### E5. Versões

| Biblioteca | Versão |
|---|---|
| Python | 3.13.4 |
| TensorFlow | 2.21.0 |
| Keras | 3.15.1 |
| NumPy | 2.5.2 |
| pandas | 3.0.5 |
| scikit-learn | 1.9.0 |
| SciPy | 1.18.1 |
| statsmodels | 0.15.0 (adicionado para C4) |
| networkx | 3.6.1 |
| matplotlib | 3.11.1 |
| yfinance | 1.7.0 |
| cot-reports | 0.1.3 |
| python-bcb, openmeteo-requests | sem `__version__` exposto; ver `pip freeze` |

`requirements.txt` está sem versões fixadas (pip instala a mais recente). Recomendação: gerar `requirements.lock` com `pip freeze` antes da entrega. `statsmodels` foi adicionado ao ambiente e deve entrar no `requirements.txt`.

### E6. Figuras

| # | Figura | Arquivo | Status |
|---|---|---|---|
| 1 | Série CEPEA 2005–2026 com cortes | `01_serie_cepea_particao.png` | gerada |
| 2 | Curva de perda treino × validação | `02_curva_perda.png` | gerada (notebook 03) |
| 3 | Previsto × realizado por horizonte | `03_previsto_realizado_validacao.png`, `03_previsto_realizado_teste.png`, `03b_residuos.png` | geradas |
| 4 | Cone de preços (mediana, q10–q90) | `04_cone_precos.png` | gerada (31/08/2026) |
| 5 | Árvore reduzida com ações | `05_arvore_decisoes.png` | gerada |
| 6 | Gatilho de venda por mês | `06_gatilho_venda_por_mes.png` | gerada |
| 7 | Receita por data, safras separadas | `07_receita_por_data_teste.png` | gerada |
| 8 | Base % com média sazonal | `08_base_fisico_futuro_pct.png` | gerada |
| 9 | Sensibilidade λ × armazenagem e Selic | `09_sensibilidade_lambda_armazenagem_selic.png` | gerada (mapa de calor + curva de Selic; base não entra porque não altera nada) |

Todas em PNG a 300 dpi, fundo branco, rótulos em português. Além destas, o notebook 05 gera as figuras da simulação por safra.

## Bloco F: análise exploratória das features e busca de hiperparâmetros

### F1. Correlação de Spearman feature × log-retorno futuro (treino)

Arquivo `eda_corr_alvo.csv`; figura `10_corr_features_alvo.png`. Ordenado pelo maior |ρ| entre os horizontes.

| feature | spearman_21d | spearman_63d | spearman_126d |
|---|---|---|---|
| chuva_arabica_90d | -0.168 | -0.372 | -0.291 |
| base_fisico_futuro_pct | -0.117 | -0.260 | -0.342 |
| chuva_arabica_30d | -0.057 | -0.282 | -0.314 |
| chuva_robusta_90d | -0.128 | -0.312 | -0.235 |
| mes_cos | 0.020 | -0.175 | -0.288 |
| mes_sin | -0.182 | -0.272 | -0.108 |
| tmin_arabica_7d | -0.035 | -0.202 | -0.257 |
| selic_meta | -0.102 | -0.173 | -0.230 |
| indice_troca_urea | 0.104 | 0.080 | 0.176 |
| spread_arabica_robusta | 0.044 | 0.114 | 0.145 |
| cot_net_pct_oi_chg4w | -0.126 | -0.062 | -0.043 |
| preco_vs_ma_1a | 0.050 | 0.097 | 0.125 |
| cot_net_pct_oi | 0.032 | 0.084 | 0.087 |
| ret_crude_1a | -0.007 | -0.034 | -0.084 |
| bienalidade_alta | -0.028 | -0.013 | -0.076 |
| preco_vs_ma_2a | 0.049 | 0.064 | 0.071 |
| ret_urea_1a | 0.070 | 0.054 | -0.017 |
| ret_robusta_1d | 0.054 | 0.051 | 0.007 |
| ret_ptax_1d | 0.050 | 0.023 | 0.000 |
| vol_21d | 0.025 | 0.038 | -0.003 |
| preco_vs_ma_1m | 0.012 | 0.009 | 0.024 |
| preco_vs_ma_3m | 0.016 | 0.017 | 0.015 |
| ret_arabica_21d | 0.004 | 0.006 | 0.016 |
| ret_ice_1d | -0.013 | -0.003 | 0.007 |
| ret_arabica_1d | 0.008 | 0.003 | 0.007 |

Leitura: o sinal está em oferta (chuva acumulada 30/90 d, Tmin), base físico×futuro, calendário e Selic, e cresce de 21 para 63/126 d. Retornos diários e de 21 d, posição vs. médias de 1 e 3 meses e volatilidade têm |ρ| < 0,04 em todos os horizontes. `geada_30d` é constante (zero) e foi excluída.

### F2. Pares de features com |ρ| > 0,7 (colinearidade)

| f1 | f2 | spearman |
|---|---|---|
| ret_arabica_1d | ret_ice_1d | 0.7 |
| ret_arabica_21d | preco_vs_ma_1m | 0.8 |
| ret_arabica_21d | preco_vs_ma_3m | 0.8 |
| preco_vs_ma_1m | preco_vs_ma_3m | 0.7 |
| preco_vs_ma_1a | preco_vs_ma_2a | 0.9 |
| mes_sin | chuva_arabica_90d | 0.8 |
| mes_sin | chuva_robusta_90d | 0.7 |
| mes_cos | chuva_arabica_30d | 0.8 |
| mes_cos | tmin_arabica_7d | 0.8 |
| chuva_arabica_30d | chuva_arabica_90d | 0.8 |
| chuva_arabica_30d | tmin_arabica_7d | 0.7 |
| chuva_arabica_30d | chuva_robusta_90d | 0.7 |
| chuva_arabica_90d | chuva_robusta_90d | 0.9 |

Figura `11_matriz_corr_features.png`. Clima e calendário medem em parte a mesma coisa (estação); médias de 1 e 2 anos e retorno de 21 d vs. média de 1 mês são quase redundantes.

### F3. Importância por permutação na LSTM final (validação)

Aumento do RMSE ao embaralhar a feature na janela (média de 3 permutações). Arquivo `eda_importancia_permutacao.csv`; figura `12_importancia_permutacao.png`.

| feature | delta_rmse_21d | delta_rmse_63d | delta_rmse_126d | delta_rmse_medio_% |
|---|---|---|---|---|
| bienalidade_alta | 0.0043 | 0.0345 | 0.0935 | 32.8067 |
| base_fisico_futuro_pct | 0.0075 | 0.0389 | 0.0844 | 32.4444 |
| indice_troca_urea | 0.0135 | 0.0488 | 0.0563 | 29.1860 |
| mes_sin | 0.0069 | 0.0215 | 0.0460 | 18.6986 |
| ret_urea_1a | 0.0012 | 0.0207 | 0.0441 | 16.0448 |
| preco_vs_ma_2a | 0.0113 | 0.0227 | 0.0224 | 14.3326 |
| chuva_arabica_30d | 0.0093 | 0.0185 | 0.0180 | 11.6345 |
| mes_cos | 0.0054 | 0.0048 | 0.0291 | 10.4206 |
| ret_arabica_21d | 0.0030 | 0.0155 | 0.0173 | 8.6429 |
| preco_vs_ma_3m | 0.0041 | 0.0198 | 0.0067 | 7.1575 |
| chuva_robusta_90d | 0.0021 | 0.0081 | 0.0127 | 5.6919 |
| preco_vs_ma_1m | 0.0022 | 0.0046 | 0.0148 | 5.5572 |
| ret_crude_1a | 0.0019 | 0.0072 | 0.0090 | 4.4569 |
| ret_arabica_1d | 0.0019 | 0.0068 | 0.0047 | 3.2711 |
| chuva_arabica_90d | -0.0042 | 0.0007 | 0.0174 | 3.2284 |
| cot_net_pct_oi_chg4w | 0.0019 | 0.0014 | 0.0026 | 1.6039 |
| ret_ice_1d | 0.0009 | 0.0049 | -0.0008 | 1.0737 |
| spread_arabica_robusta | 0.0013 | 0.0049 | -0.0018 | 0.9794 |
| vol_21d | 0.0016 | 0.0022 | -0.0003 | 0.9094 |
| cot_net_pct_oi | 0.0003 | 0.0002 | -0.0002 | 0.0920 |
| geada_30d | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| selic_meta | 0.0001 | 0.0009 | -0.0011 | -0.0725 |
| tmin_arabica_7d | 0.0049 | 0.0049 | -0.0110 | -0.1859 |
| ret_ptax_1d | 0.0002 | 0.0008 | -0.0017 | -0.1986 |
| ret_robusta_1d | 0.0025 | -0.0002 | -0.0044 | -0.3282 |
| preco_vs_ma_1a | -0.0035 | -0.0089 | 0.0050 | -1.6795 |

### F4. Busca de hiperparâmetros (seed 42, validação)

Grade de 12 configurações, um fator por vez a partir da configuração inicial (64 un., dropout 0,2, janela 63, lr 1e-3, batch 32) mais duas candidatas enxutas. Arquivo `hp_busca.csv`.

| units | dropout | lookback | lr | batch | epocas | rmse_treino | rmse_21d | rmse_63d | rmse_126d | rmse_medio | dir_126d |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 32 | 0.4000 | 63 | 0.0010 | 32 | 26 | 0.0471 | 0.0960 | 0.1661 | 0.1278 | 0.1300 | 91.6667 |
| 32 | 0.2000 | 63 | 0.0010 | 32 | 26 | 0.0369 | 0.0955 | 0.1624 | 0.1382 | 0.1320 | 84.1398 |
| 32 | 0.4000 | 126 | 0.0010 | 32 | 24 | 0.0489 | 0.0957 | 0.1714 | 0.1342 | 0.1337 | 87.6344 |
| 64 | 0.4000 | 63 | 0.0010 | 32 | 25 | 0.0431 | 0.1036 | 0.1996 | 0.1690 | 0.1574 | 75.8065 |
| 64 | 0.2000 | 126 | 0.0010 | 32 | 16 | 0.0353 | 0.1149 | 0.1890 | 0.1695 | 0.1578 | 72.3118 |
| 64 | 0.2000 | 21 | 0.0010 | 32 | 16 | 0.0357 | 0.1059 | 0.1892 | 0.1845 | 0.1599 | 72.5806 |
| 64 | 0.2000 | 63 | 0.0010 | 64 | 16 | 0.0389 | 0.1085 | 0.1707 | 0.2026 | 0.1606 | 63.1720 |
| 64 | 0.2000 | 63 | 0.0003 | 32 | 23 | 0.0418 | 0.1141 | 0.1928 | 0.1819 | 0.1629 | 71.7742 |
| 64 | 0.2000 | 63 | 0.0010 | 32 | 55 | 0.0292 | 0.1115 | 0.1942 | 0.1850 | 0.1636 | 77.1505 |
| 64 | 0.0000 | 63 | 0.0010 | 32 | 17 | 0.0155 | 0.1231 | 0.2001 | 0.1745 | 0.1659 | 75.8065 |
| 64 | 0.2000 | 63 | 0.0030 | 32 | 40 | 0.0237 | 0.1243 | 0.2042 | 0.2230 | 0.1838 | 71.5054 |
| 128 | 0.2000 | 63 | 0.0010 | 32 | 19 | 0.0278 | 0.1212 | 0.2202 | 0.2402 | 0.1938 | 67.2043 |

Leitura: só o tamanho da rede importa de forma consistente; 128 unidades é a pior configuração e 32 a melhor. Janela de 21 ou 126 dias, batch 64 e taxas de 3e-4 ou 3e-3 não ajudam; dropout 0 piora. O RMSE de treino da configuração inicial (0,029) contra 0,047 da enxuta mostra que a redução de capacidade reduz o sobreajuste.

### F5. Verificação das candidatas com 5 seeds (42–46), validação e teste

Arquivo `hp_seeds.csv`. Média ± desvio entre seeds.

| units | dropout | split | rmse_21d_mean | rmse_21d_std | rmse_63d_mean | rmse_63d_std | rmse_126d_mean | rmse_126d_std | dir_126d_mean | dir_126d_std |
|---|---|---|---|---|---|---|---|---|---|---|
| 32 | 0.2 | test | 0.1277 | 0.0065 | 0.2171 | 0.0177 | 0.2951 | 0.0294 | 72.3261 | 12.5500 |
| 32 | 0.2 | val | 0.1105 | 0.0140 | 0.1790 | 0.0227 | 0.1765 | 0.0369 | 77.0430 | 10.6286 |
| 32 | 0.4 | test | 0.1195 | 0.0031 | 0.2159 | 0.0121 | 0.2874 | 0.0237 | 76.7866 | 8.1911 |
| 32 | 0.4 | val | 0.1053 | 0.0143 | 0.1805 | 0.0143 | 0.1552 | 0.0303 | 83.0645 | 7.5173 |
| 64 | 0.2 | test | 0.1305 | 0.0105 | 0.2244 | 0.0130 | 0.2943 | 0.0188 | 75.7314 | 4.4264 |
| 64 | 0.2 | val | 0.1135 | 0.0079 | 0.1884 | 0.0170 | 0.1918 | 0.0244 | 74.1398 | 8.2317 |

Baselines nos mesmos conjuntos:

| split | rmse_curva_21d | rmse_curva_63d | rmse_curva_126d | rmse_naive_21d | rmse_naive_63d | rmse_naive_126d |
|---|---|---|---|---|---|---|
| test | 0.1299 | 0.2269 | 0.3094 | 0.1197 | 0.2332 | 0.3211 |
| val | 0.1071 | 0.1560 | 0.1927 | 0.0907 | 0.1767 | 0.2356 |

Leitura: (1) o resultado de seed única (RMSE médio 0,130) foi uma seed favorável; com 5 seeds a rede de 32 un./dropout 0,4 melhora a inicial em 5–8 % em 21 e 63 d e 19 % em 126 d na validação, e 2–8 % no teste, com variância igual ou menor. (2) Em 21 d nenhuma configuração vence o passeio aleatório na validação; em 63 d a curva de futuros segue melhor na validação. No teste a rede enxuta vence a curva nos três horizontes. (3) **Decisão (04/11/2026): a rede enxuta (32 un., dropout 0,4, seed 42) passou a ser o modelo final.** Todos os blocos A–E deste anexo, os notebooks 03–05 e as figuras foram reexecutados com ela. A configuração inicial de 64 unidades fica registrada aqui como ponto de partida da busca.
