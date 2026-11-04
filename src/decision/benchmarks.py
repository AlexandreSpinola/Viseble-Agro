"""Estratégias de comercialização para comparação no backtest.

Todas recebem o caminho REAL de preços a partir da data de decisão (índice =
datas, valores = R$/saca) e devolvem a receita líquida realizada por saca,
descontando armazenagem, quebra e custo de oportunidade — mesma contabilidade
do motor prescritivo, para a comparação ser justa.

A regra de cada benchmark só usa informação disponível até o dia da venda.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd

from src.decision.engine import K_MAX, PASSO, Custos


def liquido(preco: float, mes: int, c: Custos) -> float:
    """Valor presente (na data da decisão) de vender no mês `mes` ao preço `preco`."""
    bruto = preco * (1 - c.quebra_pct_mes) ** mes
    armazenagem = sum(c.armazenagem_saca_mes * c.delta_mensal ** k for k in range(mes))
    return bruto * c.delta_mensal ** mes - armazenagem


def preco_mes(caminho: pd.Series, k: int) -> float:
    return float(caminho.iloc[min(k * PASSO, len(caminho) - 1)])


def venda_imediata(caminho: pd.Series, c: Custos, k_max: int = K_MAX, **_) -> float:
    return liquido(preco_mes(caminho, 0), 0, c)


def venda_parcelada(caminho: pd.Series, c: Custos, k_max: int = K_MAX, **_) -> float:
    """1/(K+1) da produção a cada mês (diluição de risco, prática comum)."""
    return float(np.mean([liquido(preco_mes(caminho, k), k, c) for k in range(k_max + 1)]))


def media_movel(caminho: pd.Series, c: Custos, ma: pd.Series | None = None, k_max: int = K_MAX, **_) -> float:
    """Vende no primeiro mês em que o preço supera a média móvel de 3 meses; senão no fim."""
    for k in range(k_max + 1):
        p = preco_mes(caminho, k)
        data = caminho.index[min(k * PASSO, len(caminho) - 1)]
        if ma is not None and p > float(ma.loc[data]):
            return liquido(p, k, c)
    return liquido(preco_mes(caminho, k_max), k_max, c)


def meta_margem_coe(caminho: pd.Series, c: Custos, margem: float = 0.30, k_max: int = K_MAX, **_) -> float:
    """Vende quando o preço atinge COE·(1+margem); senão no último mês."""
    alvo = c.coe_saca * (1 + margem)
    for k in range(k_max + 1):
        p = preco_mes(caminho, k)
        if p >= alvo:
            return liquido(p, k, c)
    return liquido(preco_mes(caminho, k_max), k_max, c)


def oraculo(caminho: pd.Series, c: Custos, k_max: int = K_MAX, **_) -> float:
    """Limite superior: vende no melhor mês (conhece o futuro). Só referência."""
    return max(liquido(preco_mes(caminho, k), k, c) for k in range(k_max + 1))


BENCHMARKS: dict[str, Callable] = {
    "venda_imediata": venda_imediata,
    "venda_parcelada": venda_parcelada,
    "media_movel_3m": media_movel,
    "meta_margem_coe": meta_margem_coe,
}
