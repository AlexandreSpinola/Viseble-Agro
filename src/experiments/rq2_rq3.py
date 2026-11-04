"""Blocos A (RQ3), B (RQ2), C2, D1, D2 e E4 de reports/pedidos-para-experimentos.md.

Uso:  python -m src.experiments.rq2_rq3
Saída: reports/experimentos/*.csv e reports/figures/*.png
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.decision.backtest import ESTRATEGIAS, resumo, rodar_backtest
from src.decision.engine import Custos
from src.decision.hedge import base_stats
from src.models.dataset import HORIZONS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "experimentos"
FIG = ROOT / "reports" / "figures"
TESTE = dict(inicio="2024-07-01")
VALID = dict(inicio="2022-07-01", fim="2023-12-31")


def custos_base(**kw) -> Custos:
    base = dict(armazenagem_saca_mes=2.5, quebra_pct_mes=0.002, coe_saca=700.0,
                taxa_desconto_aa=0.10, aversao_risco=0.0)
    return Custos(**{**base, **kw})


def indicadores(bt: pd.DataFrame, ref: pd.DataFrame | None = None) -> dict:
    d = {
        "lstm_dp": bt["lstm_dp"].mean(), "venda_imediata": bt["venda_imediata"].mean(),
        "venda_parcelada": bt["venda_parcelada"].mean(),
        "freq_armazenar_%": (bt["lstm_dp_acao"] != "VENDER").mean() * 100,
        "freq_hedge_%": (bt["lstm_dp_acao"] == "ARMAZENAR+HEDGE").mean() * 100,
    }
    if ref is not None:
        d["datas_acao_muda"] = int((bt["lstm_dp_acao"] != ref["lstm_dp_acao"]).sum())
    return d


def bloco_a(base: pd.DataFrame) -> None:
    # A1 Selic
    linhas = []
    bt_vig = rodar_backtest(custos_base(), selic_vigente=True, **TESTE)
    bt_vig[["selic_usada_%"]].to_csv(OUT / "a1_selic_vigente_por_data.csv")
    linhas.append({"selic_%": "vigente (por data)", **indicadores(bt_vig, base)})
    for s in [8, 10, 12, 13.25, 15]:
        bt = rodar_backtest(custos_base(taxa_desconto_aa=s / 100), **TESTE)
        linhas.append({"selic_%": s, **indicadores(bt, base)})
    pd.DataFrame(linhas).round(2).to_csv(OUT / "a1_selic.csv", index=False)
    print("A1 ok", flush=True)

    # A2 choque de base
    st = base_stats()
    linhas = [{"cenario": "base", **indicadores(base)}]
    for dpp in [-0.05, 0.05]:
        s2 = {**st, "base_pct_por_mes": {m: v + dpp for m, v in st["base_pct_por_mes"].items()}}
        bt = rodar_backtest(custos_base(), stats=s2, **TESTE)
        linhas.append({"cenario": f"base {dpp:+.0%} pp", **indicadores(bt, base)})
    s2 = {**st, "risco_base_pct_por_h": {h: 2 * v for h, v in st["risco_base_pct_por_h"].items()}}
    bt = rodar_backtest(custos_base(), stats=s2, **TESTE)
    linhas.append({"cenario": "risco de base ×2", **indicadores(bt, base)})
    # com aversão a risco, onde o risco de base pesa
    for lam in [0.25, 0.5]:
        bt = rodar_backtest(custos_base(aversao_risco=lam), **TESTE)
        linhas.append({"cenario": f"λ={lam} base", **indicadores(bt, base)})
        bt = rodar_backtest(custos_base(aversao_risco=lam), stats=s2, **TESTE)
        linhas.append({"cenario": f"λ={lam} risco ×2", **indicadores(bt, base)})
    pd.DataFrame(linhas).round(2).to_csv(OUT / "a2_choque_base.csv", index=False)
    print("A2 ok", flush=True)

    # A3 COE no benchmark de meta de margem (e no motor via D1)
    linhas = []
    for coe in [500, 700, 900, 1100]:
        bt = rodar_backtest(custos_base(coe_saca=coe), **TESTE)
        linhas.append({"coe": coe, "meta_margem_coe": bt["meta_margem_coe"].mean(),
                       "datas_meta_difere_imediata": int((bt["meta_margem_coe"] - bt["venda_imediata"]).abs().gt(1e-6).sum()),
                       "lstm_dp": bt["lstm_dp"].mean()})
    pd.DataFrame(linhas).round(2).to_csv(OUT / "a3_coe.csv", index=False)
    print("A3 ok", flush=True)

    # A4 grade λ × armazenagem
    linhas = []
    for lam in [0.0, 0.25, 0.5, 1.0]:
        for arm in [1.5, 2.5, 5.0]:
            bt = rodar_backtest(custos_base(aversao_risco=lam, armazenagem_saca_mes=arm), **TESTE)
            r = resumo(bt).loc["lstm_dp"]
            linhas.append({"lambda": lam, "armazenagem": arm, **r.to_dict(), **{k: v for k, v in indicadores(bt).items() if k.startswith("freq")}})
    pd.DataFrame(linhas).round(2).to_csv(OUT / "a4_grade_lambda_armazenagem.csv", index=False)
    print("A4 ok", flush=True)


def bloco_b(base: pd.DataFrame) -> pd.DataFrame:
    # B1 validação
    bt_val = rodar_backtest(custos_base(), **VALID)
    bt_val.to_csv(OUT / "b1_backtest_validacao.csv")
    todos = pd.concat([bt_val.assign(periodo="validação"), base.assign(periodo="teste")])
    todos["safra"] = todos.index.year.where(todos.index.month >= 7, todos.index.year - 1)
    est = [e for e in ESTRATEGIAS if e in todos]
    por_safra = todos.groupby("safra")[est].mean()
    por_safra["n_datas"] = todos.groupby("safra").size()
    por_safra.round(1).to_csv(OUT / "b1_por_safra.csv")
    resumo(bt_val).to_csv(OUT / "b1_resumo_validacao.csv")
    resumo(todos).to_csv(OUT / "b1_resumo_4_safras.csv")
    todos.to_csv(OUT / "b1_backtest_todos.csv")
    print("B1 ok", flush=True)

    # B2 estatística pareada
    rng = np.random.default_rng(42)
    linhas = []
    for nome, bt in [("teste", base), ("teste+validação", todos)]:
        for alvo in ["venda_imediata", "venda_parcelada"]:
            d = (bt["lstm_dp"] - bt[alvo]).to_numpy()
            boot = np.array([rng.choice(d, len(d), replace=True).mean() for _ in range(10_000)])
            try:
                from scipy.stats import wilcoxon
                p = float(wilcoxon(d, zero_method="zsplit").pvalue) if np.any(d != 0) else 1.0
            except Exception:
                p = np.nan
            linhas.append({"amostra": nome, "n": len(d), "comparacao": f"lstm_dp − {alvo}",
                           "media": d.mean(), "desvio": d.std(ddof=1),
                           "ic95_inf": np.percentile(boot, 2.5), "ic95_sup": np.percentile(boot, 97.5),
                           "p_wilcoxon": p, "fracao_datas_positivas_%": (d > 0).mean() * 100})
    pd.DataFrame(linhas).round(3).to_csv(OUT / "b2_estatistica_pareada.csv", index=False)
    # captura do oráculo por data e média
    cap = {}
    for nome, bt in [("teste", base), ("teste+validação", todos)]:
        g = bt[est].sub(bt["venda_imediata"], axis=0).div(bt["oraculo"] - bt["venda_imediata"] + 1e-9, axis=0)
        g = g.where((bt["oraculo"] - bt["venda_imediata"]) > 1e-6)   # só datas em que havia ganho possível
        cap[nome] = (g.mean() * 100).round(1)
        g.mul(100).round(1).to_csv(OUT / f"b2_captura_por_data_{nome.replace('+', '_')}.csv")
    pd.DataFrame(cap).to_csv(OUT / "b2_captura_oraculo_media.csv")
    print("B2 ok", flush=True)

    # B3 decomposição
    cols = ["preco_inicial", "lstm_dp_acao", "lstm_dp_mes_venda", "lstm_dp", "venda_imediata", "oraculo",
            *[f"y_{h}d" for h in HORIZONS], *[f"ret_real_{h}d" for h in HORIZONS]]
    b3 = todos[["periodo", *cols]].copy()
    b3["ganho_vs_imediata_%"] = (b3["lstm_dp"] / b3["venda_imediata"] - 1) * 100
    for h in HORIZONS:
        b3[f"direcao_ok_{h}d"] = np.sign(b3[f"y_{h}d"]) == np.sign(b3[f"ret_real_{h}d"])
    b3.round(4).to_csv(OUT / "b3_decomposicao.csv")
    print("B3 ok", flush=True)
    return todos


def bloco_c2() -> None:
    from src.models.dataset import prepare_splits
    from src.models.lstm import evaluate
    from src.models.predict import load_artifacts
    model, _, _ = load_artifacts()
    d = prepare_splits()
    tabs = []
    for split in ["val", "test"]:
        m = evaluate(model, d[split], d["df"]); m.insert(0, "split", split); tabs.append(m)
    pd.concat(tabs).round(4).to_csv(OUT / "c2_metricas_val_teste.csv")
    print("C2 ok", flush=True)


def bloco_d1(base: pd.DataFrame) -> None:
    linhas = [{"margem_min": "desligada", **indicadores(base)}]
    for m in [0.0, 0.10, 0.30]:
        for coe in [700, 1100]:
            bt = rodar_backtest(custos_base(coe_saca=coe, margem_min_coe=m), **TESTE)
            linhas.append({"margem_min": m, "coe": coe, **indicadores(bt, base)})
    pd.DataFrame(linhas).round(2).to_csv(OUT / "d1_restricao_coe.csv", index=False)
    print("D1 ok", flush=True)


def coe_conab_guaxupe() -> dict:
    """COE (custo variável) da CONAB para Guaxupé, MG, por ano de colheita (D2)."""
    cn = pd.read_csv(ROOT / "data" / "external" / "conab_coe_cot_cafe_arabica_mg.csv")
    g = cn[(cn.municipio == "Guaxupé") & cn.COE_custo_variavel_rs_sc.notna()].copy()
    g = g[g.variante.isna()] if g.variante.isna().any() else g      # prefere a planilha sem variante
    return {int(a): float(v) for a, v in zip(g.ano, g.COE_custo_variavel_rs_sc)}


def bloco_d2(base: pd.DataFrame) -> None:
    """D2: backtest com o COE real da CONAB por safra (Guaxupé), teste e validação."""
    coe = coe_conab_guaxupe()
    coe_bt = {s: coe[s] for s in [2022, 2023, 2024, 2025]}
    bt_t = rodar_backtest(custos_base(), coe_por_safra=coe_bt, **TESTE)
    bt_t.to_csv(OUT / "d2_backtest_teste_coe_conab.csv")
    bt_v = rodar_backtest(custos_base(), coe_por_safra=coe_bt, **VALID)
    bt_v.to_csv(OUT / "d2_backtest_validacao_coe_conab.csv")
    linhas = []
    for m in ["desligada", 0.0, 0.10, 0.30]:
        bt = bt_t if m == "desligada" else rodar_backtest(custos_base(margem_min_coe=m), coe_por_safra=coe_bt, **TESTE)
        linhas.append({"margem_min": m, **indicadores(bt, base),
                       "meta_margem_coe": bt["meta_margem_coe"].mean(),
                       "datas_meta_difere_imediata": int((bt["meta_margem_coe"] - bt["venda_imediata"]).abs().gt(1e-6).sum()),
                       "margem_sobre_coe_min_%": float((bt["preco_inicial"] / bt["coe_usado"] - 1).min() * 100)})
    pd.DataFrame(linhas).round(2).to_csv(OUT / "d2_coe_conab.csv", index=False)
    print("D2 ok", flush=True)


def bloco_e4() -> None:
    from src.models.predict import forecast, load_artifacts, residual_sigma
    from src.decision.engine import recomendar
    model, scaler, df = load_artifacts()
    data = df.index[-1]
    yhat = forecast(data, df, model, scaler); sigma = residual_sigma()
    t = time.perf_counter()
    for _ in range(20):
        recomendar(float(df["cepea_arabica_brl_sc"].iloc[-1]), yhat, sigma, custos_base(), k_max=6)
    t_motor = (time.perf_counter() - t) / 20
    t = time.perf_counter(); rodar_backtest(custos_base(), **TESTE); t_bt = time.perf_counter() - t
    pd.DataFrame([{"motor_1_data_s": round(t_motor, 3), "backtest_20_datas_s": round(t_bt, 1),
                   "treino_lstm_s": "ver reports/experimentos/c5_seeds.csv (tempo_s por seed)"}]).to_csv(OUT / "e4_tempos.csv", index=False)
    print("E4 ok", flush=True)


def figuras(base: pd.DataFrame, todos: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 300, "savefig.facecolor": "white", "font.size": 9})
    from src.models.predict import load_artifacts
    _, _, df = load_artifacts()
    P = df["cepea_arabica_brl_sc"]

    # E6.1 série com cortes
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(P.index, P.values, color="#6E3F26", lw=0.8)
    for a, b, cor, nome in [("2005-12-07", "2022-06-30", "#dfe8d6", "treino"), ("2022-07-01", "2024-06-30", "#f3e6c8", "validação"), ("2024-07-01", "2026-08-31", "#f0d3c6", "teste")]:
        ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color=cor, alpha=0.6, label=nome)
    ax.set_ylabel("R$/saca"); ax.set_title("Indicador CEPEA/ESALQ café arábica (R$/saca de 60 kg) e partição temporal"); ax.legend(loc="upper left")
    fig.tight_layout(); fig.savefig(FIG / "01_serie_cepea_particao.png"); plt.close(fig)

    # E6.7 receita por data, safras separadas
    est = ["venda_imediata", "venda_parcelada", "media_movel_3m", "hedge_ate_o_fim", "lstm_dp", "oraculo"]
    rot = {"venda_imediata": "venda imediata", "venda_parcelada": "venda parcelada", "media_movel_3m": "média móvel 3 m",
           "hedge_ate_o_fim": "hedge 6 m", "lstm_dp": "Agro Visible", "oraculo": "oráculo"}
    fig, ax = plt.subplots(figsize=(11, 4.2))
    for e in est:
        ax.plot(base.index, base[e], marker="o", ms=3, lw=1.2 if e == "lstm_dp" else 0.9, label=rot[e], color="#6E3F26" if e == "lstm_dp" else None)
    ax.axvline(pd.Timestamp("2025-07-01"), color="gray", ls="--", lw=0.8); ax.text(pd.Timestamp("2025-07-05"), ax.get_ylim()[1] * 0.98, "safra 2025/26", va="top", fontsize=8, color="gray")
    ax.set_ylabel("receita líquida (R$/saca, VP)"); ax.set_title("Receita líquida por data de decisão no teste cego, todas as estratégias"); ax.legend(ncol=3, fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "07_receita_por_data_teste.png"); plt.close(fig)

    # E6.8 base %
    st = base_stats()
    b = df["base_fisico_futuro_pct"].loc["2015":] * 100
    saz = pd.Series([st["base_pct_por_mes"][m] * 100 for m in b.index.month], index=b.index)
    fig, ax = plt.subplots(figsize=(11, 3.8))
    ax.plot(b.index, b.values, color="#6E3F26", lw=0.7, label="base observada")
    ax.plot(saz.index, saz.values, color="#4F6B3B", lw=1.2, label="média sazonal (treino)")
    ax.axvline(pd.Timestamp("2022-07-01"), color="gray", ls="--", lw=0.8)
    ax.set_ylabel("% do futuro"); ax.set_title("Base física × futuro (CEPEA − ICE em R$/saca), em % do futuro"); ax.legend()
    fig.tight_layout(); fig.savefig(FIG / "08_base_fisico_futuro_pct.png"); plt.close(fig)

    # E6.9 mapas de calor
    a4 = pd.read_csv(OUT / "a4_grade_lambda_armazenagem.csv")
    piv = a4.pivot(index="lambda", columns="armazenagem", values="receita_media_R$/sc")
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    im = axes[0].imshow(piv.values, cmap="YlOrBr", aspect="auto")
    axes[0].set_xticks(range(len(piv.columns))); axes[0].set_xticklabels(piv.columns); axes[0].set_yticks(range(len(piv.index))); axes[0].set_yticklabels(piv.index)
    axes[0].set_xlabel("armazenagem (R$/saca/mês)"); axes[0].set_ylabel("aversão a risco λ"); axes[0].set_title("Receita média do Agro Visible (R$/saca)")
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            axes[0].text(j, i, f"{piv.values[i, j]:.0f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=axes[0])
    a1 = pd.read_csv(OUT / "a1_selic.csv"); a2 = pd.read_csv(OUT / "a2_choque_base.csv")
    a1n = a1[a1["selic_%"] != "vigente (por data)"].copy(); a1n["selic_%"] = a1n["selic_%"].astype(float)
    axes[1].plot(a1n["selic_%"], a1n["lstm_dp"], "o-", color="#6E3F26", label="Agro Visible")
    axes[1].plot(a1n["selic_%"], a1n["venda_imediata"], "s--", color="gray", label="venda imediata")
    axes[1].set_xlabel("taxa de desconto (% a.a.)"); axes[1].set_ylabel("R$/saca"); axes[1].set_title("Sensibilidade à Selic"); axes[1].legend()
    fig.tight_layout(); fig.savefig(FIG / "09_sensibilidade_lambda_armazenagem_selic.png"); plt.close(fig)

    # E6.4/5/6 cone, árvore, gatilhos para a última data
    from src.models.predict import forecast, residual_sigma
    from src.decision.engine import recomendar, grafo_decisoes, K_MAX, _trajetoria
    from src.decision.hedge import futuro_por_mes, base_por_mes, risco_base_pct
    from src.models.predict import load_artifacts as la
    model, scaler, _ = la()
    data = df.index[-1]; p0 = float(P.loc[data]); yhat = forecast(data, df, model, scaler); sigma = residual_sigma()
    F = futuro_por_mes(data, float(df["ptax_venda"].loc[data]), float(df["ice_arabica_brl_sc"].loc[data]), K_MAX)
    bexp = base_por_mes(data, K_MAX, stats=st); rb = np.array([risco_base_pct(j * 21, st) for j in range(K_MAX + 1)])
    rec = recomendar(p0, yhat, sigma, custos_base(), futuros=F, base_pct=bexp, risco_base_pct=rb)
    mu, sd = _trajetoria(yhat, sigma, K_MAX); meses = np.arange(K_MAX + 1)
    from scipy.stats import norm
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.fill_between(meses, p0 * np.exp(mu + norm.ppf(0.1) * sd), p0 * np.exp(mu + norm.ppf(0.9) * sd), color="#c9d6bd", alpha=0.7, label="quantis 10–90 %")
    ax.plot(meses, p0 * np.exp(mu), "o-", color="#4F6B3B", label="mediana (LSTM)")
    ax.set_xlabel("meses após a decisão"); ax.set_ylabel("R$/saca"); ax.set_title(f"Cone de preços do motor em {data.date()}"); ax.legend()
    fig.tight_layout(); fig.savefig(FIG / "04_cone_precos.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(meses, rec.gatilhos, "s-", color="#9A5B12", label="gatilho de venda")
    ax.plot(meses, p0 * np.exp(mu), "o--", color="#4F6B3B", label="preço previsto")
    ax.axhline(p0, color="gray", lw=0.8, ls=":", label="preço hoje")
    ax.set_xlabel("mês"); ax.set_ylabel("R$/saca"); ax.set_title(f"Gatilho de venda por mês em {data.date()} (nan = nunca vender no mês)"); ax.legend()
    fig.tight_layout(); fig.savefig(FIG / "06_gatilho_venda_por_mes.png"); plt.close(fig)

    import networkx as nx
    G = grafo_decisoes(rec, yhat, sigma)
    pos = {n: (d["mes"], d["preco"]) for n, d in G.nodes(data=True)}
    cor = {"VENDER": "#b03a2e", "ARMAZENAR": "#4F6B3B", "ARMAZENAR+HEDGE": "#2e6f9e"}
    fig, ax = plt.subplots(figsize=(9, 4.5))
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.25, arrows=False)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=[cor[d["acao"]] for _, d in G.nodes(data=True)], node_size=320)
    nx.draw_networkx_labels(G, pos, {n: f"{d['preco']:.0f}" for n, d in G.nodes(data=True)}, font_size=6, font_color="white", ax=ax)
    for k, v in cor.items():
        ax.scatter([], [], color=v, label=k.lower())
    ax.set_axis_on(); ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)
    ax.set_xlabel("mês"); ax.set_ylabel("R$/saca"); ax.set_title(f"Árvore reduzida de cenários com ação ótima, {data.date()}"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "05_arvore_decisoes.png"); plt.close(fig)
    print("figuras ok", flush=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    base = rodar_backtest(custos_base(), **TESTE)
    base.to_csv(OUT / "backtest_teste_base.csv")
    print("base ok", flush=True)
    bloco_a(base)
    todos = bloco_b(base)
    bloco_c2()
    bloco_d1(base)
    bloco_d2(base)
    bloco_e4()
    figuras(base, todos)
    print("concluído", flush=True)
