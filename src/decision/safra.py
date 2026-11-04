"""Simulação por safra: o cafeicultor tem o café em mãos na colheita e um ano
para vender.

Diferenças em relação ao backtest mensal (backtest.py):
- uma decisão por safra, ancorada na colheita (padrão: 1º dia útil de julho,
  pico da colheita do arábica em MG/SP);
- horizonte de 12 meses (252 dias úteis), além do alcance da LSTM (126 d):
  a política é ROLANTE — reavaliada todo mês com a previsão daquela data e o
  prazo restante — e além de 6 meses a trajetória é extrapolada de forma
  conservadora (engine._trajetoria);
- devolve também a trilha mês a mês (preço, ação, previsão), para o gráfico
  da safra.

Não exige retreino: o modelo foi treinado até jun/2022, e as safras 2024/25
e 2025/26 estão inteiras no teste cego. As safras 2022/23 e 2023/24 (validação)
ampliam a amostra, mas serviram ao early stopping e não são cegas.
"""

import numpy as np
import pandas as pd

from src.decision.backtest import FUT, liquido_hedge
from src.decision.benchmarks import BENCHMARKS, liquido, oraculo, preco_mes
from src.decision.engine import HEDGE, K_MAX, NOME_ACAO, PASSO, Custos, recomendar
from src.decision.hedge import base_por_mes, base_stats, futuro_por_mes, risco_base_pct
from src.models.dataset import HORIZONS, TARGET
from src.models.predict import forecast_batch, load_artifacts, residual_sigma

MESES_SAFRA = 12


def data_colheita(ano: int, df: pd.DataFrame, mes: int = 7) -> pd.Timestamp:
    """1º dia útil (com cotação CEPEA) do mês de colheita do ano-safra `ano`."""
    pos = df.index.searchsorted(pd.Timestamp(year=ano, month=mes, day=1))
    return df.index[pos]


def simular_safra(ano: int, custos: Custos | None = None, mes_colheita: int = 7,
                  meses: int = MESES_SAFRA, hedge: bool = True,
                  artefatos: tuple | None = None) -> dict:
    """Simula a comercialização da safra `ano` a partir da colheita.

    Devolve dict com: receitas por estratégia (R$/saca, VP na colheita), a
    trilha mensal da política LSTM+DP e o caminho real de preços."""
    c = custos or Custos()
    model, scaler, df = artefatos or load_artifacts()
    sigma = residual_sigma()
    stats = base_stats()
    price, futuro, ptax = df[TARGET], df[FUT], df["ptax_venda"]

    i0 = df.index.get_loc(data_colheita(ano, df, mes_colheita))
    if i0 + meses * PASSO >= len(df):
        raise ValueError(f"safra {ano}: faltam dados para {meses} meses após a colheita")
    sl = slice(i0, i0 + meses * PASSO + 1)
    caminho, fut = price.iloc[sl], futuro.iloc[sl]
    datas = pd.DatetimeIndex([caminho.index[k * PASSO] for k in range(meses)])
    previsoes = forecast_batch(datas, df, model, scaler)

    # --- política rolante LSTM+DP, com trilha
    trilha, receita, mes_venda = [], None, None
    for k in range(meses):
        data = datas[k]
        p = preco_mes(caminho, k)
        yhat = {h: float(previsoes.loc[data, f"y_{h}d"]) for h in HORIZONS}
        restante = meses - k
        kw = {}
        if hedge:
            kw = dict(
                futuros=futuro_por_mes(data, float(ptax.loc[data]), preco_mes(fut, k), restante),
                base_pct=base_por_mes(data, restante, stats=stats),
                risco_base_pct=np.array([risco_base_pct(j * PASSO, stats) for j in range(restante + 1)]),
            )
        cc = Custos(**{**c.__dict__, "permitir_hedge": hedge})
        rec = recomendar(p, yhat, sigma, cc, k_max=restante, **kw)
        trilha.append({"mes": k, "data": data, "preco": p, "acao": rec.acao,
                       "y_21d": yhat[21], "y_63d": yhat[63], "y_126d": yhat[126],
                       "valor_vender": rec.valor_vender, "valor_armazenar": rec.valor_armazenar,
                       "valor_hedge": rec.valor_hedge, "mes_hedge": rec.mes_hedge})
        if rec.acao == "VENDER":
            receita, mes_venda = liquido(p, k, c), k
            break
        if rec.acao == NOME_ACAO[HEDGE]:
            m = k + rec.mes_hedge
            receita, mes_venda = liquido_hedge(caminho, fut, k, m, c), m
            break
    if receita is None:
        receita, mes_venda = liquido(preco_mes(caminho, meses), meses, c), meses

    receitas = {nome: fn(caminho, c, ma=df["ma_3m"], k_max=meses) for nome, fn in BENCHMARKS.items()}
    receitas["hedge_ate_o_fim"] = liquido_hedge(caminho, fut, 0, meses, c)
    receitas["lstm_dp"] = receita
    receitas["oraculo"] = oraculo(caminho, c, k_max=meses)
    mes_oraculo = int(np.argmax([liquido(preco_mes(caminho, k), k, c) for k in range(meses + 1)]))

    return {
        "safra": f"{ano}/{str(ano + 1)[-2:]}",
        "colheita": caminho.index[0],
        "cego": caminho.index[0] >= pd.Timestamp("2024-07-01"),
        "receitas": pd.Series(receitas, name=f"{ano}/{str(ano + 1)[-2:]}"),
        "mes_venda": mes_venda, "mes_oraculo": mes_oraculo,
        "trilha": pd.DataFrame(trilha).set_index("mes"),
        "caminho": caminho,
    }


def simular_safras(anos: list[int], custos: Custos | None = None, **kw) -> tuple[pd.DataFrame, list[dict]]:
    """Roda várias safras e devolve (tabela de receitas por safra, resultados)."""
    art = load_artifacts()
    res = [simular_safra(a, custos, artefatos=art, **kw) for a in anos]
    tab = pd.DataFrame([r["receitas"] for r in res])
    tab.insert(0, "cego", [r["cego"] for r in res])
    tab.insert(1, "mes_venda_lstm", [r["mes_venda"] for r in res])
    tab.insert(2, "mes_oraculo", [r["mes_oraculo"] for r in res])
    return tab, res


if __name__ == "__main__":
    tab, _ = simular_safras([2022, 2023, 2024, 2025])
    pd.set_option("display.width", 200)
    print(tab.round(0))
