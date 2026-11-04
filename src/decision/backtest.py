"""Backtest cego no conjunto de TESTE: motor prescritivo × benchmarks.

Para cada data de decisão (mensal, a partir de jul/2024), simula a política
LSTM+DP de forma ROLANTE — a cada mês reavalia com a previsão daquela data e
o prazo restante — e compara a receita líquida por saca com os benchmarks
sobre o mesmo caminho real de preços.

Hedge no backtest: a curva por vencimento não existe para datas passadas
(Yahoo descarta contratos vencidos), então a decisão usa curva plana (primeiro
vencimento) e o resultado realizado é o de um hedge rolado no primeiro
vencimento: receita = físico na venda + (F_entrada − F_saída) − custo_op,
com F em R$/saca (ICE × PTAX). Rolagens ficam embutidas na série contínua.
"""

import numpy as np
import pandas as pd

from src.decision.benchmarks import BENCHMARKS, liquido, oraculo, preco_mes
from src.decision.engine import HEDGE, K_MAX, NOME_ACAO, PASSO, Custos, recomendar
from src.decision.hedge import base_por_mes, base_stats, futuro_por_mes, risco_base_pct
from src.models.dataset import HORIZONS, TARGET
from src.models.predict import forecast_batch, load_artifacts, residual_sigma

FUT = "ice_arabica_brl_sc"


def liquido_hedge(caminho: pd.Series, futuro: pd.Series, k_in: int, m_out: int, c: Custos) -> float:
    """VP (na data da decisão) de armazenar de k_in a m_out com hedge no futuro."""
    spot = preco_mes(caminho, m_out) * (1 - c.quebra_pct_mes) ** m_out
    pnl = preco_mes(futuro, k_in) - preco_mes(futuro, m_out)
    efetivo = spot + pnl - c.custo_op_b3_saca
    armazenagem = sum(c.armazenagem_saca_mes * c.delta_mensal ** j for j in range(m_out))
    return efetivo * c.delta_mensal ** m_out - armazenagem


def hedge_ate_o_fim(caminho: pd.Series, futuro: pd.Series, c: Custos) -> float:
    """Benchmark: armazena o prazo todo com hedge desde o dia da decisão."""
    return liquido_hedge(caminho, futuro, 0, K_MAX, c)


def politica_lstm_dp(caminho: pd.Series, futuro: pd.Series, ptax: pd.Series, c: Custos,
                     previsoes: pd.DataFrame, sigma: dict[int, float], stats: dict,
                     hedge: bool) -> tuple[float, int, str]:
    """Aplica a DP mês a mês. Devolve (receita líquida, mês de venda, ação inicial)."""
    acao0 = None
    for k in range(K_MAX):
        p = preco_mes(caminho, k)
        data = caminho.index[k * PASSO]
        yhat = {h: float(previsoes.loc[data, f"y_{h}d"]) for h in HORIZONS}
        restante = K_MAX - k
        kw = {}
        if hedge:
            kw = dict(
                futuros=futuro_por_mes(data, float(ptax.loc[data]), preco_mes(futuro, k), restante),
                base_pct=base_por_mes(data, restante, stats=stats),
                risco_base_pct=np.array([risco_base_pct(j * PASSO, stats) for j in range(restante + 1)]),
            )
        cc = Custos(**{**c.__dict__, "permitir_hedge": hedge})
        rec = recomendar(p, yhat, sigma, cc, k_max=restante, **kw)
        acao0 = acao0 or rec.acao
        if rec.acao == "VENDER":
            return liquido(p, k, c), k, acao0
        if rec.acao == NOME_ACAO[HEDGE]:
            m = k + rec.mes_hedge
            return liquido_hedge(caminho, futuro, k, m, c), m, acao0
    return liquido(preco_mes(caminho, K_MAX), K_MAX, c), K_MAX, acao0


def rodar_backtest(custos: Custos | None = None, inicio: str = "2024-07-01", fim: str | None = None,
                   passo_dias: int = PASSO, stats: dict | None = None,
                   selic_vigente: bool = False, coe_por_safra: dict | None = None) -> pd.DataFrame:
    """Backtest mensal entre `inicio` e `fim` (padrão: até onde há 6 meses de futuro).

    stats           estatísticas de base (padrão: base_stats()); permite choques (A2)
    selic_vigente   se True, a taxa de desconto de cada data é a meta Selic vigente
                    nela, em vez de custos.taxa_desconto_aa
    coe_por_safra   {ano_safra: COE R$/sc} (D2, CONAB); substitui custos.coe_saca
                    pelo valor da safra da data de decisão (ano-safra começa em julho)
    Além das receitas, grava por data (B3): ação em k=0, mês de venda, previsões
    ŷ_21/63/126 na data e retornos realizados nos mesmos horizontes."""
    c = custos or Custos()
    model, scaler, df = load_artifacts()
    sigma = residual_sigma()
    stats = stats or base_stats()
    price, futuro, ptax = df[TARGET], df[FUT], df["ptax_venda"]

    pos0 = df.index.searchsorted(pd.Timestamp(inicio))
    pos_fim = df.index.searchsorted(pd.Timestamp(fim), side="right") if fim else len(df)
    origens = [i for i in range(pos0, len(df) - K_MAX * PASSO, passo_dias) if i < pos_fim]
    datas_prev = pd.DatetimeIndex(
        [df.index[i + k * PASSO] for i in origens for k in range(K_MAX)]).unique()
    previsoes = forecast_batch(datas_prev, df, model, scaler)

    linhas = []
    for i in origens:
        sl = slice(i, i + K_MAX * PASSO + 1)
        caminho, fut = price.iloc[sl], futuro.iloc[sl]
        d0 = df.index[i]
        ci = c
        if selic_vigente:
            ci = Custos(**{**ci.__dict__, "taxa_desconto_aa": float(df["selic_meta"].loc[d0]) / 100})
        if coe_por_safra:
            safra = d0.year if d0.month >= 7 else d0.year - 1
            ci = Custos(**{**ci.__dict__, "coe_saca": float(coe_por_safra[safra])})
        row = {"data_decisao": d0, "preco_inicial": float(caminho.iloc[0]),
               "selic_usada_%": ci.taxa_desconto_aa * 100, "coe_usado": ci.coe_saca}
        for nome, fn in BENCHMARKS.items():
            row[nome] = fn(caminho, ci, ma=df["ma_3m"])
        row["hedge_ate_o_fim"] = hedge_ate_o_fim(caminho, fut, ci)
        row["lstm_dp_sem_hedge"], _, _ = politica_lstm_dp(caminho, fut, ptax, ci, previsoes, sigma, stats, hedge=False)
        row["lstm_dp"], row["lstm_dp_mes_venda"], row["lstm_dp_acao"] = politica_lstm_dp(
            caminho, fut, ptax, ci, previsoes, sigma, stats, hedge=True)
        row["oraculo"] = oraculo(caminho, ci)
        for h in HORIZONS:
            row[f"y_{h}d"] = float(previsoes.loc[d0, f"y_{h}d"])
            row[f"ret_real_{h}d"] = float(np.log(caminho.iloc[h] / caminho.iloc[0]))
        linhas.append(row)
    return pd.DataFrame(linhas).set_index("data_decisao")


ESTRATEGIAS = [*BENCHMARKS, "hedge_ate_o_fim", "lstm_dp_sem_hedge", "lstm_dp", "oraculo"]


def resumo(bt: pd.DataFrame) -> pd.DataFrame:
    """Receita líquida média, ganho % sobre venda imediata e captura do oráculo."""
    est = [e for e in ESTRATEGIAS if e in bt]
    base = bt["venda_imediata"]
    out = pd.DataFrame({
        "receita_media_R$/sc": bt[est].mean(),
        "ganho_vs_imediata_%": ((bt[est].div(base, axis=0) - 1) * 100).mean(),
        "vence_imediata_%": (bt[est].gt(base + 1e-9, axis=0)).mean() * 100,
        "captura_oraculo_%": (bt[est].div(bt["oraculo"], axis=0) * 100).mean(),
        "desvio_padrao": bt[est].std(),
        "pior_caso_R$/sc": bt[est].min(),
    })
    return out.round(2)


if __name__ == "__main__":
    bt = rodar_backtest()
    print(resumo(bt))
