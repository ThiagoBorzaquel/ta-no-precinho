# =========================
# GERAR páginas automáticas
# =========================

def gerar_pagina(nome, titulo, conteudo, descricao="", keywords=""):

    with open("docs/layout_base.html", "r", encoding="utf-8") as f:
        template = f.read()

    url = f"https://tanoprecinho.site/{nome}.html"

    html = template.replace("{{titulo}}", titulo)
    html = html.replace("{{conteudo}}", conteudo)
    html = html.replace("{{descricao}}", descricao)
    html = html.replace("{{keywords}}", keywords)
    html = html.replace("{{url}}", url)

    with open(f"docs/{nome}.html", "w", encoding="utf-8") as f:
        f.write(html)


# =========================
# CRIAR AS PÁGINAS
# =========================

gerar_pagina(
    "privacidade",
    "Política de Privacidade",
    """
<p>Este site coleta informações de navegação para melhorar a experiência do usuário.</p>
<p>Utilizamos serviços como Google Analytics e Google AdSense que podem utilizar cookies.</p>
<p>Nenhuma informação pessoal sensível é armazenada.</p>
"""
)

gerar_pagina(
    "termos",
    "Termos de Uso",
    """
<p>As informações apresentadas possuem caráter educacional.</p>
<p>Não constituem recomendação de investimento.</p>
<p>O usuário é responsável por suas próprias decisões financeiras.</p>
"""
)

gerar_pagina(
    "cookies",
    "Política de Cookies",
    """
<p>Este site utiliza cookies para melhorar a experiência do usuário.</p>
<p>Cookies podem ser utilizados para análise de tráfego e anúncios personalizados.</p>
"""
)

gerar_pagina(
    "sobre",
    "Sobre o Projeto",
    """
<p>O Tá no Precinho é um projeto independente que analisa automaticamente ações da bolsa brasileira.</p>
<p>O objetivo é identificar empresas potencialmente negociadas abaixo do valor justo.</p>
"""
)

gerar_pagina(
    "contato",
    "Contato",
    """
<p>Para contato ou sugestões:</p>
<p>Email: contato@ta-noprecinho.com</p>
"""
)

gerar_pagina(
    "investidor",
    "Mensagem para o Investidor",
    """
<div style="max-width:700px;margin:auto">

<h2>📈 Uma mensagem para quem investe</h2>

<p>
O mercado financeiro não recompensa quem corre mais rápido.
Ele recompensa quem permanece mais tempo.
</p>

<p>
A paciência é uma das maiores vantagens competitivas de um investidor.
Enquanto muitos tentam prever o próximo movimento do mercado,
os grandes resultados geralmente vêm de algo muito mais simples:
tempo + disciplina.
</p>

<p>
Empresas crescem.
Lucros crescem.
Dividendos crescem.
</p>

<p>
Mas isso leva anos.
</p>

<p>
Se você está aqui analisando empresas,
você já está fazendo algo que a maioria das pessoas nunca fará:
pensando no longo prazo.
</p>

<p>
Continue aprendendo. Continue investindo. Continue paciente.
</p>

<p style="margin-top:30px;font-weight:600">
O tempo é o melhor amigo do investidor disciplinado.
</p>

<br>

<a href="/" style="color:#3b82f6">← Voltar ao ranking</a>

</div>
"""
)

gerar_pagina(
    "fundamentalista",
    "O que é Análise Fundamentalista",
    """
<div style="max-width:700px;margin:auto">

<h2>📊 O que é análise fundamentalista?</h2>

<p>
A análise fundamentalista é um método utilizado por investidores para avaliar o valor real de uma empresa.
Ela analisa os fundamentos do negócio, como lucros, endividamento, crescimento e geração de caixa.
</p>

<p>
O objetivo é descobrir se uma ação está sendo negociada por um preço justo, caro ou barato em relação ao valor da empresa.
</p>

<h3>Principais indicadores analisados</h3>

<ul>
<li>P/L (Preço sobre Lucro)</li>
<li>P/VP (Preço sobre Valor Patrimonial)</li>
<li>ROE (Retorno sobre patrimônio)</li>
<li>Dividend Yield</li>
</ul>

<p>
Investidores de longo prazo utilizam esses indicadores para encontrar empresas sólidas negociadas abaixo do valor justo.
</p>

<br>

<a href="javascript:history.back()">← Voltar</a>

</div>
"""
)

gerar_pagina(
    "pl",
    "O que é P/L",
    """
<div style="max-width:700px;margin:auto">

<h2>📈 O que é P/L?</h2>

<p>
O indicador P/L significa <strong>Preço sobre Lucro</strong>.
Ele mostra quantos anos levaria para o investidor recuperar o valor pago pela ação considerando o lucro atual da empresa.
</p>

<h3>Exemplo</h3>

<p>
Se uma empresa possui P/L = 10, significa que o preço da ação equivale a 10 anos de lucro da empresa.
</p>

<h3>Como interpretar</h3>

<ul>
<li>P/L baixo → pode indicar ação barata</li>
<li>P/L alto → pode indicar ação cara</li>
</ul>

<p>
Porém o indicador deve sempre ser analisado junto com crescimento, setor e qualidade da empresa.
</p>

<br>

<a href="javascript:history.back()">← Voltar</a>

</div>
"""
)

gerar_pagina(
    "roe",
    "O que é ROE",
    """
<div style="max-width:700px;margin:auto">

<h2>📊 O que é ROE?</h2>

<p>
ROE significa <strong>Return on Equity</strong>, ou retorno sobre o patrimônio líquido.
</p>

<p>
Esse indicador mostra quanto lucro a empresa gera utilizando o capital dos acionistas.
</p>

<h3>Exemplo</h3>

<p>
Se uma empresa possui ROE de 20%, significa que ela gera R$20 de lucro para cada R$100 de patrimônio.
</p>

<h3>Como interpretar</h3>

<ul>
<li>ROE alto → empresa eficiente</li>
<li>ROE baixo → menor rentabilidade</li>
</ul>

<br>

<a href="javascript:history.back()">← Voltar</a>

</div>
"""
)

gerar_pagina(
    "dividend-yield",
    "O que é Dividend Yield",
    """
<div style="max-width:700px;margin:auto">

<h2>💰 O que é Dividend Yield?</h2>

<p>
Dividend Yield é o indicador que mostra quanto uma empresa paga de dividendos em relação ao preço da ação.
</p>

<h3>Exemplo</h3>

<p>
Se uma ação custa R$100 e paga R$8 de dividendos por ano, o dividend yield é de 8%.
</p>

<h3>Como interpretar</h3>

<ul>
<li>Dividend Yield alto → maior renda de dividendos</li>
<li>Dividend Yield baixo → foco maior em crescimento</li>
</ul>

<p>
Empresas maduras costumam pagar mais dividendos do que empresas em fase de crescimento.
</p>

<br>

<a href="javascript:history.back()">← Voltar</a>

</div>
"""
)

# =========================
# Gerar pagina tickers
# =========================

def gerar_pagina_acao(row):

    ticker = row["Ticker"]

    texto_analise = f"""
    <h3>Análise da ação {ticker}</h3>

    <p>
    A ação <strong>{ticker}</strong> ({row["Empresa"]}) pertence ao setor
    <strong>{row["Setor"]}</strong> da bolsa brasileira.
    </p>

    <p>
    Atualmente apresenta <strong>P/L {round(row["PL"],2)}</strong>,
    <strong>P/VP {round(row["PVP"],2)}</strong> e
    <strong>ROE {round(row["ROE"]*100,2)}%</strong>.
    </p>

    <p>
    O dividend yield atual é de
    <strong>{round(row["DivYield"]*100,2)}%</strong>.
    </p>

    <p>
    Segundo nosso modelo baseado em múltiplo conservador de P/L 15,
    o preço justo estimado seria
    <strong>R$ {round(row["PrecoJusto"],2)}</strong>.
    </p>
    """


    descricao = f"""
    Análise da ação {ticker} ({row["Empresa"]}) da B3.
    Veja indicadores como P/L {round(row["PL"],2)},
    ROE {round(row["ROE"]*100,2)}%,
    Dividend Yield {round(row["DivYield"]*100,2)}%
    e estimativa de preço justo.
    """

    info_empresa = f"""
    <div class="card" style="max-width:700px;margin:20px auto;">

    <h3>🏢 Sobre a empresa</h3>

    <p style="line-height:1.6;color:#94a3b8">
    {row["Resumo"]}
    </p>

    <br>

    <p><strong>CNPJ:</strong> {row.get("CNPJ", "Não disponível")}</p>

    <p>
    <strong>Site oficial:</strong><br>
    <a href="{row.get("Site", "#")}" target="_blank" style="color:#3b82f6">
    {row.get("Site", "Não disponível")}
    </a>
    </p>

    </div>
    """

    keywords = f"{ticker}, {row['Empresa']}, ação {ticker}, análise fundamentalista, ações B3"

    with open("docs/layout_base.html", "r", encoding="utf-8") as f:
        template = f.read()

    conteudo = f"""
<a href="../index.html" class="secondary">← Voltar ao ranking</a>

<div class="card" style="max-width:420px;margin:auto">

<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">

<img src="../logos/{ticker}.png"
onerror="this.onerror=null;this.src='../logos/default.svg';"
style="width:32px;height:32px;object-fit:contain">

<div>
<h2 style="margin:0">{ticker}</h2>
<div class="secondary">{row["Empresa"]}</div>
</div>

</div>

<div class="secondary" style="margin-bottom:6px">{row["Setor"]}</div>

<span class="badge" style="
background:{cores_categoria.get(row['Categoria'], '#3b82f6')}20;
color:{cores_categoria.get(row['Categoria'], '#3b82f6')};
border:1px solid {cores_categoria.get(row['Categoria'], '#3b82f6')};
display:inline-block;
margin-bottom:12px">
{row["Categoria"]}
</span>

<div class="metric-grid">

<div class="metric">
<span>P/L</span>
<span>{round(row["PL"],2)}</span>
</div>

<div class="metric">
<span>P/VP</span>
<span>{round(row["PVP"],2)}</span>
</div>

<div class="metric">
<span>ROE</span>
<span>{round(row["ROE"]*100,2)}%</span>
</div>

<div class="metric">
<span>Dividend Yield</span>
<span>{round(row["DivYield"]*100,2)}%</span>
</div>

<div class="metric">
<span>Score</span>
<span style="color:{'#22c55e' if row['Score']>=70 else '#eab308'}">
{row["Score"]}
</span>
</div>

<div class="metric">
<span>Desconto</span>
<span style="color:#22c55e">
{round(row["Desconto_%"],2)}%
</span>
</div>

<div class="metric">
<span>Preço justo</span>
<span>R$ {round(row["PrecoJusto"],2)}</span>
</div>

<div class="metric">
<span>Risco</span>
<span style="font-size:20px">
{row["Farol"]}
</span>
</div>

</div>

</div>

<div class="card" style="max-width:700px;margin:20px auto;">
{texto_analise}
{info_empresa}
</div>

"""

    html = template.replace("{{titulo}}", ticker)
    html = html.replace("{{conteudo}}", conteudo)
    html = html.replace("{{descricao}}", descricao)
    html = html.replace("{{keywords}}", keywords)
    html = html.replace("{{url}}", f"https://tanoprecinho.site/acoes/{ticker}.html")

    # Schema JSON-LD
    schema = f"""
<script type="application/ld+json">
{{
 "@context": "https://schema.org",
 "@type": "FinancialProduct",
 "name": "{ticker}",
 "description": "{descricao.strip()}",
 "provider": {{
   "@type": "Organization",
   "name": "{row["Empresa"]}"
 }},
 "category": "Ação da B3",
 "url": "https://tanoprecinho.site/acoes/{ticker}.html"
}}
</script>
"""

    html = html.replace("</head>", schema + "\n</head>")

    with open(f"docs/acoes/{ticker}.html", "w", encoding="utf-8") as f:
        f.write(html)


# =========================
# GERAR páginas das ações
# =========================

for _, row in df.iterrows():
    gerar_pagina_acao(row)