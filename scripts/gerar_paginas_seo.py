from scripts.gerar_metric import gerar_metric
from scripts.gerar_slug import gerar_slug
import datetime

def gerar_paginas_seo_ticker(row):
    """3 páginas SEO diferenciadas por foco (item 2 — sem conteúdo duplicado)"""

    ticker  = row["Ticker"]
    empresa = limpar_nome_empresa(row["Empresa"])
    setor   = row["Setor"]
    slug    = gerar_slug(empresa, ticker)
    desconto = round(row["Desconto_%"], 2)
    pl       = round(row["PL"], 2)
    pvp      = round(row["PVP"], 2)
    roe      = round(row["ROE"] * 100, 2)
    dy       = round(row["DivYield"] * 100, 2)
    pjusto   = round(row["PrecoJusto"], 2)

    with open("docs/layout_base.html", "r", encoding="utf-8") as f:
        template = f.read()
    
 # -------------------------------------------------------
    # PÁGINA 1: vale-a-pena — foco em visão geral (item 2)
    # -------------------------------------------------------
    nome1   = f"vale-a-pena-{slug}"
    titulo1 = f"Vale a pena investir em {empresa} ({ticker}) em 2026?"
    desc1   = f"Análise completa de {ticker}: indicadores, setor, riscos e oportunidade. Atualizado hoje."
    schema1 = f"""<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article","headline":"{titulo1}",
"author":{{"@type":"Organization","name":"Tá no Precinho"}},
"dateModified":"{datetime.date.today().isoformat()}"}}
</script>"""

    conteudo1 = f"""
{schema1}
<div style="max-width:780px;margin:auto">

<a href="/index.html" style="color:#94a3b8;font-size:13px;">← Ranking completo</a>

<div class="card" style="text-align:center;margin:16px 0">
<img src="../logos/{ticker}.png" alt="Logo {empresa}" loading="lazy"
     onerror="this.onerror=null;this.src='../logos/default.svg';"
     style="width:44px;height:44px;margin-bottom:8px">
<h1 style="margin:0;font-size:21px">{titulo1}</h1>
<p style="color:#22c55e;font-size:13px;margin:6px 0">Atualizado hoje • {setor}</p>
</div>

<div class="card">
<h2>Visão geral de {ticker}</h2>
<p><strong>{empresa}</strong> atua no setor de <strong>{setor}</strong>. Com P/L de {pl} e ROE de {roe}%, a empresa {'apresenta fundamentos atrativos para o investidor de longo prazo.' if roe >= 15 and pl < 15 else 'requer análise cuidadosa antes de qualquer decisão.'}</p>
<p>O score fundamentalista atual é de <strong>{row["Score"]}/100</strong>, {'indicando boa qualidade nos indicadores analisados.' if row["Score"] >= 70 else 'com pontos que merecem atenção.'}</p>
</div>

<div class="card" style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);">
<h2>Principais indicadores</h2>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;">
{gerar_metric("P/L", pl)}
{gerar_metric("P/VP", pvp)}
{gerar_metric("ROE", f"{roe}%")}
{gerar_metric("DY", f"{dy}%")}
{gerar_metric("Score", row["Score"])}
{gerar_metric("Desconto", f"{desconto}%")}
</div>
</div>

<div class="card">
<h2>Riscos e oportunidades</h2>
<p>{"Com desconto de " + str(desconto) + "% em relação ao preço justo, existe potencial de valorização para quem tem horizonte de longo prazo." if desconto > 10 else "A ação negocia próxima ou acima do preço justo estimado, o que reduz a margem de segurança."}</p>
<p>{"O alto Dividend Yield de " + str(dy) + "% é um ponto positivo para quem busca renda passiva." if dy >= 6 else "Os dividendos são modestos, sendo mais adequada para investidores focados em crescimento."}</p>
<p><strong>Atenção:</strong> esta análise é informativa e não constitui recomendação de investimento.</p>
</div>

<div class="card">
<h3>🔗 Aprofunde a análise</h3>
<ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:8px;">
  <li><a href="/acoes/{ticker}.html">📊 Análise completa de {ticker}</a></li>
  <li><a href="/seo/{slug}-ta-barato.html">💸 {ticker} está barata? Análise de valuation</a></li>
  <li><a href="/seo/{slug}-paga-dividendos.html">💰 {ticker} paga bons dividendos?</a></li>
  <li><a href="/index.html">← Ver ranking completo</a></li>
</ul>
</div>

</div>"""

    html1 = template.replace("{{titulo}}", titulo1).replace("{{conteudo}}", conteudo1) \
                    .replace("{{descricao}}", desc1).replace("{{keywords}}", f"{ticker}, vale a pena {ticker}, {empresa} 2026") \
                    .replace("{{url}}", f"https://tanoprecinho.site/seo/{nome1}.html")
    with open(f"docs/seo/{nome1}.html", "w", encoding="utf-8") as f:
        f.write(html1)

    # -------------------------------------------------------
    # PÁGINA 2: ta-barato — foco em valuation P/L e preço justo (item 2)
    # -------------------------------------------------------
    nome2   = f"{slug}-ta-barato"
    titulo2 = f"{empresa} ({ticker}) está barata? Análise de valuation 2026"
    desc2   = f"Veja se {ticker} está barata: P/L {pl}, P/VP {pvp} e preço justo estimado em R$ {pjusto}. Análise atualizada hoje."
    schema2 = f"""<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article","headline":"{titulo2}",
"author":{{"@type":"Organization","name":"Tá no Precinho"}},
"dateModified":"{datetime.date.today().isoformat()}"}}
</script>"""

    if pl < 8:
        conclusao_pl = f"Um P/L de {pl} é considerado baixo — o mercado está pagando menos de 8 anos de lucro pela empresa, o que historicamente sugere subvalorização."
    elif pl < 15:
        conclusao_pl = f"Um P/L de {pl} é razoável para o setor de {setor}. Não está excessivamente caro nem barato."
    else:
        conclusao_pl = f"Um P/L de {pl} está acima do múltiplo conservador de 15x. Isso pode indicar que o mercado precifica crescimento futuro."

    conteudo2 = f"""
{schema2}
<div style="max-width:780px;margin:auto">

<a href="/index.html" style="color:#94a3b8;font-size:13px;">← Ranking completo</a>

<div class="card" style="text-align:center;margin:16px 0">
<img src="../logos/{ticker}.png" alt="Logo {empresa}" loading="lazy"
     onerror="this.onerror=null;this.src='../logos/default.svg';"
     style="width:44px;height:44px;margin-bottom:8px">
<h1 style="margin:0;font-size:21px">{titulo2}</h1>
<p style="color:#22c55e;font-size:13px;margin:6px 0">Análise de valuation • Atualizado hoje</p>
</div>

<div class="card">
<h2>Preço justo de {ticker}</h2>
<p>Utilizando o método do P/L justo com múltiplo conservador de <strong>15x</strong>, o preço justo estimado para {ticker} é de <strong>R$ {pjusto}</strong>.</p>
<p>{"Com o desconto atual de " + str(desconto) + "%, a ação negocia abaixo do valor estimado — o que pode representar uma oportunidade." if desconto > 0 else "A ação está sendo negociada acima do preço justo estimado, com ágio de " + str(abs(desconto)) + "%."}</p>
</div>

<div class="card" style="background:rgba(59,130,246,0.06);border:1px solid rgba(59,130,246,0.2);">
<h2>Indicadores de valuation</h2>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;">
{gerar_metric("P/L", pl)}
{gerar_metric("P/VP", pvp)}
{gerar_metric("Preço justo", f"R$ {pjusto}")}
{gerar_metric("Desconto", f"{desconto}%")}
</div>
</div>

<div class="card">
<h2>O que o P/L diz sobre {ticker}?</h2>
<p>{conclusao_pl}</p>
<p>O P/VP de <strong>{pvp}</strong> {'indica que a ação negocia abaixo do valor patrimonial — característica típica de ações de valor.' if pvp < 1 else 'mostra que o mercado paga ' + str(pvp) + 'x o patrimônio líquido da empresa.'}</p>
</div>

<div class="card">
<h2>Conclusão de valuation</h2>
<p>{"Os indicadores sugerem que " + ticker + " pode estar subvalorizada pelo mercado. Para investidores de value investing, esse desconto pode representar uma entrada interessante." if desconto > 15 else "O valuation atual de " + ticker + " está dentro de um patamar moderado. Não há margem de segurança expressiva pelo critério do P/L justo."}</p>
<p>⚠️ Esta análise é exclusivamente informativa e <strong>não constitui recomendação de investimento</strong>.</p>
</div>

<div class="card">
<h3>🔗 Continue analisando</h3>
<ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:8px;">
  <li><a href="/acoes/{ticker}.html">📊 Análise completa de {ticker}</a></li>
  <li><a href="/seo/vale-a-pena-{slug}.html">🤔 Vale a pena investir em {empresa}?</a></li>
  <li><a href="/seo/{slug}-paga-dividendos.html">💰 {ticker} paga bons dividendos?</a></li>
  <li><a href="/index.html">← Ver ranking completo</a></li>
</ul>
</div>

</div>"""

    html2 = template.replace("{{titulo}}", titulo2).replace("{{conteudo}}", conteudo2) \
                    .replace("{{descricao}}", desc2).replace("{{keywords}}", f"{ticker} está barata, valuation {ticker}, preço justo {ticker}") \
                    .replace("{{url}}", f"https://tanoprecinho.site/seo/{nome2}.html")
    with open(f"docs/seo/{nome2}.html", "w", encoding="utf-8") as f:
        f.write(html2)

    # -------------------------------------------------------
    # PÁGINA 3: paga-dividendos — foco em renda (item 2)
    # -------------------------------------------------------
    nome3   = f"{slug}-paga-dividendos"
    titulo3 = f"{empresa} ({ticker}) paga bons dividendos em 2026?"
    desc3   = f"{ticker} tem Dividend Yield de {dy}% e ROE de {roe}%. Veja se os dividendos são sustentáveis. Análise atualizada hoje."
    schema3 = f"""<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article","headline":"{titulo3}",
"author":{{"@type":"Organization","name":"Tá no Precinho"}},
"dateModified":"{datetime.date.today().isoformat()}"}}
</script>"""

    if dy >= 10:
        analise_dy = f"O Dividend Yield de <strong>{dy}%</strong> é muito elevado. {ticker} é uma das melhores pagadoras de dividendos do mercado, mas vale verificar se o payout é sustentável a longo prazo."
    elif dy >= 6:
        analise_dy = f"O Dividend Yield de <strong>{dy}%</strong> é alto e bem acima da poupança. {ticker} pode ser uma boa opção para quem busca renda passiva consistente."
    elif dy >= 3:
        analise_dy = f"O Dividend Yield de <strong>{dy}%</strong> é moderado. A empresa distribui dividendos sem comprometer o caixa para reinvestimento."
    else:
        analise_dy = f"O Dividend Yield de <strong>{dy}%</strong> é baixo. O foco da empresa parece ser crescimento — os dividendos são secundários."

    conteudo3 = f"""
{schema3}
<div style="max-width:780px;margin:auto">

<a href="/index.html" style="color:#94a3b8;font-size:13px;">← Ranking completo</a>

<div class="card" style="text-align:center;margin:16px 0">
<img src="../logos/{ticker}.png" alt="Logo {empresa}" loading="lazy"
     onerror="this.onerror=null;this.src='../logos/default.svg';"
     style="width:44px;height:44px;margin-bottom:8px">
<h1 style="margin:0;font-size:21px">{titulo3}</h1>
<p style="color:#22c55e;font-size:13px;margin:6px 0">Análise de dividendos • Atualizado hoje</p>
</div>

<div class="card">
<h2>Dividend Yield de {ticker}</h2>
<p>{analise_dy}</p>
<p>Com ROE de <strong>{roe}%</strong>, {'a empresa demonstra eficiência na geração de lucro, o que é um bom sinal para a sustentabilidade dos dividendos.' if roe >= 15 else 'o retorno sobre patrimônio é moderado — acompanhe os resultados trimestrais para avaliar continuidade.'}</p>
</div>

<div class="card" style="background:rgba(34,197,94,0.06);border:1px solid rgba(34,197,94,0.2);">
<h2>Indicadores de renda</h2>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;">
{gerar_metric("Dividend Yield", f"{dy}%")}
{gerar_metric("ROE", f"{roe}%")}
{gerar_metric("P/L", pl)}
{gerar_metric("Score", row["Score"])}
</div>
</div>

<div class="card">
<h2>Os dividendos de {ticker} são sustentáveis?</h2>
<p>Para avaliar a sustentabilidade dos dividendos, observamos a relação entre o Dividend Yield e o ROE. {"Com ROE de " + str(roe) + "% e DY de " + str(dy) + "%, a empresa demonstra capacidade de gerar lucro suficiente para manter os pagamentos." if roe > dy else "O DY está próximo ou acima do ROE, o que pode indicar distribuição elevada em relação à rentabilidade — monitorar resultados futuros."}</p>
<p>Empresas do setor de <strong>{setor}</strong> costumam {'ter política de dividendos mais previsível.' if setor in ['Utilidades Públicas', 'Serviços Financeiros', 'Energia'] else 'variar os dividendos conforme ciclos de negócio.'}</p>
</div>

<div class="card">
<h2>Conclusão sobre os dividendos de {ticker}</h2>
<p>{"Com DY de " + str(dy) + "%, " + ticker + " é uma opção relevante para investidores que buscam renda passiva na bolsa brasileira." if dy >= 5 else ticker + " não se destaca como pagadora de dividendos. Para estratégia de renda, existem opções mais adequadas no ranking."}</p>
<p>⚠️ Análise informativa. <strong>Não constitui recomendação de investimento.</strong></p>
</div>

<div class="card">
<h3>🔗 Veja também</h3>
<ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:8px;">
  <li><a href="/acoes/{ticker}.html">📊 Análise completa de {ticker}</a></li>
  <li><a href="/seo/vale-a-pena-{slug}.html">🤔 Vale a pena investir em {empresa}?</a></li>
  <li><a href="/seo/{slug}-ta-barato.html">💸 {ticker} está barata? Valuation</a></li>
  <li><a href="/seo/acoes-maior-dividend-yield.html">💰 Ver todas as ações com alto DY</a></li>
  <li><a href="/index.html">← Ranking completo</a></li>
</ul>
</div>

</div>"""

    html3 = template.replace("{{titulo}}", titulo3).replace("{{conteudo}}", conteudo3) \
                    .replace("{{descricao}}", desc3).replace("{{keywords}}", f"{ticker} dividendos, dividend yield {ticker}, {empresa} paga dividendos") \
                    .replace("{{url}}", f"https://tanoprecinho.site/seo/{nome3}.html")
    with open(f"docs/seo/{nome3}.html", "w", encoding="utf-8") as f:
        f.write(html3)