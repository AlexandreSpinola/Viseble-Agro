"""Motor prescritivo: vender × armazenar × armazenar com hedge, por programação
dinâmica estocástica.

Formulação (parada ótima com custos de carregamento e instrumento de hedge):

- Tempo: passos mensais k = 0..K (K ≤ 6 meses ≈ 126 dias úteis, horizonte
  máximo da LSTM). k = 0 é a data da decisão (pós-colheita).
- Estado: (k, x) com x = ln P, preço físico CEPEA em R$/saca, discretizado
  numa grade.
- Transição: x_{k+1} = x_k + Δμ_k + ε, ε ~ N(0, Δσ²_k). Δμ_k vem da trajetória
  prevista pela LSTM (ŷ_21, ŷ_63, ŷ_126 interpolados) e Δσ²_k da incerteza
  residual do modelo na validação — o grafo temporal de decisões é uma cadeia
  de Markov sobre a grade de preços.
- Ações em cada nó:
    VENDER            recebe P·(1−quebra)^k no físico e encerra;
    ARMAZENAR         paga armazenagem do mês, desconta e segue descoberto;
    HEDGE até m > k   vende futuro do vencimento m e armazena até m: recebe
                      F_{k,m}·(1+b_m) − custo_op (preço travado, módulo 5
                      AgroSafety), sujeito só ao risco de base. A curva nos
                      nós futuros desloca-se com o físico: F_{k,m} = F_{0,m}·P_k/P_0.
- Valor: V_K(x) = vender; V_k(x) = max(vender, armazenar, max_m hedge_m), com
  armazenar = −c_arm + δ·CE[V_{k+1}] e CE = E − λ·DP (certeza-equivalente;
  λ = 0 → neutro ao risco). O hedge é penalizado por λ·risco_de_base.

Saída: recomendação em k = 0 (ação, vencimento do hedge, preço travado),
gatilhos de venda por mês e a distribuição do mês de venda sob a política.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.models.dataset import HORIZONS

PASSO = 21                        # dias úteis por passo (~1 mês)
K_MAX = max(HORIZONS) // PASSO    # 6 meses
VENDER, ARMAZENAR, HEDGE = 0, 1, 2
NOME_ACAO = {VENDER: "VENDER", ARMAZENAR: "ARMAZENAR", HEDGE: "ARMAZENAR+HEDGE"}


@dataclass
class Custos:
    """Parâmetros econômicos (R$/saca de 60 kg). Ajustar com CONAB/cooperativa/B3."""
    armazenagem_saca_mes: float = 2.50     # armazém geral / cooperativa
    quebra_pct_mes: float = 0.002          # perda técnica de peso e qualidade
    coe_saca: float = 700.0                # custo operacional efetivo (CONAB)
    taxa_desconto_aa: float = 0.10         # custo de oportunidade (≈ Selic)
    aversao_risco: float = 0.0             # λ: penaliza o desvio-padrão da continuação
    custo_op_b3_saca: float = 10.0         # corretagem + emolumentos, entrada e saída
    permitir_hedge: bool = True            # habilita a ação ARMAZENAR+HEDGE
    margem_min_coe: float | None = None    # D1(ii): VENDER só se P >= COE·(1+m) enquanto houver prazo;
                                           # None desliga a restrição; no último mês a venda é forçada

    @property
    def delta_mensal(self) -> float:
        return (1 + self.taxa_desconto_aa) ** (-1 / 12)


@dataclass
class Recomendacao:
    acao: str                          # "VENDER" | "ARMAZENAR" | "ARMAZENAR+HEDGE"
    preco_hoje: float
    valor_vender: float                # R$/saca vendendo hoje
    valor_armazenar: float             # R$/saca esperado (VP) armazenando descoberto
    valor_hedge: float                 # R$/saca (VP) do melhor hedge; nan se desabilitado
    mes_hedge: int | None              # vencimento (meses) do melhor hedge
    preco_travado: float               # R$/saca travado pelo hedge (nominal, no mês de venda)
    ganho_esperado_pct: float          # (melhor alternativa / vender − 1)·100
    mes_venda_esperado: float          # E[mês de venda] sob a política ótima
    gatilhos: pd.Series                # preço mínimo (R$/saca) que dispara VENDER, por mês
    dist_mes_venda: pd.Series          # P(vender no mês k)
    trajetoria_prevista: pd.Series     # preço central previsto por mês
    curva_futuro: pd.Series            # futuro R$/saca usado para cada mês de venda
    base_esperada: pd.Series           # base % esperada por mês de venda
    margem_sobre_coe_pct: float = field(default=np.nan)
    _grid: np.ndarray = field(default=None, repr=False)
    _politica: np.ndarray = field(default=None, repr=False)

    def __str__(self) -> str:
        h = (f"hedge→{self.mes_hedge}m R$ {self.valor_hedge:.0f} (trava R$ {self.preco_travado:.0f})"
             if self.mes_hedge is not None else "hedge n/d")
        return (f"{self.acao} | preço hoje R$ {self.preco_hoje:.0f}/sc | "
                f"vender R$ {self.valor_vender:.0f} × armazenar R$ {self.valor_armazenar:.0f} × {h} "
                f"({self.ganho_esperado_pct:+.1f}% vs vender) | mês de venda esperado {self.mes_venda_esperado:.1f} | "
                f"margem sobre COE {self.margem_sobre_coe_pct:+.0f}%")


def _trajetoria(yhat: dict[int, float], sigma: dict[int, float],
                k_max: int = K_MAX) -> tuple[np.ndarray, np.ndarray]:
    """Interpola ŷ_h e σ_h (h = 21, 63, 126) para os passos mensais 0..k_max.

    Além de 126 dias (fora do alcance da LSTM) a extrapolação é conservadora:
    deriva mantida no último valor previsto e incerteza crescendo com a raiz
    do tempo a partir de σ_126, como num passeio aleatório."""
    hs = np.array([0, *HORIZONS], dtype=float)
    ks = np.arange(k_max + 1) * PASSO
    mu = np.interp(ks, hs, [0.0, *[yhat[h] for h in HORIZONS]])
    sd = np.interp(ks, hs, [0.0, *[sigma[h] for h in HORIZONS]])
    # incerteza acumulada não pode diminuir com o horizonte
    sd = np.sqrt(np.maximum.accumulate(sd ** 2))
    alem = ks > hs[-1]
    if alem.any():
        sd[alem] = sd[~alem][-1] * np.sqrt(ks[alem] / hs[-1])
    return mu, sd


def _matriz_transicao(grid: np.ndarray, dmu: float, dsd: float) -> np.ndarray:
    """P[i, j] = P(x_{k+1} = grid[j] | x_k = grid[i]) discretizando N(x_i + dmu, dsd²)."""
    dsd = max(dsd, 1e-4)
    z = (grid[None, :] - (grid[:, None] + dmu)) / dsd
    P = np.exp(-0.5 * z ** 2)
    return P / P.sum(axis=1, keepdims=True)


def recomendar(preco_hoje: float, yhat: dict[int, float], sigma: dict[int, float],
               custos: Custos | None = None, k_max: int = K_MAX, n_grid: int = 121,
               futuros: np.ndarray | None = None, base_pct: np.ndarray | None = None,
               risco_base_pct: np.ndarray | None = None) -> Recomendacao:
    """Resolve a DP para a data de decisão e devolve a recomendação.

    k_max          prazo máximo de armazenagem em meses (encurta no backtest rolante;
                   pode passar de 6: além da LSTM a trajetória é extrapolada)
    futuros        F[m], m = 0..k_max: futuro em R$/saca do vencimento que cobre o
                   mês de venda m (índice 0 = primeiro vencimento hoje)
    base_pct       b[m]: base percentual esperada no mês de venda m
    risco_base_pct rb[j]: desvio (fração) da variação da base em j meses, j = 0..k_max
    Sem `futuros`, a ação de hedge é desabilitada."""
    c = custos or Custos()
    K = max(1, int(k_max))
    mu, sd = _trajetoria(yhat, sigma, K)
    x0 = np.log(preco_hoje)
    amp = 4 * max(sd[-1], 0.05) + np.abs(mu).max()
    grid = np.linspace(x0 - amp, x0 + amp, n_grid)
    precos = np.exp(grid)
    d = c.delta_mensal

    espacamento = grid[1] - grid[0]
    dmu = np.diff(mu)
    dsd = np.sqrt(np.clip(np.diff(sd ** 2), espacamento ** 2, None))
    P = [_matriz_transicao(grid, dmu[k], dsd[k]) for k in range(K)]

    # --- hedge: valor em k de travar até m (função do preço no nó, via deslocamento paralelo)
    usar_hedge = c.permitir_hedge and futuros is not None
    if usar_hedge:
        F = np.asarray(futuros, dtype=float)[: K + 1]
        b = np.asarray(base_pct if base_pct is not None else np.zeros(K + 1), dtype=float)[: K + 1]
        rb = np.asarray(risco_base_pct if risco_base_pct is not None else np.zeros(K + 1), dtype=float)[: K + 1]

    def valor_hedge_no(k: int) -> tuple[np.ndarray, np.ndarray]:
        """Melhor hedge partindo de k, por nó: (valor, vencimento m)."""
        melhor = np.full(n_grid, -np.inf)
        venc = np.full(n_grid, -1)
        for m in range(k + 1, K + 1):
            desloc = precos / preco_hoje
            travado = F[m] * desloc * (1 + b[m]) - c.custo_op_b3_saca          # R$/sc nominal em m
            arm = sum(c.armazenagem_saca_mes * d ** j for j in range(m - k))
            risco = c.aversao_risco * rb[m - k] * F[m] * desloc
            v = (travado - risco) * (1 - c.quebra_pct_mes) ** m * d ** (m - k) - arm
            melhora = v > melhor
            melhor[melhora] = v[melhora]
            venc[melhora] = m
        return melhor, venc

    # --- indução retroativa
    vender = np.stack([precos * (1 - c.quebra_pct_mes) ** k for k in range(K + 1)])
    V = np.empty_like(vender)
    politica = np.full(vender.shape, VENDER, dtype=int)
    venc_hedge = np.full(vender.shape, -1, dtype=int)
    V[K] = vender[K]
    for k in range(K - 1, -1, -1):
        esperado = P[k] @ V[k + 1]
        dp = np.sqrt(np.clip(P[k] @ V[k + 1] ** 2 - esperado ** 2, 0, None))
        armazenar = -c.armazenagem_saca_mes + d * (esperado - c.aversao_risco * dp)
        vender_k = vender[k]
        if c.margem_min_coe is not None:      # restrição de margem sobre COE (nunca no último mês)
            vender_k = np.where(precos >= c.coe_saca * (1 + c.margem_min_coe), vender[k], -np.inf)
        opcoes = [vender_k, armazenar]
        if usar_hedge:
            vh, mh = valor_hedge_no(k)
            opcoes.append(vh)
            venc_hedge[k] = mh
        opcoes = np.stack(opcoes)
        politica[k] = opcoes.argmax(axis=0)
        V[k] = opcoes.max(axis=0)

    gatilhos = pd.Series(
        [float(precos[politica[k] == VENDER].min()) if (politica[k] == VENDER).any() else np.nan
         for k in range(K + 1)], index=range(K + 1), name="gatilho_venda")

    # --- distribuição do mês de venda (hedge até m conta como venda em m)
    i0 = int(np.abs(grid - x0).argmin())
    massa = np.zeros(n_grid)
    massa[i0] = 1.0
    dist = np.zeros(K + 1)
    for k in range(K + 1):
        dist[k] += massa[politica[k] == VENDER].sum()
        for m in range(k + 1, K + 1):
            dist[m] += massa[(politica[k] == HEDGE) & (venc_hedge[k] == m)].sum()
        massa = np.where(politica[k] == ARMAZENAR, massa, 0.0)
        if k < K:
            massa = massa @ P[k]
    dist_mes = pd.Series(dist, index=range(K + 1), name="p_venda")

    # --- valores em k = 0 no preço de hoje
    valor_vender = float(vender[0, i0])
    esperado0 = float(P[0][i0] @ V[1])
    dp0 = np.sqrt(max(float(P[0][i0] @ V[1] ** 2) - esperado0 ** 2, 0.0))
    valor_armazenar = float(-c.armazenagem_saca_mes + d * (esperado0 - c.aversao_risco * dp0))
    if usar_hedge:
        vh0, mh0 = valor_hedge_no(0)
        valor_hedge, mes_hedge = float(vh0[i0]), int(mh0[i0])
        preco_travado = float(F[mes_hedge] * (1 + b[mes_hedge]) - c.custo_op_b3_saca)
    else:
        valor_hedge, mes_hedge, preco_travado = np.nan, None, np.nan
    acao = NOME_ACAO[int(politica[0, i0])]
    melhor_alt = max(valor_armazenar, valor_hedge if usar_hedge else -np.inf)

    return Recomendacao(
        acao=acao, preco_hoje=preco_hoje,
        valor_vender=valor_vender, valor_armazenar=valor_armazenar,
        valor_hedge=valor_hedge, mes_hedge=mes_hedge, preco_travado=preco_travado,
        ganho_esperado_pct=(melhor_alt / valor_vender - 1) * 100,
        mes_venda_esperado=float((dist_mes.index * dist_mes).sum()),
        gatilhos=gatilhos, dist_mes_venda=dist_mes,
        trajetoria_prevista=pd.Series(preco_hoje * np.exp(mu), index=range(K + 1), name="preco_previsto"),
        curva_futuro=pd.Series(F if usar_hedge else np.nan, index=range(K + 1), name="futuro_brl"),
        base_esperada=pd.Series(b if usar_hedge else np.nan, index=range(K + 1), name="base_pct"),
        margem_sobre_coe_pct=(preco_hoje / c.coe_saca - 1) * 100,
        _grid=grid, _politica=politica,
    )


def grafo_decisoes(rec: Recomendacao, yhat: dict[int, float], sigma: dict[int, float],
                   n_ramos: int = 3) -> "networkx.DiGraph":
    """Grafo temporal (árvore de cenários enxuta) para visualização: em cada mês,
    ramos nos quantis 10/50/90 da distribuição prevista, anotados com a ação ótima."""
    import networkx as nx
    from scipy.stats import norm

    K = len(rec.gatilhos) - 1
    mu, sd = _trajetoria(yhat, sigma, K)
    qs = np.linspace(0.1, 0.9, n_ramos)
    G = nx.DiGraph()
    G.add_node((0, 0), mes=0, preco=rec.preco_hoje, acao=rec.acao)
    for k in range(1, K + 1):
        for j, q in enumerate(qs):
            p = rec.preco_hoje * np.exp(mu[k] + norm.ppf(q) * sd[k])
            i = int(np.abs(rec._grid - np.log(p)).argmin())
            acao = NOME_ACAO[int(rec._politica[k, i])]
            G.add_node((k, j), mes=k, preco=float(p), acao=acao, quantil=float(q))
            for jp in (range(n_ramos) if k > 1 else [0]):
                G.add_edge((k - 1, jp), (k, j))
    return G
