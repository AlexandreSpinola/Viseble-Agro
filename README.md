# Agro Visible — Sistema de Suporte à Decisão Prescritiva na Comercialização do Café

TCC — Alexandre Marques Spinola Cardoso
Orientador: Gustavo Andrade do Vale | Coorientador: Paulo Henrique Sales

Abordagem híbrida que acopla previsões de preços via redes neurais **LSTM** a um motor
prescritivo de **programação dinâmica estocástica** (grafo temporal de decisões), para
recomendar ao cafeicultor **quando vender ou armazenar** o café pós-colheita,
maximizando a receita líquida descontados custos de armazenagem, COE/COT e risco de base.

## Estrutura do projeto

```
├── data/
│   ├── raw/            # Dados brutos coletados das APIs (imutáveis)
│   ├── external/       # Dados de terceiros (planilhas CONAB, COT/CFTC etc.)
│   ├── interim/        # Dados intermediários em transformação
│   └── processed/      # Datasets finais alinhados para modelagem
├── notebooks/          # Notebooks de exploração e experimentos (numerados: 01-, 02-...)
├── models/             # Modelos treinados (pesos LSTM, scalers, checkpoints)
├── reports/
│   ├── figures/        # Gráficos e figuras para o TCC (PNG 300 dpi)
│   ├── experimentos/   # CSVs dos experimentos (blocos A–E)
│   └── dossie-tecnico.md, anexo-experimentos.md, pedidos-para-experimentos.md
├── src/
│   ├── data/           # Coleta (yfinance, python-bcb, CEPEA, CFTC, clima)
│   ├── features/       # Engenharia de atributos e alinhamento temporal
│   ├── models/         # Treino (lstm.py), sequências (dataset.py) e previsão por data (predict.py)
│   ├── decision/       # engine.py (DP: vender × armazenar × armazenar+hedge), hedge.py (curva, base, risco de base), benchmarks.py, backtest.py, safra.py (colheita + 12 meses)
│   ├── experiments/    # experimentos do TCC: rq2_rq3.py (sensibilidade, validação, estatística), retreinos.py (ablação, seeds), arima.py, anexo.py
│   └── visualization/  # Visualizações
└── tests/              # Testes
```

## Setup

```powershell
# Criar e ativar o ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt
```

## Fontes de dados

| Dado | Fonte | Biblioteca |
|---|---|---|
| Futuros de Café (ICE NY - Coffee C) | Yahoo Finance | `yfinance` (KC=F contínuo + curva por vencimento KC{H,K,N,U,Z}yy.NYB, acumulada em `data/raw/ice_curve.csv`) |
| Câmbio PTAX e Selic | Banco Central (SGS) | `python-bcb` |
| Preço físico arábica/robusta | CEPEA/ESALQ | scraping / CSV |
| Posições de fundos (COT) | CFTC | `cot-reports` |
| Clima histórico | INMET / Open-Meteo | `openmeteo-requests` |
| Custos de produção (COE/COT) | CONAB | planilhas em `data/external/` |

## Etapas do MVP

1. Coleta e tratamento de dados (`src/data`)
2. Engenharia de features e alinhamento temporal (`src/features`)
3. Treino da LSTM e previsão de trajetórias de preço (`src/models`)
4. Motor prescritivo (vender × armazenar × armazenar com hedge em futuros) por programação dinâmica (`src/decision`)
5. Backtesting contra benchmarks: venda imediata, venda parcelada, média móvel, meta de margem sobre COE

## Notebooks

| # | Conteúdo |
|---|---|
| 01 | Coleta e alinhamento das fontes |
| 02 | Engenharia de features e split cronológico |
| 03 | LSTM multi-horizonte (log-retornos 21/63/126 d) vs. passeio aleatório e vs. previsão implícita na curva de futuros |
| 04 | Curva de futuros e base, motor prescritivo (DP estocástica com hedge), grafo de decisões e backtest × benchmarks |
| 05 | Simulação por safra: colheita em julho + 12 meses para vender, política rolante, 4 safras (2 cegas) |

Linha de comando: `python -m src.models.lstm` (treino), `python -m src.decision.backtest` (backtest mensal no teste) e `python -m src.decision.safra` (simulação por safra).

## Hedge e base (módulo 5 AgroSafety)

- `preço travado = futuro do vencimento (R$/saca) × (1 + base esperada) − custo operacional B3`
- Base modelada em **% do futuro** (estável, ≈ −20%), sazonal por mês; **risco de base** = desvio da variação da base em 21/63/126 dias úteis. Ambos estimados só no treino (`data/processed/base_stats.json`).
- O Yahoo só mantém contratos ativos: rode `python -m src.data.futures_curve` periodicamente para acumular a curva histórica. Para datas sem curva o motor assume curva plana (hedge rolado no 1º vencimento).

## Experimentos

`python -m src.experiments.rq2_rq3` (blocos A, B, C2, D1, D2, E4 e figuras), `python -m src.experiments.retreinos` (C3, C5; ~35 min em CPU), `python -m src.experiments.arima` (C4) e `python -m src.experiments.anexo` (monta `reports/anexo-experimentos.md` e o anexa ao dossiê). COE/COT reais da CONAB em `data/external/conab_coe_cot_cafe_arabica_mg.csv`.
