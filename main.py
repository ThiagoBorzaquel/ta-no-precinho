import yfinance as yf
import pandas as pd
import time
import os
import datetime
import tqdm
import random
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from scripts.validate_data import validar_dados
from scripts.scoring import value_score
from scripts.scoring import calcular_preco_justo
from scripts.scoring import calcular_desconto
from scripts.scoring import calcular_risco, farol_risco
from scripts.scoring import calcular_ranking
from scripts.logger import logger
from scripts.logo_manager import preparar_logos
from scripts.collect_data import get_b3_tickers, get_stock_data, filtrar_acoes_validas
from scripts.history_manager import salvar_historico
from scripts.history_analysis import carregar_historico


traducao_setores = {
    "Energy": "Energia",
    "Basic Materials": "Materiais Básicos",
    "Financial Services": "Serviços Financeiros",
    "Healthcare": "Saúde",
    "Industrials": "Indústria",
    "Consumer Cyclical": "Consumo Cíclico",
    "Consumer Defensive": "Consumo Defensivo",
    "Utilities": "Utilidades Públicas",
    "Real Estate": "Imobiliário",
    "Communication Services": "Comunicação",
    "Technology": "Tecnologia"
}

cores_categoria = {
    "Blue Chips": "#3b82f6",
    "Mid Caps": "#22c55e",
    "Small Caps": "#facc15"
}

# =========================
# CLASSIFICAÇÃO MARKET CAP
# =========================

def classificar_cap(market_cap):
    if market_cap >= 50_000_000_000:
        return "Blue Chips"
    elif market_cap >= 10_000_000_000:
        return "Mid Caps"
    else:
        return "Small Caps"


# =========================
# EXECUÇÃO PRINCIPAL
# =========================

logger.info("iniciando pipeline")

print("Buscando dados da B3...")

tickers = get_b3_tickers()
tickers = filtrar_acoes_validas(tickers)
tickers = sorted(set(tickers))

logger.info(f"{len(tickers)} Ativos encontrados para análise.")

universo_b3 = len(tickers)

print("Ações filtradas:", universo_b3)

# =========================
# COLETA FUNDAMENTALISTA
# =========================

df = get_stock_data(tickers, traducao_setores, classificar_cap)

cnpj_empresas = {
    "PETR4": "33.000.167/0001-01",
    "VALE3": "33.592.510/0001-54",
    "ITUB4": "60.701.190/0001-04",
}

df["CNPJ"] = df["Ticker"].map(cnpj_empresas).fillna("Não disponível")

logger.info(f"{len(df)} empresas coletadas com dados fundamentalistas.")

df = validar_dados(df)

logger.info(f"{len(df)} empresas com dados válidos após validação.")

acoes_coletadas = len(df)

if df.empty or "Ticker" not in df.columns:
    print("⚠️ Nenhum dado disponível. Abortando execução.")
    exit()

# =========================
# LIMPAR NOMES
# =========================

def limpar_nome_empresa(nome):
    if not isinstance(nome, str):
        return nome

    remover = [
        " ON", " PN", " N1", " N2", " NM",
        "ON ", "PN ", "N1 ", "N2 ", "NM ",
        "ON", "PN", "N1", "N2", "NM"
    ]

    nome_limpo = nome

    for termo in remover:
        nome_limpo = nome_limpo.replace(termo, "")

    nome_limpo = " ".join(nome_limpo.split())

    return nome_limpo.strip()

# =========================
# FILTRO DE QUALIDADE
# =========================

df = df[
    (df["PL"] > 0) &
    (df["PL"] < 30) &
    (df["PVP"] > 0) &
    (df["PVP"] < 10) &
    (df["ROE"] > 0.10) &
    (df["ROE"] < 1) &
    (df["DivYield"] > 0.02) &
    (df["DivYield"] < 0.20) &
    (df["MarketCap"] > 1_000_000_000)
]

acoes_analisadas = len(df)

if df.empty:
    print("Nenhuma empresa passou no filtro.")
    logger.info("Nenhuma empresa passou no filtro de qualidade.")
    exit()

logger.info(f"{len(df)} empresas passaram no filtro de qualidade.")

# Score
df["Score"] = df.apply(value_score, axis=1)

pagadoras_div = len(df[df["DivYield"] > 0])
score_alto = len(df[df["Score"] >= 70])

total_acoes = len(df)
pagadoras_div = len(df[df["DivYield"] > 0])
score_alto = len(df[df["Score"] >= 70])

# Preço justo
df["LucroPorAcao"] = df["Preco"] / df["PL"]
df["PrecoJusto"] = df["LucroPorAcao"] * 15

# Desconto %
df["Desconto_%"] = df.apply(calcular_desconto, axis=1)

df["Ranking"] = df.apply(calcular_ranking, axis=1)

historico = carregar_historico(365)

top_n = 9999
df = df.nlargest(top_n, "Desconto_%")

# Risco
df["Risco"] = df.apply(calcular_risco, axis=1)
df["Risco_num"] = pd.to_numeric(df["Risco"], errors="coerce")
df["Farol"] = df["Risco"].apply(farol_risco)

def garantir_colunas(df):
    colunas = ["Desconto_%", "Ranking", "Risco", "Farol"]
    for c in colunas:
        if c not in df.columns:
            df[c] = 0
    return df

salvar_historico(df)

historico = carregar_historico(365)

if not historico.empty:
    historico = historico.sort_values("Data")
    preco_antigo = historico.groupby("Ticker")["Preco"].first()
    df["Preco_antigo"] = df["Ticker"].map(preco_antigo)
    df["Variacao_%"] = (
        (df["Preco"] - df["Preco_antigo"]) / df["Preco_antigo"] * 100
    ).fillna(0)
else:
    df["Variacao_%"] = 0

preparar_logos(df)
df = garantir_colunas(df)
df["Empresa"] = df["Empresa"].apply(limpar_nome_empresa)

top10 = df.head(5)
top_blue = df[df["Categoria"] == "Blue Chips"].sort_values("Desconto_%", ascending=False).head(5)
top_mid = df[df["Categoria"] == "Mid Caps"].sort_values("Desconto_%", ascending=False).head(5)
top_small = df[df["Categoria"] == "Small Caps"].sort_values("Desconto_%", ascending=False).head(5)

print("Empresas após filtros:", len(df))

total_acoes = len(df)
pagadoras_div = len(df[df["DivYield"] > 0])
score_alto = len(df[df["Score"] >= 70])

print(f"{len(df)} empresas válidas encontradas.")

# =========================
# GERAR SITEMAP
# =========================

def gerar_sitemap(df):

    base_url = "https://tanoprecinho.site"

    urls = []

    def add_url(loc, freq="daily", priority="0.7"):
        urls.append(f"""
        <url>
            <loc>{loc}</loc>
            <changefreq>{freq}</changefreq>
            <priority>{priority}</priority>
        </url>
        """)

    # HOME
    add_url(f"{base_url}/", "daily", "1.0")

    # PÁGINAS SEO FIXAS (TODAS DENTRO DE /seo)
    paginas = [
        "privacidade",
        "termos",
        "cookies",
        "sobre",
        "contato",
        "investidor",
        "fundamentalista",
        "pl",
        "roe",
        "dividend-yield",
        "missao"
    ]

    for p in paginas:
        add_url(f"{base_url}/seo/{p}.html", "monthly", "0.6")

    # PÁGINAS DE AÇÕES
    for _, row in df.iterrows():
        ticker = row["Ticker"]
        empresa = row["Empresa"]
        slug = gerar_slug(empresa, ticker)

        # página principal da ação
        add_url(f"{base_url}/acoes/{ticker}.html", "daily", "0.8")

        # páginas SEO da ação
        add_url(f"{base_url}/seo/{slug}.html")
        add_url(f"{base_url}/seo/vale-a-pena-{slug}.html")
        add_url(f"{base_url}/seo/{slug}-ta-barato.html")
        add_url(f"{base_url}/seo/{slug}-paga-dividendos.html")

    # PÁGINAS DE RANKING
    paginas_rank = [
        "melhores-acoes-dividendos",
        "acoes-baratas-2026",
        "melhores-acoes-para-investir",
        "acoes-maior-dividend-yield",
        "acoes-maior-roe",
        "acoes-mais-seguras",
        "acoes-dividendos-mensais"
    ]

    for p in paginas_rank:
        add_url(f"{base_url}/seo/{p}.html", "daily", "0.9")

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{''.join(urls)}
</urlset>
"""

    with open("docs/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap)

    print("✅ Sitemap gerado corretamente.")

# =========================
# GERAR MÉTRICA
# =========================

def gerar_metric(nome, valor, cor="#e2e8f0"):
    return f"""
    <div style="
    background:#020617;
    padding:14px;
    border-radius:14px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    ">
        <span style="color:#cbd5e1">{nome}</span>
        <strong style="color:#e2e8f0">{valor}</strong>
    </div>
    """

# =========================
# GERAR PÁGINAS AUTOMÁTICAS
# =========================

def _aplicar_template(nome, titulo, conteudo, descricao, keywords, url):
    with open("docs/layout_base.html", "r", encoding="utf-8") as f:
        template = f.read()
    html = template.replace("{{titulo}}", titulo)
    html = html.replace("{{conteudo}}", conteudo)
    html = html.replace("{{descricao}}", descricao)
    html = html.replace("{{keywords}}", keywords)
    html = html.replace("{{url}}", url)
    return html

def gerar_pagina_raiz(nome, titulo, conteudo, descricao="", keywords=""):
    """Páginas legais e educativas — salvas em docs/ (raiz do site)"""
    url = f"https://tanoprecinho.site/{nome}.html"
    html = _aplicar_template(nome, titulo, conteudo, descricao, keywords, url)
    with open(f"docs/{nome}.html", "w", encoding="utf-8") as f:
        f.write(html)

def gerar_pagina(nome, titulo, conteudo, descricao="", keywords=""):
    """Páginas de ranking/SEO — salvas em docs/seo/"""
    url = f"https://tanoprecinho.site/seo/{nome}.html"
    html = _aplicar_template(nome, titulo, conteudo, descricao, keywords, url)
    with open(f"docs/seo/{nome}.html", "w", encoding="utf-8") as f:
        f.write(html)


# =========================
# PÁGINAS INSTITUCIONAIS
# =========================

gerar_pagina_raiz(
    "privacidade",
    "Política de Privacidade",
    """
<p>Este site coleta informações de navegação para melhorar a experiência do usuário.</p>
<p>Utilizamos serviços como Google Analytics e Google AdSense que podem utilizar cookies.</p>
<p>Nenhuma informação pessoal sensível é armazenada.</p>
"""
)

gerar_pagina_raiz(
    "termos",
    "Termos de Uso",
    """
<p>As informações apresentadas possuem caráter educacional.</p>
<p>Não constituem recomendação de investimento.</p>
<p>O usuário é responsável por suas próprias decisões financeiras.</p>
"""
)

gerar_pagina_raiz(
    "cookies",
    "Política de Cookies",
    """
<p>Este site utiliza cookies para melhorar a experiência do usuário.</p>
<p>Cookies podem ser utilizados para análise de tráfego e anúncios personalizados.</p>
"""
)

gerar_pagina_raiz(
    "sobre",
    "Sobre o Projeto",
    """
<p>O Tá no Precinho é um projeto independente que analisa automaticamente ações da bolsa brasileira.</p>
<p>O objetivo é identificar empresas potencialmente negociadas abaixo do valor justo.</p>
"""
)

gerar_pagina_raiz(
    "contato",
    "Contato",
    """
<p>Para contato ou sugestões:</p>
<p>Email: contato@ta-noprecinho.com</p>
"""
)

gerar_pagina_raiz(
    "investidor",
    "Mensagem para o Investidor",
    """
<div style="max-width:700px;margin:auto">
<h2>📈 Uma mensagem para quem investe</h2>
<p>O mercado financeiro não recompensa quem corre mais rápido. Ele recompensa quem permanece mais tempo.</p>
<p>A paciência é uma das maiores vantagens competitivas de um investidor.</p>
<p>Empresas crescem. Lucros crescem. Dividendos crescem. Mas isso leva anos.</p>
<p>Se você está aqui analisando empresas, você já está fazendo algo que a maioria das pessoas nunca fará: pensando no longo prazo.</p>
<p style="margin-top:30px;font-weight:600">O tempo é o melhor amigo do investidor disciplinado.</p>
<br>
<a href="/docs/index.html" style="color:#3b82f6">← Voltar ao ranking</a>
</div>
"""
)

gerar_pagina_raiz(
    "fundamentalista",
    "O que é Análise Fundamentalista",
    """
<div style="max-width:700px;margin:auto">
<h2>📊 O que é análise fundamentalista?</h2>
<p>A análise fundamentalista é um método utilizado por investidores para avaliar o valor real de uma empresa.</p>
<p>O objetivo é descobrir se uma ação está sendo negociada por um preço justo, caro ou barato.</p>
<h3>Principais indicadores analisados</h3>
<ul>
<li>P/L (Preço sobre Lucro)</li>
<li>P/VP (Preço sobre Valor Patrimonial)</li>
<li>ROE (Retorno sobre patrimônio)</li>
<li>Dividend Yield</li>
</ul>
<br>
<a href="index.html" style="color:#3b82f6">← Voltar ao ranking</a>
</div>
"""
)

gerar_pagina_raiz(
    "pl",
    "O que é P/L",
    """
<div style="max-width:700px;margin:auto">
<h2>📈 O que é P/L?</h2>
<p>O indicador P/L significa <strong>Preço sobre Lucro</strong>. Ele mostra quantos anos levaria para o investidor recuperar o valor pago pela ação.</p>
<h3>Como interpretar</h3>
<ul>
<li>P/L baixo → pode indicar ação barata</li>
<li>P/L alto → pode indicar ação cara</li>
</ul>
<br>
<a href="index.html" style="color:#3b82f6">← Voltar ao ranking</a>
</div>
"""
)

gerar_pagina_raiz(
    "roe",
    "O que é ROE",
    """
<div style="max-width:700px;margin:auto">
<h2>📊 O que é ROE?</h2>
<p>ROE significa <strong>Return on Equity</strong>, ou retorno sobre o patrimônio líquido.</p>
<p>Mostra quanto lucro a empresa gera utilizando o capital dos acionistas.</p>
<h3>Como interpretar</h3>
<ul>
<li>ROE alto → empresa eficiente</li>
<li>ROE baixo → menor rentabilidade</li>
</ul>
<br>
<a href="index.html" style="color:#3b82f6">← Voltar ao ranking</a>
</div>
"""
)

gerar_pagina_raiz(
    "dividend-yield",
    "O que é Dividend Yield",
    """
<div style="max-width:700px;margin:auto">
<h2>💰 O que é Dividend Yield?</h2>
<p>Dividend Yield mostra quanto uma empresa paga de dividendos em relação ao preço da ação.</p>
<h3>Como interpretar</h3>
<ul>
<li>Dividend Yield alto → maior renda de dividendos</li>
<li>Dividend Yield baixo → foco maior em crescimento</li>
</ul>
<br>
<a href="index.html" style="color:#3b82f6">← Voltar ao ranking</a>
</div>
"""
)

gerar_pagina_raiz(
    "missao",
    "Nossa missão",
    """
<div style="max-width:700px;margin:auto">
<h2>🎯 Nossa missão</h2>
<p>Nosso objetivo é tornar a análise de ações mais simples, acessível e transparente para qualquer pessoa.</p>
<p>Criamos este site para fazer exatamente o contrário do mercado tradicional: informação clara, direta e visual.</p>
<hr style="margin:25px 0;border:1px solid #243247;">
<h2>📊 O que fazemos</h2>
<p>Analisamos automaticamente centenas de empresas listadas na B3 utilizando:</p>
<ul>
<li>P/L (Preço sobre Lucro)</li>
<li>P/VP (Preço sobre Valor Patrimonial)</li>
<li>ROE (Retorno sobre Patrimônio)</li>
<li>Dividend Yield</li>
</ul>
<p>A partir desses dados calculamos: Score de qualidade, preço justo estimado, nível de risco e grau de desconto.</p>
<hr style="margin:25px 0;border:1px solid #243247;">

<!-- FIX ACESSIBILIDADE: Transparência do Score explicada na página de missão -->
<h2>🔢 Como o Score é calculado</h2>
<p>O Score vai de 0 a 100 e é composto por critérios objetivos:</p>
<ul>
<li><strong>P/L baixo</strong> — quanto menor, maior a pontuação (empresa mais barata pelo lucro)</li>
<li><strong>P/VP baixo</strong> — empresa negociada abaixo do patrimônio recebe mais pontos</li>
<li><strong>ROE alto</strong> — empresas mais eficientes e rentáveis pontuam mais</li>
<li><strong>Dividend Yield alto</strong> — bom pagamento de dividendos contribui positivamente</li>
<li><strong>Desconto em relação ao preço justo</strong> — quanto maior o desconto, maior o Score</li>
</ul>
<p>O Score final combina esses fatores com pesos específicos por setor, pois cada segmento tem características diferentes (bancos, energia, varejo etc.).</p>
<hr style="margin:25px 0;border:1px solid #243247;">
<h2>🔎 Transparência</h2>
<p>Todas as análises são baseadas em critérios quantitativos e regras pré-definidas. Não há interferência manual nos rankings.</p>
<hr style="margin:25px 0;border:1px solid #243247;">
<h2>⚠️ Aviso importante</h2>
<p>Este site tem caráter exclusivamente informativo e educacional. <strong>Não constitui recomendação de compra ou venda de ativos.</strong> Cada investidor deve tomar suas próprias decisões considerando seu perfil de risco.</p>
<br>
<a href="index.html" style="color:#3b82f6">← Voltar ao ranking</a>
</div>
""",
    descricao="Conheça a missão do Tá no Precinho e como analisamos ações da bolsa de forma simples e transparente.",
    keywords="missão, análise de ações, bolsa brasileira, investimentos, educação financeira"
)

# =========================
# GERAR SLUG
# =========================

def gerar_slug(nome_empresa, ticker):
    try:
        nome = unicodedata.normalize('NFKD', nome_empresa).encode('ascii', 'ignore').decode('utf-8')
        nome = nome.lower()
        nome = re.sub(r'[^a-z0-9]+', '-', nome)
        nome = nome.strip('-')
        return f"{nome}-{ticker.lower()}"
    except:
        return ticker.lower()

# =========================
# TEXTOS DINÂMICOS
# =========================

aberturas = [
    "Muitos investidores se perguntam se vale a pena investir nesta {empresa}.",
    "Essa é uma dúvida comum entre investidores.",
    "Vamos analisar se essa ação {ticker} pode ser uma oportunidade."
]

fechamentos = [
    "Tudo depende do seu perfil de investimento.",
    "O ideal é analisar pensando no longo prazo.",
    "Cada investidor deve avaliar risco e retorno."
]

def interpretar_empresa(row):
    if row["Desconto_%"] > 20:
        return "A ação parece estar significativamente descontada."
    elif row["Desconto_%"] > 0:
        return "A ação está levemente abaixo do valor justo."
    else:
        return "A ação pode estar negociando acima do valor justo."


def gerar_texto_seo(row):
    return f"""
    <p>{random.choice(aberturas).format(empresa=row["Empresa"], ticker=row["Ticker"])}</p>
    <p>{interpretar_empresa(row)}</p>
    <p>A empresa apresenta ROE de {round(row["ROE"]*100,2)}% e dividend yield de {round(row["DivYield"]*100,2)}%.</p>
    <p>{random.choice(fechamentos)}</p>
    """

# =========================
# GERAR PÁGINA POR AÇÃO
# =========================

def gerar_pagina_acao(row):

    ticker = row["Ticker"]
    empresa = limpar_nome_empresa(row["Empresa"])

    descricao = f"Análise da ação {ticker} ({empresa}) com indicadores atualizados."
    keywords = f"{ticker}, {empresa}, ação {ticker}, análise fundamentalista"

    slug = gerar_slug(empresa, ticker)

    texto_analise = f"""
    <h3>📊 Vale a pena investir em {ticker}?</h3>
    <p>A <strong>{empresa} ({ticker})</strong> atua no setor <strong>{row["Setor"]}</strong>.</p>
    <p>Hoje apresenta P/L de <strong>{round(row["PL"],2)}</strong>,
    ROE de <strong>{round(row["ROE"]*100,2)}%</strong>
    e dividend yield de <strong>{round(row["DivYield"]*100,2)}%</strong>.</p>
    <p>O preço justo estimado é de <strong>R$ {round(row["PrecoJusto"],2)}</strong>.</p>
    """

    info_empresa = f"""
    <div class="card" style="max-width:700px;margin:20px auto;">
    <h3>🏢 Sobre a empresa {empresa}</h3>
    <p style="line-height:1.6;color:#cbd5e1">{row["Resumo"]}</p>
    </div>
    """

    links = f"""
    <div class="card" style="max-width:700px;margin:20px auto;">
    <h3>🔗 Explore mais</h3>
    <ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:8px;">
      <li><a href="../seo/vale-a-pena-{slug}.html">Vale a pena investir em {empresa}?</a></li>
      <li><a href="../seo/{slug}-paga-dividendos.html">{empresa} paga dividendos?</a></li>
      <li><a href="../seo/{slug}-ta-barato.html">{empresa} está barata?</a></li>
    </ul>
    </div>
    """

    with open("docs/layout_base.html", "r", encoding="utf-8") as f:
        template = f.read()

    conteudo = f"""

    <a href="../index.html" style="color:#94a3b8;font-size:13px;">← Voltar ao ranking</a>

    <div style="text-align:center;margin:20px 0">

    <!-- FIX ACESSIBILIDADE: alt descritivo na logo -->
    <img src="../logos/{ticker}.png"
         alt="Logo da empresa {empresa}"
         onerror="this.onerror=null;this.src='../logos/default.svg';"
         style="width:50px;height:50px;margin-bottom:10px">

    <h1 style="margin:0">{empresa} ({ticker})</h1>
    <div style="color:#cbd5e1;margin-top:5px">{row["Setor"]}</div>

    </div>

    <div style="max-width:420px;margin:auto">
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:15px;">
    {gerar_metric("P/L", round(row["PL"],2))}
    {gerar_metric("P/VP", round(row["PVP"],2))}
    {gerar_metric("ROE", f'{round(row["ROE"]*100,2)}%')}
    {gerar_metric("DY", f'{round(row["DivYield"]*100,2)}%')}
    {gerar_metric("Score", row["Score"], "#22c55e" if row["Score"] >= 70 else "#eab308")}
    {gerar_metric("Desconto", f'{round(row["Desconto_%"],2)}%', "#22c55e" if row["Desconto_%"] > 0 else "#ef4444")}
    {gerar_metric("Preço justo", f'R$ {round(row["PrecoJusto"],2)}')}
    {gerar_metric("Risco", row["Farol"])}
    </div>
    </div>

    <div class="card" style="max-width:700px;margin:20px auto;">
    {texto_analise}
    </div>

    {info_empresa}
    {links}
    """

    html = template.replace("{{titulo}}", ticker)
    html = html.replace("{{conteudo}}", conteudo)
    html = html.replace("{{descricao}}", descricao)
    html = html.replace("{{keywords}}", keywords)
    html = html.replace("{{url}}", f"https://tanoprecinho.site/acoes/{ticker}.html")

    with open(f"docs/acoes/{ticker}.html", "w", encoding="utf-8") as f:
        f.write(html)

    with open(f"docs/seo/{slug}.html", "w", encoding="utf-8") as f:
        f.write(html)

# =========================
# GERAR PÁGINAS SEO POR TICKER
# =========================

def gerar_paginas_seo_ticker(row):

    ticker = row["Ticker"]
    empresa = limpar_nome_empresa(row["Empresa"])
    slug = gerar_slug(empresa, ticker)

    paginas = [
        (f"vale-a-pena-{slug}", f"👉 Vale a pena investir em {empresa} ({ticker})?"),
        (f"{slug}-ta-barato", f"{empresa} ({ticker}) 📉 está barato?"),
        (f"{slug}-paga-dividendos", f"{empresa} ({ticker}) 💰 paga dividendos?")
    ]

    for nome, titulo in paginas:

        conteudo = f"""
    <div style="max-width:900px;margin:auto">

    <div style="max-width:700px;margin:auto;margin-bottom:15px">
    <a href="../index.html" style="display:inline-block;color:#cbd5e1;text-decoration:none;font-size:13px;padding:6px 10px;border-radius:8px;background:#1e293b;">
      ← Voltar ao ranking
    </a>
    </div>

    <div class="card" style="text-align:center;margin-bottom:15px">

    <!-- FIX ACESSIBILIDADE: alt descritivo na logo -->
    <img src="../logos/{ticker}.png"
         alt="Logo da empresa {empresa}"
         onerror="this.onerror=null;this.src='../logos/default.svg';"
         style="width:50px;height:50px;margin-bottom:10px">

    <h1 style="margin:0;font-size:22px">{empresa} ({ticker})</h1>
    <p style="color:#22c55e;font-size:13px;margin-bottom:10px">Atualizado hoje • Dados da bolsa</p>
    <div style="color:#cbd5e1;margin-top:5px">{row["Setor"]}</div>

    </div>

    <div class="card">
    {gerar_texto_seo(row)}
    </div>

    <div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">
    <h3>📊 Indicadores</h3>
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:10px;">
    {gerar_metric("P/L", round(row["PL"],2))}
    {gerar_metric("ROE", f'{round(row["ROE"]*100,2)}%')}
    {gerar_metric("DY", f'{round(row["DivYield"]*100,2)}%')}
    {gerar_metric("Desconto", f'{round(row["Desconto_%"],2)}%')}
    </div>
    </div>

    <div class="card">
    <h3>🔗 Continue analisando</h3>
    <a href="../acoes/{ticker}.html" style="display:inline-block;margin-top:10px;padding:10px 16px;background:#22c55e;color:white;border-radius:8px;text-decoration:none;font-weight:600;">
      Ver análise completa de {empresa} →
    </a>
    <br><br>
    <a href="../index.html" style="color:#3b82f6">← Ver ranking completo</a>
    </div>

    </div>
    """

        with open("docs/layout_base.html", "r", encoding="utf-8") as f:
            template = f.read()

        html = template.replace("{{titulo}}", titulo)
        html = html.replace("{{conteudo}}", conteudo)
        html = html.replace("{{descricao}}", titulo)
        html = html.replace("{{keywords}}", titulo)
        html = html.replace("{{url}}", f"https://tanoprecinho.site/seo/{nome}.html")

        with open(f"docs/seo/{nome}.html", "w", encoding="utf-8") as f:
            f.write(html)

# =========================
# GERAR PÁGINAS DE RANKING
# =========================

def gerar_paginas_ranking(df):

    top_div = df.sort_values("DivYield", ascending=False).head(20)

    lista_div = "".join([
    f"""
    <div style="background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);padding:14px;border-radius:12px;display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px">
    <img src="../logos/{row['Ticker']}.png"
         alt="Logo {row['Empresa']}"
         onerror="this.onerror=null;this.src='../logos/default.svg';"
         style="width:28px;height:28px">
    <div>
    <a href="../acoes/{row['Ticker']}.html" style="color:#e2e8f0;text-decoration:none;font-weight:600;">{row['Empresa']}</a>
    <div style="font-size:12px;color:#cbd5e1">{row['Ticker']}</div>
    </div>
    </div>
    <div style="color:#22c55e;font-weight:700;">{round(row['DivYield']*100,2)}%</div>
    </div>
    """
    for _, row in top_div.iterrows()
    ])

    gerar_pagina(
        "melhores-acoes-dividendos",
        "Melhores ações de dividendos",
        f"<div>{lista_div}</div>",
        descricao="Ranking atualizado das melhores ações de dividendos da bolsa.",
        keywords="melhores dividendos, ações dividendos"
    )

    top_baratas = df.sort_values("Desconto_%", ascending=False).head(20)

    lista_baratas = "".join([
    f"""
    <div style="background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);padding:14px;border-radius:12px;display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px">
    <img src="../logos/{row['Ticker']}.png"
         alt="Logo {row['Empresa']}"
         onerror="this.onerror=null;this.src='../logos/default.svg';"
         style="width:28px;height:28px">
    <div>
    <a href="../acoes/{row['Ticker']}.html" style="color:#e2e8f0;text-decoration:none;font-weight:600;">{row['Empresa']}</a>
    <div style="font-size:12px;color:#cbd5e1">{row['Ticker']}</div>
    </div>
    </div>
    <div style="color:#22c55e;font-weight:700;">{round(row['Desconto_%'],2)}%</div>
    </div>
    """
    for _, row in top_baratas.iterrows()
    ])

    gerar_pagina(
        "acoes-baratas-2026",
        "Ações mais baratas da bolsa",
        f"<div>{lista_baratas}</div>",
        descricao="Veja as ações mais baratas hoje na bolsa.",
        keywords="ações baratas, ações descontadas"
    )

# =========================
# GERAR PÁGINAS HIGH INTENT
# =========================

def gerar_paginas_high_intent(df):

    def montar_lista(df_base, tipo="geral"):
        html_lista = ""

        for i, (_, row) in enumerate(df_base.iterrows(), start=1):
            medalhas = ["🥇", "🥈", "🥉"]
            icone = medalhas[i-1] if i <= 3 else ""

            tag = ""
            if row["DivYield"] > 0.08:
                tag = "💰 RENDA"
            elif row["ROE"] > 0.20:
                tag = "🏆 ALTA RENT"
            elif row["Desconto_%"] > 50:
                tag = "🔥 OPORTUNIDADE"

            html_lista += f"""
            <a href="../acoes/{row['Ticker']}.html" style="text-decoration:none;color:inherit" aria-label="Ver análise de {row['Empresa']} ({row['Ticker']})">
            <div style="background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);padding:14px;border-radius:12px;display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
            <div style="display:flex;align-items:center;gap:10px">
            <img src="../logos/{row['Ticker']}.png"
                 alt="Logo {row['Empresa']}"
                 onerror="this.onerror=null;this.src='../logos/default.svg';"
                 style="width:28px;height:28px">
            <div>
            <div style="font-weight:600">#{i} {icone} {row['Empresa']}</div>
            <div style="font-size:12px;color:#cbd5e1">{row['Ticker']} • {row['Setor']}</div>
            </div>
            </div>
            <div style="text-align:right">
            <div style="color:#22c55e;font-weight:700">{round(row['Score'],0)}</div>
            <div style="font-size:11px;color:#cbd5e1">{tag}</div>
            </div>
            </div>
            </a>
            """

        return html_lista

    top_score = df.sort_values("Score", ascending=False).head(20)
    gerar_pagina(
        "melhores-acoes-para-investir",
        "Melhores ações para investir em 2026",
        f"""<div class="card"><h2>🏆 Melhores ações para investir</h2>
        <p style="color:#22c55e;font-size:13px">Atualizado hoje • Ranking baseado em Score</p>
        {montar_lista(top_score)}</div>""",
        descricao="Veja as melhores ações para investir hoje na bolsa brasileira.",
        keywords="melhores ações 2026, melhores ações para investir hoje"
    )

    top_dy = df.sort_values("DivYield", ascending=False).head(20)
    gerar_pagina(
        "acoes-maior-dividend-yield",
        "Ações com maior dividend yield hoje",
        f"""<div class="card"><h2>💰 Maiores pagadoras de dividendos</h2>
        <p style="color:#22c55e;font-size:13px">Atualizado hoje • Ranking por Dividend Yield</p>
        {montar_lista(top_dy)}</div>""",
        descricao="Ranking das ações com maior dividend yield da bolsa.",
        keywords="ações dividend yield alto, melhores dividendos hoje"
    )

    top_roe = df.sort_values("ROE", ascending=False).head(20)
    gerar_pagina(
        "acoes-maior-roe",
        "Ações com maior ROE da bolsa",
        f"""<div class="card"><h2>📈 Empresas mais rentáveis</h2>
        <p style="color:#22c55e;font-size:13px">Atualizado hoje • Ranking por ROE</p>
        {montar_lista(top_roe)}</div>""",
        descricao="Veja as empresas mais rentáveis da bolsa com maior ROE.",
        keywords="ações com maior roe, empresas mais lucrativas"
    )

    seguras = df[df["Risco_num"] < 0.3].sort_values("Score", ascending=False).head(20)
    gerar_pagina(
        "acoes-mais-seguras",
        "Ações mais seguras da bolsa",
        f"""<div class="card"><h2>🛡️ Ações mais seguras</h2>
        <p style="color:#22c55e;font-size:13px">Baixo risco • Score alto</p>
        {montar_lista(seguras)}</div>""",
        descricao="Ranking de ações mais seguras da bolsa brasileira.",
        keywords="ações seguras, ações baixo risco"
    )

    renda = df[df["DivYield"] > 0.06].sort_values("DivYield", ascending=False).head(20)
    gerar_pagina(
        "acoes-dividendos-mensais",
        "Ações para renda mensal com dividendos",
        f"""<div class="card"><h2>💵 Renda mensal com dividendos</h2>
        <p style="color:#cbd5e1;font-size:13px">Empresas com alto pagamento de dividendos</p>
        {montar_lista(renda)}</div>""",
        descricao="Ações que podem gerar renda mensal com dividendos.",
        keywords="ações dividendos mensais, renda passiva ações"
    )

# =========================
# SETUP DIRETÓRIOS
# =========================

os.makedirs("docs", exist_ok=True)
os.makedirs("docs/acoes", exist_ok=True)
os.makedirs("docs/seo", exist_ok=True)

hoje = datetime.date.today()
data_br = hoje.strftime("%d/%m/%Y")

df.to_csv("docs/ranking.csv", index=False)

setores = sorted(df["Setor"].unique())
categorias = sorted(df["Categoria"].unique())

top3 = df.head(3)

logger.info("Gerando site...")

for _, row in df.iterrows():
    gerar_pagina_acao(row)
    gerar_paginas_seo_ticker(row)

gerar_paginas_ranking(df)
gerar_paginas_high_intent(df)
gerar_sitemap(df)

# =========================
# HTML PRINCIPAL - INDEX
# =========================

setores = sorted(df["Setor"].unique())
categorias = sorted(df["Categoria"].unique())

html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>

<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5213961841779335" crossorigin="anonymous"></script>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Ranking automático das ações brasileiras mais baratas baseado em análise fundamentalista. Atualizado diariamente.">
<meta name="keywords" content="ações baratas, bolsa brasileira, value investing, ranking ações, B3">
<meta property="og:title" content="Tá no Precinho? - Ranking de ações brasileiras">
<meta property="og:description" content="Descubra quais ações podem estar baratas hoje segundo análise fundamentalista.">
<meta property="og:image" content="https://tanoprecinho.site/images/og-image.jpg">

<link rel="icon" type="image/png" sizes="32x32" href="/favicon.png">
<link rel="shortcut icon" href="/favicon.ico">

<title>Tá no Precinho? | Ranking de ações da bolsa brasileira</title>

<script>
window.addEventListener("load", function() {{
  let script = document.createElement("script");
  script.src = "https://cdn.jsdelivr.net/npm/chart.js";
  document.body.appendChild(script);
}});
</script>

<style>
:root{{
    --bg:#0f172a;
    --card:#1e293b;
    --card-light:#0f172a;
    --accent:#3b82f6;
    --text:#e2e8f0;
    --muted:#cbd5e1;
}}

body{{
    margin:0;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    background:var(--bg);
    color:var(--text);
}}

.container{{
    max-width:1200px;
    margin:auto;
    padding:25px 16px;
}}

h1{{ margin-top:0; }}

.subtitle{{
    color:var(--muted);
    margin-bottom:25px;
    font-size:14px;
}}

.card{{
    background:var(--card);
    padding:14px;
    border-radius:12px;
    margin-bottom:14px;
}}

/* FIX ACESSIBILIDADE: label + select associados */
.filter-group{{
    display:flex;
    flex-direction:column;
    gap:4px;
}}

.filters{{
    display:grid;
    grid-template-columns:repeat(5,1fr);
    gap:12px;
    align-items:flex-end;
}}

select,input{{
    padding:8px;
    border-radius:8px;
    border:none;
    font-size:14px;
    background:#0f172a;
    color:#e2e8f0;
}}

/* FIX ACESSIBILIDADE: foco visível */
select:focus, input:focus, a:focus, button:focus, [tabindex]:focus {{
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
}}

tr:nth-child(even){{
    background:var(--card-light);
}}

.badge{{
    padding:4px 8px;
    border-radius:8px;
    font-size:11px;
}}

.grid{{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
    gap:15px;
}}

.grafico-box{{
    background:var(--card-light);
    padding:12px;
    border-radius:12px;
}}

.stats{{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
    gap:15px;
    margin-bottom:25px;
}}

.stat-box{{
    background:var(--card);
    padding:16px;
    border-radius:12px;
    text-align:center;
}}

.stat-num{{
    font-size:22px;
    font-weight:bold;
}}

.stat-label{{
    font-size:12px;
    color:var(--muted);
}}

canvas{{ max-height:250px; }}

/* FIX ACESSIBILIDADE: aviso de risco visível acima do ranking */
.aviso-risco{{
    background:rgba(234,179,8,0.1);
    border:1px solid rgba(234,179,8,0.3);
    border-radius:10px;
    padding:12px 16px;
    font-size:13px;
    color:#fde68a;
    margin-bottom:16px;
    display:flex;
    align-items:flex-start;
    gap:8px;
}}

.footer{{
    margin-top:30px;
    font-size:12px;
    color:var(--muted);
    text-align:center;
}}

.footer-links{{
    display:flex;
    justify-content:center;
    gap:20px;
    flex-wrap:wrap;
    margin-bottom:10px;
}}

.footer-links a{{
    color:#cbd5e1;
    font-size:13px;
    text-decoration:none;
}}

.footer-links a:hover{{ color:#3b82f6; }}

.footer-copy{{ font-size:12px;color:#64748b; }}

@media(max-width:768px){{
    h1{{ font-size:22px; }}
    .subtitle{{ font-size:13px; }}
    .filters{{ grid-template-columns:1fr; }}
    select,input{{ width:100%;padding:10px; }}
    thead{{ display:none; }}
    table,tbody,tr,td{{ display:block;width:100%; }}
    tbody{{ display:flex;flex-direction:column;align-items:center;gap:14px; }}
    tr{{ background:var(--card);max-width:420px;width:90%;margin:auto;padding:14px;border-radius:14px;box-shadow:0 6px 18px rgba(0,0,0,0.35); }}
    td{{ display:flex;justify-content:space-between;padding:6px 0;font-size:13px; }}
    td:first-child{{ display:block;font-size:16px;font-weight:bold;margin-bottom:4px;text-align:left; }}
    td:nth-child(4)::before{{content:"P/L: ";}}
    td:nth-child(5)::before{{content:"P/VP: ";}}
    td:nth-child(6)::before{{content:"ROE: ";}}
    td:nth-child(7)::before{{content:"Dividend Yield: ";}}
    td:nth-child(8)::before{{content:"Score: ";}}
    td:nth-child(9)::before{{content:"Desconto: ";}}
    td:nth-child(10)::before{{content:"Preço justo: ";}}
    td:nth-child(11)::before{{content:"Risco: ";}}
    td::before{{ font-weight:600;color:var(--muted); }}
    .footer-links{{ flex-direction:column;gap:8px; }}
}}

table{{ width:100%;border-collapse:collapse;margin-top:10px; }}
thead{{ background:#334155; }}

/* FIX ACESSIBILIDADE: scope nos th via HTML */
th{{
    padding:12px 10px;
    font-size:13px;
    text-align:center;
    color:#cbd5e1;
    cursor:pointer;
}}

th:hover{{ background:#3d5068; }}

td{{
    padding:12px 10px;
    font-size:13px;
    text-align:center;
    border-bottom:1px solid #243247;
}}

tbody tr{{ cursor:pointer; }}
tbody tr:hover{{ background:#1f2a3d; }}

td:first-child{{ text-align:left; }}

.ticker{{
    font-weight:700;
    font-size:14px;
    color:#e2e8f0;
    text-decoration:none;
}}

.ticker:hover{{ color:#3b82f6; }}

.empresa{{ font-size:11px;color:#cbd5e1; }}

.desconto-positivo{{ color:#22c55e;font-weight:600; }}
.desconto-negativo{{ color:#ef4444; }}
.score-alto{{ color:#22c55e;font-weight:700; }}
.score-medio{{ color:#eab308; }}

#cookie-banner{{
    position:fixed;
    bottom:20px;
    left:50%;
    transform:translateX(-50%);
    z-index:9999;
    width:90%;
    max-width:420px;
    display:none;
}}

.cookie-box{{
    background:#1e293b;
    padding:16px;
    border-radius:12px;
    box-shadow:0 8px 30px rgba(0,0,0,0.4);
    font-size:13px;
    color:#e2e8f0;
}}

.cookie-box a{{ color:#3b82f6;text-decoration:none; }}

.cookie-buttons{{ display:flex;gap:10px;margin-top:10px; }}

.cookie-accept{{
    background:#22c55e;border:none;padding:8px 14px;
    border-radius:8px;cursor:pointer;color:white;
}}

.cookie-reject{{
    background:#ef4444;border:none;padding:8px 14px;
    border-radius:8px;cursor:pointer;color:white;
}}

.menu{{
    display:flex;
    flex-wrap:wrap;
    gap:14px;
    margin:12px 0 22px 0;
    font-size:14px;
}}

.menu a{{
    color:#cbd5e1;
    text-decoration:none;
    padding:6px 10px;
    border-radius:8px;
    background:#1e293b;
}}

.menu a:hover{{ color:#3b82f6;background:#243247; }}

details{{ cursor:pointer; }}
summary{{ font-weight:600;font-size:16px;margin-bottom:10px; }}
details p{{ margin-top:10px; }}

</style>

<script>

let ordemAsc = false;

function aplicarFiltros() {{
    let categoria = document.getElementById("filtroCategoria").value;
    let setorFiltro = document.getElementById("filtroSetor").value;
    let scoreMin = parseFloat(document.getElementById("filtroScore").value) || 0;
    let quantidade = parseInt(document.getElementById("filtroQuantidade").value);
    let periodo = parseInt(document.getElementById("filtroPeriodo").value);

    let linhas = Array.from(document.querySelectorAll("tbody tr"));

    let filtradas = linhas.filter(linha => {{
        let setorLinha = linha.dataset.setor;
        let categoriaLinha = linha.dataset.categoria;
        let scoreLinha = parseFloat(linha.dataset.score);
        let variacaoLinha = parseFloat(linha.dataset.variacao);

        if (setorFiltro !== "Todos" && setorLinha !== setorFiltro) return false;
        if (categoria !== "Todos" && categoriaLinha !== categoria) return false;
        if (scoreLinha < scoreMin) return false;
        if (periodo > 0 && variacaoLinha === 0) return false;

        return true;
    }});

    linhas.forEach(l => l.style.display = "none");
    filtradas.slice(0, quantidade).forEach(l => {{ l.style.display = ""; }});
}}

function ordenarTabela(coluna) {{
    let tabela = document.querySelector("tbody");
    let linhas = Array.from(tabela.querySelectorAll("tr"));

    ordemAsc = !ordemAsc;

    linhas.sort((a, b) => {{
        let valA = a.children[coluna].innerText.replace('%','').replace(',','.');
        let valB = b.children[coluna].innerText.replace('%','').replace(',','.');
        return ordemAsc
            ? parseFloat(valA) - parseFloat(valB)
            : parseFloat(valB) - parseFloat(valA);
    }});

    linhas.forEach(l => tabela.appendChild(l));
}}

function criarGrafico(id, labels, data, cor) {{
    new Chart(document.getElementById(id), {{
        type: 'bar',
        data: {{
            labels: labels,
            datasets: [{{ data: data, backgroundColor: cor, borderRadius: 6 }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{ y: {{ beginAtZero: true }} }}
        }}
    }});
}}

window.onload = function() {{
    criarGrafico("graficoTop10", {list(top10["Ticker"])}, {list(top10["Desconto_%"])}, "#ef4444");
    criarGrafico("graficoBlue", {list(top_blue["Ticker"])}, {list(top_blue["Desconto_%"])}, "#3b82f6");
    criarGrafico("graficoMid", {list(top_mid["Ticker"])}, {list(top_mid["Desconto_%"])}, "#22c55e");
    criarGrafico("graficoSmall", {list(top_small["Ticker"])}, {list(top_small["Desconto_%"])}, "#facc15");
    aplicarFiltros();
}};

function aceitarCookies(){{
    localStorage.setItem("cookies_consent","accepted");
    document.getElementById("cookie-banner").style.display="none";
}}

function recusarCookies(){{
    localStorage.setItem("cookies_consent","rejected");
    document.getElementById("cookie-banner").style.display="none";
}}

function verificarCookies(){{
    let consent = localStorage.getItem("cookies_consent");
    if(!consent){{ document.getElementById("cookie-banner").style.display="block"; }}
}}

window.addEventListener("load", verificarCookies);

</script>

</head>

<body>

<div class="container">

<!-- FIX ACESSIBILIDADE: nav com aria-label -->
<nav aria-label="Menu principal">
<div style="margin-bottom:20px" class="menu">
  <a href="index.html">Ranking</a>
  <a href="missao.html">Nossa missão</a>
  <a href="fundamentalista.html">Análise Fundamentalista</a>
  <a href="pl.html">O que é P/L</a>
  <a href="roe.html">O que é ROE</a>
  <a href="dividend-yield.html">Dividend Yield</a>
</div>
</nav>

<header>
<h1>
<a href="investidor.html" style="text-decoration:none;color:inherit" aria-label="Tá no Precinho - página inicial">
📉 Tá no Precinho?
</a>
</h1>

<p class="subtitle">
Criamos este site com um objetivo simples: tornar a análise de ações acessível para qualquer pessoa.
A informação aqui é gratuita e sempre será.<br>
Atualizado automaticamente todos os dias.<br><br>
Atualizado em {data_br}
</p>
</header>

<main>

<!-- ESTATÍSTICAS -->
<div class="stats" role="region" aria-label="Estatísticas gerais">

<div class="stat-box">
<div class="stat-num">{universo_b3}</div>
<div class="stat-label">📊 Ativos B3</div>
</div>

<div class="stat-box">
<div class="stat-num">{acoes_coletadas}</div>
<div class="stat-label">🔎 Ações analisadas</div>
</div>

<div class="stat-box">
<div class="stat-num">{acoes_analisadas}</div>
<div class="stat-label">💰 Pagadoras de dividendos</div>
</div>

<div class="stat-box">
<div class="stat-num">{score_alto}</div>
<div class="stat-label">🏆 Score ≥ 70</div>
</div>

</div>

<!-- FILTROS -->
<!-- FIX ACESSIBILIDADE: todos os labels com for= associados ao id do select -->
<div class="card" role="search" aria-label="Filtros do ranking">
<div class="filters">

<div class="filter-group">
<label for="filtroQuantidade">Quantidade</label>
<select id="filtroQuantidade" onchange="aplicarFiltros()">
<option value="20" selected>20</option>
<option value="30">30</option>
<option value="40">40</option>
<option value="50">50</option>
<option value="100">100</option>
<option value="9999">Todos</option>
</select>
</div>

<div class="filter-group">
<label for="filtroSetor">Setor</label>
<select id="filtroSetor" onchange="aplicarFiltros()">
<option>Todos</option>
"""

for s in setores:
    html += f"<option>{s}</option>"

html += """
</select>
</div>

<div class="filter-group">
<label for="filtroCategoria">Categoria</label>
<select id="filtroCategoria" onchange="aplicarFiltros()">
<option>Todos</option>
"""

for c in categorias:
    html += f"<option>{c}</option>"

html += """
</select>
</div>

<div class="filter-group">
<label for="filtroPeriodo">Período</label>
<select id="filtroPeriodo" onchange="aplicarFiltros()">
<option value="0">Hoje</option>
<option value="7">1 semana</option>
<option value="15">15 dias</option>
<option value="30">1 mês</option>
<option value="90">3 meses</option>
<option value="180">6 meses</option>
<option value="365">1 ano</option>
</select>
</div>

<div class="filter-group">
<label for="filtroScore">Score mínimo</label>
<input type="number" id="filtroScore" onchange="aplicarFiltros()" placeholder="Ex: 50" aria-label="Score mínimo">
</div>

</div>
</div>

<!-- GRÁFICOS -->
<div class="card" role="region" aria-label="Gráficos de desempenho">
<h2>📊 Gráficos</h2>
<div class="grid">

<div class="grafico-box">
<h3>Mais descontadas do dia 🔥</h3>
<canvas id="graficoTop10" aria-label="Gráfico das ações mais descontadas" role="img"></canvas>
</div>

<div class="grafico-box">
<h3>Blue Chips 🏦</h3>
<canvas id="graficoBlue" aria-label="Gráfico Blue Chips" role="img"></canvas>
</div>

<div class="grafico-box">
<h3>Mid Caps 📈</h3>
<canvas id="graficoMid" aria-label="Gráfico Mid Caps" role="img"></canvas>
</div>

<div class="grafico-box">
<h3>Small Caps 🚀</h3>
<canvas id="graficoSmall" aria-label="Gráfico Small Caps" role="img"></canvas>
</div>

</div>
</div>

<!-- OPORTUNIDADES -->
<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Explore rankings prontos com as melhores ações da bolsa hoje.</p>
<nav aria-label="Rankings especializados" class="menu">
<a href="seo/melhores-acoes-para-investir.html">🏆 Melhores ações</a>
<a href="seo/acoes-maior-dividend-yield.html">💰 Dividendos</a>
<a href="seo/acoes-maior-roe.html">📈 Alta rentabilidade</a>
<a href="seo/acoes-mais-seguras.html">🛡️ Mais seguras</a>
<a href="seo/acoes-dividendos-mensais.html">💵 Renda mensal</a>
<a href="seo/acoes-baratas-2026.html">🔥 Ações baratas</a>
<a href="seo/melhores-acoes-dividendos.html">💸 Dividendos 2026</a>
</nav>
</div>

<!-- RANKING -->
<div class="card" role="region" aria-label="Ranking de ações">
<h2>📋 Ranking</h2>

<p style="color:#22c55e;font-size:13px;margin-bottom:6px">Atualizado hoje • Dados em tempo real</p>

<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">
Ranking das ações mais descontadas da bolsa com base em análise fundamentalista.
</p>

<!-- FIX ACESSIBILIDADE: aviso de risco visível, acima da tabela -->
<div class="aviso-risco" role="note" aria-label="Aviso de risco">
  ⚠️ <span><strong>Atenção:</strong> Este ranking é informativo e educacional. <strong>Não constitui recomendação de investimento.</strong> Sempre faça sua própria análise antes de investir.</span>
</div>

<details class="ranking-explicacao">

<summary>📊 Como funciona o ranking?</summary>

<div style="font-size:14px;color:#94a3b8;line-height:1.7">

<p>
Este ranking foi criado para identificar ações que podem estar negociando abaixo do valor justo,
utilizando critérios objetivos da análise fundamentalista.
</p>

<br>

<h3>📊 Critérios analisados</h3>

<p>
As empresas são avaliadas com base em:
</p>

<ul>
<li><strong>P/L</strong> – relação entre preço e lucro</li>
<li><strong>P/VP</strong> – relação entre preço e patrimônio</li>
<li><strong>ROE</strong> – eficiência da empresa</li>
<li><strong>Dividend Yield</strong> – retorno em dividendos</li>
</ul>

<p>
Com base nesses dados, calculamos:
</p>

<ul>
<li>Score de qualidade</li>
<li>Preço justo estimado (P/L = 15)</li>
<li>Percentual de desconto</li>
<li>Nível de risco</li>
</ul>

<br>

<h3>🏆 Como funciona o ranking</h3>

<p>
As ações são ordenadas principalmente pelo <strong>desconto em relação ao preço justo</strong>.
</p>

<p>
Quanto maior o desconto e melhor o score, melhor a posição no ranking.
</p>

<br>

<h3>🧠 Legenda dos ícones</h3>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">

<div>🥇 🥈 🥉 → Top 3 do ranking</div>
<div>💰 → Alto pagamento de dividendos</div>
<div>🏆 → Alta rentabilidade (ROE elevado)</div>
<div>🔥 → Grande desconto (oportunidade)</div>

</div>

<br>

<h3>🚦 Risco (farol)</h3>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">

<div>🟢 Baixo risco</div>
<div>🟡 Risco moderado</div>
<div>🔴 Alto risco</div>

</div>

<br>

<p>
⚠️ Este ranking é apenas informativo e não constitui recomendação de investimento.
</p>

</div>

</details>

<br>

<!-- FIX ACESSIBILIDADE: tabela com caption e scope nos th -->
<table role="grid" aria-label="Tabela de ranking de ações">

<caption style="text-align:left;font-size:13px;color:#cbd5e1;margin-bottom:8px;caption-side:top;">
  Ranking das ações mais descontadas — clique no cabeçalho para ordenar
</caption>

<thead>
<tr>
<th scope="col" onclick="ordenarTabela(0)" aria-sort="none">Ticker ↕</th>
<th scope="col" onclick="ordenarTabela(1)" aria-sort="none">Setor ↕</th>
<th scope="col" onclick="ordenarTabela(2)" aria-sort="none">Categoria ↕</th>
<th scope="col" onclick="ordenarTabela(3)" aria-sort="none">P/L ↕</th>
<th scope="col" onclick="ordenarTabela(4)" aria-sort="none">P/VP ↕</th>
<th scope="col" onclick="ordenarTabela(5)" aria-sort="none">ROE ↕</th>
<th scope="col" onclick="ordenarTabela(6)" aria-sort="none">DY ↕</th>
<th scope="col" onclick="ordenarTabela(7)" aria-sort="none">Score ↕</th>
<th scope="col" onclick="ordenarTabela(8)" aria-sort="none">Desconto % ↕</th>
<th scope="col" onclick="ordenarTabela(9)" aria-sort="none">Preço Justo ↕</th>
<th scope="col">Risco</th>
</tr>
</thead>

<tbody>
"""

for i, (_, row) in enumerate(df.iterrows(), start=1):

    roe = round((row["ROE"] or 0) * 100, 2)
    dy = round((row["DivYield"] or 0) * 100, 2)
    desconto = round(row["Desconto_%"], 2)
    medalhas = ["🥇", "🥈", "🥉"]
    icone = medalhas[i-1] if i <= 3 else ""

    tag = ""
    if row["DivYield"] > 0.08:
        tag = '<span style="background:#22c55e20;color:#22c55e;padding:2px 8px;border-radius:6px;font-size:11px;margin-left:6px;">ALTO DY</span>'

    # FIX ACESSIBILIDADE: tr clicável com tabindex e onkeypress para teclado
    html += f"""
<tr onclick="window.location='acoes/{row['Ticker']}.html'"
    tabindex="0"
    onkeypress="if(event.key==='Enter') window.location='acoes/{row['Ticker']}.html'"
    aria-label="Ver análise de {row['Empresa']} ({row['Ticker']})"
    data-setor="{row['Setor']}"
    data-categoria="{row['Categoria']}"
    data-score="{row['Score']}"
    data-variacao="{row['Variacao_%']}">

<td>
<span style="color:#cbd5e1;font-size:12px">#{i} {icone}</span>
<div style="display:flex;align-items:center;gap:8px">
<!-- FIX ACESSIBILIDADE: alt descritivo em todas as logos -->
<img src="logos/{row['Ticker']}.png"
     alt="Logo {row['Empresa']}"
     onerror="this.onerror=null;this.src='logos/default.svg';"
     style="width:20px;height:20px;object-fit:contain">
<a class="ticker" href="acoes/{row['Ticker']}.html" aria-label="Ver análise completa de {row['Empresa']}">
{row['Ticker']}
</a>
</div>
<span class="empresa">{row['Empresa']} {tag}</span>
</td>

<td>{row['Setor']}</td>

<td>
<span class="badge" style="
background:{cores_categoria.get(row['Categoria'], '#3b82f6')}20;
color:{cores_categoria.get(row['Categoria'], '#3b82f6')};
border:1px solid {cores_categoria.get(row['Categoria'], '#3b82f6')}">
{row['Categoria']}
</span>
</td>

<td>{round(row['PL'],2)}</td>
<td>{round(row['PVP'],2)}</td>
<td>{roe}%</td>
<td>{dy}%</td>

<td style="font-weight:600;color:{'#22c55e' if row['Score'] >= 70 else '#eab308'}">
{row['Score']}
</td>

<td>
<span style="font-size:15px;font-weight:700;color:{'#22c55e' if desconto > 0 else '#ef4444'}">
{desconto}%
</span>
</td>

<td>R$ {round(row["PrecoJusto"],2)}</td>

<!-- FIX ACESSIBILIDADE: farol com texto alternativo via aria-label -->
<td style="text-align:center;" aria-label="Risco: {row['Risco']}">
<span style="font-size:18px;display:inline-block;" title="{row['Risco']}">
{row["Farol"]}
</span>
</td>

</tr>
"""

html += f"""
</tbody>
</table>

</div>

<!-- EDUCAÇÃO -->
<div class="card" role="region" aria-label="Conteúdo educativo">
<h2>📚 Aprenda análise fundamentalista</h2>
<p>Se você quer entender melhor como avaliamos as empresas, veja nossos guias:</p>
<nav aria-label="Guias educativos" class="menu">
<a href="missao.html">Nossa missão</a>
<a href="fundamentalista.html">O que é análise fundamentalista</a>
<a href="pl.html">O que é P/L</a>
<a href="roe.html">O que é ROE</a>
<a href="dividend-yield.html">O que é Dividend Yield</a>
</nav>
</div>

</main>

<footer>
<div class="footer">
⚠️ Este ranking utiliza dados públicos do Yahoo Finance e aplica critérios quantitativos próprios. Não constitui recomendação de investimento.<br>
<a href="ranking.csv" aria-label="Baixar ranking completo em CSV">Baixar CSV</a>
</div>

<div class="footer">
<nav aria-label="Links institucionais" class="footer-links">
<a href="privacidade.html">Privacidade</a>
<a href="termos.html">Termos</a>
<a href="cookies.html">Cookies</a>
<a href="sobre.html">Sobre</a>
<a href="contato.html">Contato</a>
</nav>
<div class="footer-copy">© Tá no Precinho, 2026 — Todos os direitos reservados.</div>
</div>
</footer>

<!-- BANNER DE COOKIES -->
<div id="cookie-banner" role="dialog" aria-label="Aviso de cookies" aria-modal="true">
<div class="cookie-box">
<p>
Utilizamos cookies para melhorar sua experiência, analisar tráfego e exibir anúncios.
Ao continuar navegando você concorda com nossa
<a href="/cookies.html">Política de Cookies</a>.
</p>
<div class="cookie-buttons">
<button onclick="aceitarCookies()" class="cookie-accept" aria-label="Aceitar cookies">Aceitar</button>
<button onclick="recusarCookies()" class="cookie-reject" aria-label="Recusar cookies">Recusar</button>
</div>
</div>
</div>

</div>

</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Site atualizado com melhorias de acessibilidade.")
