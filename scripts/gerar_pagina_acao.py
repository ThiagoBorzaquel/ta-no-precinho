# =========================
# GERAR PÁGINA POR AÇÃO
# =========================
#
# Requisitos extras (já no projeto): yfinance, pandas, datetime, html
# - Card "Últimos proventos pagos"  -> yfinance Ticker.dividends
# - Card "Últimas notícias"         -> yfinance Ticker.news
#   As notícias são exibidas dentro do próprio site (título, resumo,
#   data e fonte) com um link de referência apontando para a origem.
#
# Tolerante a falhas: se a API não retornar dados, o card mostra
# uma mensagem amigável em vez de quebrar a geração da página.

import html as _html
import datetime as _dt

try:
    import yfinance as yf
except Exception:
    yf = None


# -------------------------
# Helpers de coleta
# -------------------------

def _yf_ticker(ticker):
    """Retorna um yfinance.Ticker já com sufixo .SA (B3)."""
    if yf is None:
        return None
    symbol = ticker if ticker.endswith(".SA") else f"{ticker}.SA"
    try:
        return yf.Ticker(symbol)
    except Exception:
        return None


def obter_proventos(ticker, limite=6):
    """
    Retorna lista dos últimos proventos pagos:
    [{"data": "dd/mm/aaaa", "valor": 1.23}, ...]
    Mais recentes primeiro. Lista vazia se indisponível.
    """
    t = _yf_ticker(ticker)
    if t is None:
        return []
    try:
        serie = t.dividends
        if serie is None or len(serie) == 0:
            return []
        serie = serie.sort_index(ascending=False).head(limite)
        proventos = []
        for data, valor in serie.items():
            try:
                data_fmt = data.strftime("%d/%m/%Y")
            except Exception:
                data_fmt = str(data)[:10]
            proventos.append({
                "data": data_fmt,
                "valor": round(float(valor), 4),
            })
        return proventos
    except Exception:
        return []


def obter_noticias(ticker, limite=5):
    """
    Retorna lista das últimas notícias do ticker:
    [{"titulo","resumo","data","fonte","url"}, ...]
    Lista vazia se indisponível.
    """
    t = _yf_ticker(ticker)
    if t is None:
        return []
    try:
        bruto = t.news or []
    except Exception:
        bruto = []

    noticias = []
    for item in bruto[:limite]:
        # yfinance >=0.2.40 entrega no formato {"id":..., "content": {...}}
        # versões antigas entregam plano. Tratamos os dois.
        c = item.get("content", item) if isinstance(item, dict) else {}
        titulo = (c.get("title") or "").strip()
        if not titulo:
            continue

        resumo = (c.get("summary") or c.get("description") or "").strip()

        # URL — tenta canonicalUrl, depois clickThroughUrl, depois link
        url = ""
        for chave in ("canonicalUrl", "clickThroughUrl"):
            v = c.get(chave)
            if isinstance(v, dict) and v.get("url"):
                url = v["url"]
                break
        if not url:
            url = c.get("link") or item.get("link") or ""

        # Fonte
        fonte = ""
        prov = c.get("provider")
        if isinstance(prov, dict):
            fonte = prov.get("displayName") or ""
        if not fonte:
            fonte = item.get("publisher") or ""

        # Data
        data_fmt = ""
        pub = c.get("pubDate") or c.get("displayTime")
        if pub:
            try:
                data_fmt = _dt.datetime.fromisoformat(
                    pub.replace("Z", "+00:00")
                ).strftime("%d/%m/%Y")
            except Exception:
                data_fmt = str(pub)[:10]
        elif item.get("providerPublishTime"):
            try:
                data_fmt = _dt.datetime.fromtimestamp(
                    item["providerPublishTime"]
                ).strftime("%d/%m/%Y")
            except Exception:
                pass

        noticias.append({
            "titulo": titulo,
            "resumo": resumo,
            "data": data_fmt,
            "fonte": fonte,
            "url": url,
        })
    return noticias


# -------------------------
# Helpers de renderização
# -------------------------

def render_card_proventos(ticker, proventos):
    if not proventos:
        return f"""
<div class="card">
<h2>💰 Últimos proventos pagos por {ticker}</h2>
<p style="color:#94a3b8">Nenhum provento recente foi encontrado para este ativo.</p>
</div>
"""

    linhas = "".join(
        f"""<tr>
  <td style="padding:8px;border-bottom:1px solid #1e293b">{p['data']}</td>
  <td style="padding:8px;border-bottom:1px solid #1e293b;text-align:right;color:#22c55e;font-weight:600">
    R$ {p['valor']:.4f}
  </td>
</tr>"""
        for p in proventos
    )

    return f"""
<div class="card">
<h2>💰 Últimos proventos pagos por {ticker}</h2>
<p style="color:#cbd5e1;font-size:14px">Histórico recente de dividendos e juros sobre capital próprio distribuídos por ação.</p>
<div style="overflow-x:auto">
<table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:14px">
  <thead>
    <tr style="color:#94a3b8;text-align:left">
      <th style="padding:8px;border-bottom:1px solid #334155">Data do pagamento</th>
      <th style="padding:8px;border-bottom:1px solid #334155;text-align:right">Valor por ação</th>
    </tr>
  </thead>
  <tbody>
    {linhas}
  </tbody>
</table>
</div>
<p style="color:#64748b;font-size:12px;margin-top:10px">
Fonte: Yahoo Finance. Os valores podem incluir dividendos, JCP e bonificações.
</p>
</div>
"""


def render_card_noticias(ticker, empresa, noticias):
    if not noticias:
        return f"""
<div class="card">
<h2>📰 Últimas notícias sobre {ticker}</h2>
<p style="color:#94a3b8">Nenhuma notícia recente disponível para {empresa} no momento.</p>
</div>
"""

    itens = []
    for n in noticias:
        titulo = _html.escape(n["titulo"])
        resumo = _html.escape(n["resumo"]) if n["resumo"] else ""
        fonte  = _html.escape(n["fonte"])  if n["fonte"]  else "Fonte externa"
        data   = _html.escape(n["data"])   if n["data"]   else ""
        url    = n["url"]

        meta = " • ".join(x for x in [data, fonte] if x)

        link_fonte = (
            f'<a href="{url}" target="_blank" rel="noopener nofollow" '
            f'style="color:#3b82f6;font-size:13px;text-decoration:none">'
            f'Ler matéria completa na fonte →</a>'
            if url else ""
        )

        itens.append(f"""
<article style="padding:12px 0;border-bottom:1px solid #1e293b">
  <h3 style="margin:0 0 6px 0;font-size:16px;color:#f1f5f9">{titulo}</h3>
  <div style="color:#94a3b8;font-size:12px;margin-bottom:6px">{meta}</div>
  {f'<p style="margin:6px 0;color:#cbd5e1;font-size:14px;line-height:1.5">{resumo}</p>' if resumo else ''}
  {link_fonte}
</article>""")

    return f"""
<div class="card">
<h2>📰 Últimas notícias sobre {ticker}</h2>
<p style="color:#cbd5e1;font-size:14px">Resumo das matérias mais recentes envolvendo {empresa}. Clique em cada notícia para conferir o conteúdo completo na fonte original.</p>
<div>
{''.join(itens)}
</div>
<p style="color:#64748b;font-size:12px;margin-top:10px">
Fonte agregadora: Yahoo Finance. Conteúdo de terceiros — Tá no Precinho não se responsabiliza pelo material publicado pelos veículos originais.
</p>
</div>
"""


# -------------------------
# GERAR PÁGINA POR AÇÃO
# -------------------------

def gerar_pagina_acao(row):
    ticker   = row["Ticker"]
    empresa  = limpar_nome_empresa(row["Empresa"])
    setor    = row["Setor"]
    slug     = gerar_slug(empresa, ticker)
    desconto = round(row["Desconto_%"], 2)
    pl       = round(row["PL"], 2)
    pvp      = round(row["PVP"], 2)
    roe      = round(row["ROE"] * 100, 2)
    dy       = round(row["DivYield"] * 100, 2)
    preco    = round(row["Preco"], 2) if "Preco" in row else "—"
    pjusto   = round(row["PrecoJusto"], 2)

    titulo_pg    = f"{ticker} está barata em 2026? Análise completa — {empresa}"
    descricao_pg = (
        f"Veja agora a análise de {ticker} ({empresa}): P/L {pl}, "
        f"ROE {roe}%, Dividend Yield {dy}% e desconto de {desconto}% "
        f"em relação ao preço justo. Atualizado hoje."
    )
    keywords_pg = (
        f"{ticker}, {empresa}, ação {ticker} está barata, "
        f"análise {ticker}, dividendos {ticker}, vale a pena {ticker} 2026, "
        f"proventos {ticker}, notícias {ticker}"
    )

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
        avaliacao_dy = f"O Dividend Yield de <strong>{dy}%</strong> é elevado, classificando {ticker} como uma pagadora generosa de dividendos."
    elif dy >= 4:
        avaliacao_dy = f"O Dividend Yield de <strong>{dy}%</strong> é moderado. A empresa distribui dividendos de forma consistente."
    else:
        avaliacao_dy = f"O Dividend Yield de <strong>{dy}%</strong> é baixo. O foco da empresa parece ser mais crescimento."

    if pl < 8:
        avaliacao_pl = f"O P/L de <strong>{pl}</strong> é baixo, sugerindo que o mercado paga pouco pelo lucro desta empresa."
    elif pl < 15:
        avaliacao_pl = f"O P/L de <strong>{pl}</strong> está dentro de um patamar razoável para o setor {setor}."
    else:
        avaliacao_pl = f"O P/L de <strong>{pl}</strong> é mais elevado, indicando que o mercado precifica crescimento ou qualidade acima da média."

    # >>> NOVOS BLOCOS: proventos e notícias <<<
    proventos = obter_proventos(ticker, limite=6)
    noticias  = obter_noticias(ticker, limite=5)
    card_proventos = render_card_proventos(ticker, proventos)
    card_noticias  = render_card_noticias(ticker, empresa, noticias)

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
<img src="../logos/{ticker}.png" loading="lazy"
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
<p>O P/VP de <strong>{pvp}</strong> {'indica que a empresa negocia abaixo do valor patrimonial — sinal positivo para value investing.' if pvp < 1 else 'mostra que o mercado precifica a empresa acima do patrimônio líquido.'}</p>
</div>

<div class="card">
<h2>{ticker} paga bons dividendos?</h2>
<p>{avaliacao_dy}</p>
<p>{avaliacao_roe}</p>
</div>

{card_proventos}

{card_noticias}

<div class="card">
<h2>Riscos de investir em {ticker}</h2>
<ul>
<li>Variações macroeconômicas que afetam o setor de <strong>{setor}</strong></li>
<li>{"Alto endividamento relativo ao patrimônio (P/VP " + str(pvp) + "x)" if pvp > 3 else "Nível de alavancagem dentro do esperado para o setor"}</li>
<li>{"Dividend Yield elevado pode indicar distribuição insustentável" if dy > 15 else "Distribuição de dividendos aparentemente sustentável"}</li>
<li>Resultados futuros dependem do desempenho operacional da empresa</li>
</ul>
</div>

<div class="card">
<h2>Conclusão sobre {ticker}</h2>
<p>Com base nos indicadores fundamentalistas atuais, {empresa} ({ticker}) apresenta {'um cenário favorável para investidores de longo prazo.' if desconto > 10 and dy > 4 else 'dados que merecem atenção. Recomendamos aprofundar a análise antes de tomar qualquer decisão.'}</p>
<p>Lembre-se: esta análise é baseada em dados quantitativos e <strong>não constitui recomendação de investimento</strong>.</p>
</div>

</article>

<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<nav aria-label="Paginas tickers" class="menu">
    <a href="../seo/melhores-acoes-para-investir.html">🏆 Melhores ações</a>
    <a href="../seo/acoes-maior-dividend-yield.html">💰 Dividendos</a>
    <a href="../seo/acoes-maior-roe.html">📈 Alta rentabilidade</a>
    <a href="../seo/acoes-mais-seguras.html">🛡 Mais seguras</a>
    <a href="../seo/acoes-dividendos-mensais.html">💵 Renda mensal</a>
    <a href="../seo/acoes-baratas-2026.html">🔥 Ações baratas</a>
    <a href="../seo/melhores-acoes-dividendos.html">💸 Dividendos 2026</a>
    <a href="../seo/comparar.html">↔️ Comparar Ações</a>
    <a href="../investidores.html">📚 Maiores investidores da bolsa</a>

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
