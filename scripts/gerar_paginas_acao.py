from scripts.gerar_metric import gerar_metric
from scripts.gerar_slug import gerar_slug
import datetime
from limpar_nome import limpar_nome_empresa

# =========================
# GERAR PÁGINA POR AÇÃO
# =========================

def gerar_pagina_acao(row):
    """Página principal da ação em /acoes/TICKER.html"""

    ticker = row["Ticker"]
    empresa = limpar_nome_empresa(row["Empresa"])
    setor   = row["Setor"]
    slug    = gerar_slug(empresa, ticker)
    desconto = round(row["Desconto_%"], 2)
    pl       = round(row["PL"], 2)
    pvp      = round(row["PVP"], 2)
    roe      = round(row["ROE"] * 100, 2)
    dy       = round(row["DivYield"] * 100, 2)
    preco    = round(row["Preco"], 2) if "Preco" in row else "—"
    pjusto   = round(row["PrecoJusto"], 2)

    # ---------- Titles e metas dinâmicos (item 12 e 13) ----------
    titulo_pg = f"{ticker} está barata em 2026? Análise completa — {empresa}"
    descricao_pg = (
        f"Veja agora a análise de {ticker} ({empresa}): P/L {pl}, "
        f"ROE {roe}%, Dividend Yield {dy}% e desconto de {desconto}% "
        f"em relação ao preço justo. Atualizado hoje."
    )
    keywords_pg = (
        f"{ticker}, {empresa}, ação {ticker} está barata, "
        f"análise {ticker}, dividendos {ticker}, vale a pena {ticker} 2026"
    )

    # ---------- Interpretações textuais (item 6 — E-E-A-T) ----------
    if desconto > 30:
        avaliacao_desc = f"Com um desconto de <strong>{desconto}%</strong> em relação ao preço justo estimado de R$ {pjusto}, a ação aparenta estar significativamente descontada pelo mercado."
    elif desconto > 0:
        avaliacao_desc = f"Com um desconto de <strong>{desconto}%</strong>, a ação negocia abaixo do preço justo estimado de R$ {pjusto}, podendo representar uma oportunidade para investidores de longo prazo."
    else:
        avaliacao_desc = f"A ação está negociando <strong>acima do preço justo</strong> estimado de R$ {pjusto}. Isso não significa necessariamente que está cara, mas exige maior cautela na análise."

    if roe >= 20:
        avaliacao_roe = f"O ROE de <strong>{roe}%</strong> indica alta eficiência — a empresa gera muito retorno para os acionistas em relação ao capital investido."
    elif roe >= 12:
        avaliacao_roe = f"O ROE de <strong>{roe}%</strong> é razoável e está dentro da média do setor {setor}."
    else:
        avaliacao_roe = f"O ROE de <strong>{roe}%</strong> está abaixo do ideal. Vale analisar se trata-se de um momento pontual ou tendência."

    if dy >= 8:
        avaliacao_dy = f"O Dividend Yield de <strong>{dy}%</strong> é elevado, classificando {ticker} como uma pagadora generosa de dividendos. Boa opção para quem busca renda passiva."
    elif dy >= 4:
        avaliacao_dy = f"O Dividend Yield de <strong>{dy}%</strong> é moderado. A empresa distribui dividendos de forma consistente, sem comprometer reinvestimentos."
    else:
        avaliacao_dy = f"O Dividend Yield de <strong>{dy}%</strong> é baixo. O foco da empresa parece ser mais crescimento do que distribuição de renda."

    if pl < 8:
        avaliacao_pl = f"O P/L de <strong>{pl}</strong> é baixo, sugerindo que o mercado paga pouco pelo lucro desta empresa — potencial sinal de subvalorização."
    elif pl < 15:
        avaliacao_pl = f"O P/L de <strong>{pl}</strong> está dentro de um patamar razoável para o setor {setor}."
    else:
        avaliacao_pl = f"O P/L de <strong>{pl}</strong> é mais elevado, indicando que o mercado precifica crescimento ou qualidade acima da média."

    # ---------- Schema JSON-LD (item 9) ----------
    schema = f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{titulo_pg}",
  "description": "{descricao_pg}",
  "author": {{"@type": "Organization", "name": "Tá no Precinho", "url": "https://tanoprecinho.site"}},
  "publisher": {{"@type": "Organization", "name": "Tá no Precinho", "url": "https://tanoprecinho.site"}},
  "mainEntityOfPage": "https://tanoprecinho.site/acoes/{ticker}.html",
  "dateModified": "{datetime.date.today().isoformat()}"
}}
</script>"""

    with open("docs/layout_base.html", "r", encoding="utf-8") as f:
        template = f.read()
    conteudo = f"""
{schema}

<a href="/index.html" style="color:#94a3b8;font-size:13px;">← Voltar ao ranking</a>

<div style="text-align:center;margin:20px 0">
<img src="../logos/{ticker}.png"
     alt="Logo da empresa {empresa}"
     loading="lazy"
     onerror="this.onerror=null;this.src='../logos/default.svg';"
     style="width:50px;height:50px;margin-bottom:10px">
<h1 style="margin:0">{empresa} ({ticker})</h1>
<div style="color:#cbd5e1;margin-top:5px;font-size:13px">{setor} • Atualizado hoje</div>
</div>

<div style="max-width:520px;margin:auto">
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:15px;">
{gerar_metric("P/L", pl)}
{gerar_metric("P/VP", pvp)}
{gerar_metric("ROE", f"{roe}%")}
{gerar_metric("DY", f"{dy}%")}
{gerar_metric("Score", row["Score"], "#22c55e" if row["Score"] >= 70 else "#eab308")}
{gerar_metric("Desconto", f"{desconto}%", "#22c55e" if desconto > 0 else "#ef4444")}
{gerar_metric("Preço atual", f"R$ {preco}")}
{gerar_metric("Preço justo", f"R$ {pjusto}")}
</div>
</div>

<article style="max-width:700px;margin:20px auto;">

<div class="card">
<h2>Vale a pena investir em {ticker}?</h2>
<p>A <strong>{empresa}</strong> é uma empresa do setor de <strong>{setor}</strong> listada na Bolsa de Valores brasileira (B3) sob o ticker <strong>{ticker}</strong>.</p>
<p>{avaliacao_desc}</p>
<p>{row.get("Resumo", "")}</p>
</div>

<div class="card">
<h2>A ação {ticker} está barata?</h2>
<p>O preço justo estimado com base no P/L conservador de 15x é de <strong>R$ {pjusto}</strong>. {avaliacao_pl}</p>
<p>O P/VP de <strong>{pvp}</strong> {'indica que a empresa negocia abaixo do valor patrimonial — sinal positivo para value investing.' if pvp < 1 else f'mostra que o mercado precifica a empresa acima do patrimônio líquido.'}</p>
</div>

<div class="card">
<h2>{ticker} paga bons dividendos?</h2>
<p>{avaliacao_dy}</p>
<p>{avaliacao_roe}</p>
</div>

<div class="card">
<h2>Riscos de investir em {ticker}</h2>
<p>Todo investimento em ações possui riscos. Para {ticker}, os principais pontos de atenção são:</p>
<ul>
<li>Variações macroeconômicas que afetam o setor de <strong>{setor}</strong></li>
<li>{"Alto endividamento relativo ao patrimônio (P/VP " + str(pvp) + "x)" if pvp > 3 else "Nível de alavancagem dentro do esperado para o setor"}</li>
<li>{"Dividend Yield elevado pode indicar distribuição insustentável — vale verificar o payout" if dy > 15 else "Distribuição de dividendos aparentemente sustentável"}</li>
<li>Resultados futuros dependem do desempenho operacional da empresa</li>
</ul>
</div>

<div class="card">
<h2>Conclusão sobre {ticker}</h2>
<p>Com base nos indicadores fundamentalistas atuais, {empresa} ({ticker}) apresenta {'um cenário favorável para investidores de longo prazo, especialmente pelo desconto em relação ao preço justo e pelo bom retorno em dividendos.' if desconto > 10 and dy > 4 else 'dados que merecem atenção. Recomendamos aprofundar a análise antes de tomar qualquer decisão.'}
</p>
<p>Lembre-se: esta análise é baseada em dados quantitativos e <strong>não constitui recomendação de investimento</strong>. Avalie seu perfil de risco antes de investir.</p>
</div>

</article>

<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Explore rankings prontos com as melhores ações da bolsa hoje.</p>
<nav aria-label="Paginas tickers" class="menu">
    <a href="../seo/melhores-acoes-para-investir.html">🏆 Melhores ações</a>
    <a href="../seo/acoes-maior-dividend-yield.html">💰 Dividendos</a>
    <a href="../seo/acoes-maior-roe.html">📈 Alta rentabilidade</a>
    <a href="../seo/acoes-mais-seguras.html">🛡 Mais seguras</a></li>
    <a href="../seo/acoes-dividendos-mensais.html">💵 Renda mensal</a>
    <a href="../seo/acoes-baratas-2026.html">🔥 Ações baratas</a></li>
    <a href="../seo/melhores-acoes-dividendos.html">💸 Dividendos 2026</a>
</nav>
</div>
"""

    html = template.replace("{{titulo}}", titulo_pg)
    html = html.replace("{{conteudo}}", conteudo)
    html = html.replace("{{descricao}}", descricao_pg)
    html = html.replace("{{keywords}}", keywords_pg)
    html = html.replace("{{url}}", f"https://tanoprecinho.site/acoes/{ticker}.html")

    with open(f"docs/acoes/{ticker}.html", "w", encoding="utf-8") as f:
        f.write(html)

    with open(f"docs/seo/{slug}.html", "w", encoding="utf-8") as f:
        f.write(html)

