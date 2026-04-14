import yfinance as yf
import pandas as pd
import time
import os
import datetime
import tqdm
import random
import re
import unicodedata
import json
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
# GERAR SLUG  ← movida para cima para evitar referência antes da definição
# =========================

def gerar_slug(nome_empresa, ticker):
    try:
        nome = unicodedata.normalize('NFKD', nome_empresa).encode('ascii', 'ignore').decode('utf-8')
        nome = nome.lower()
        nome = re.sub(r'[^a-z0-9]+', '-', nome)
        nome = nome.strip('-')
        return f"{nome}-{ticker.lower()}"
    except Exception:
        return ticker.lower()


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

if "Ticker" not in df.columns:
    print("⚠️ ERRO: coluna 'Ticker' não encontrada")
    print("Colunas disponíveis:", df.columns)
    exit()

if df.empty:
    print("⚠️ Nenhum dado coletado. Verifique a API / scraping.")
    exit()

if "Ticker" not in df.columns:
    print("⚠️ Coluna 'Ticker' não encontrada.")
    print(df.head())
    exit()

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

total_acoes = len(df)
pagadoras_div = len(df[df["DivYield"] > 0])
score_alto = len(df[df["Score"] >= 70])

print("Empresas após filtros:", len(df))
print(f"{len(df)} empresas válidas encontradas.")

# =========================
# JSON PARA GRÁFICOS
# =========================

top10     = df.head(5)
top_blue  = df[df["Categoria"] == "Blue Chips"].sort_values("Desconto_%", ascending=False).head(5)
top_mid   = df[df["Categoria"] == "Mid Caps"].sort_values("Desconto_%", ascending=False).head(5)
top_small = df[df["Categoria"] == "Small Caps"].sort_values("Desconto_%", ascending=False).head(5)

def to_json(df_base):
    return json.dumps([
        {
            "ticker":  row["Ticker"],
            "empresa": row["Empresa"],
            "desconto": round(row["Desconto_%"], 1)
        }
        for _, row in df_base.iterrows()
    ])

top10_json      = to_json(top10)
top_blue_json   = to_json(top_blue)
top_mid_json    = to_json(top_mid)
top_small_json  = to_json(top_small)


# =========================
# GERAR SITEMAP
# =========================

def gerar_sitemap(df):
    base_url = "https://tanoprecinho.site"
    urls = []

    def add(loc, freq="daily", pri="0.7"):
        urls.append(f"  <url><loc>{loc}</loc><changefreq>{freq}</changefreq><priority>{pri}</priority></url>")

    add(f"{base_url}/", "daily", "1.0")

    for p, freq, pri in [
        ("missao.html",          "monthly", "0.7"),
        ("fundamentalista.html", "monthly", "0.7"),
        ("pl.html",              "monthly", "0.7"),
        ("roe.html",             "monthly", "0.7"),
        ("dividend-yield.html",  "monthly", "0.7"),
        ("investidor.html",      "monthly", "0.5"),
        ("privacidade.html",     "monthly", "0.3"),
        ("termos.html",          "monthly", "0.3"),
        ("cookies.html",         "monthly", "0.3"),
        ("sobre.html",           "monthly", "0.4"),
        ("contato.html",         "monthly", "0.4"),
    ]:
        add(f"{base_url}/{p}", freq, pri)

    for p in [
        "seo/melhores-acoes-para-investir.html",
        "seo/acoes-maior-dividend-yield.html",
        "seo/acoes-maior-roe.html",
        "seo/acoes-mais-seguras.html",
        "seo/acoes-dividendos-mensais.html",
        "seo/melhores-acoes-dividendos.html",
        "seo/acoes-baratas-2026.html",
    ]:
        add(f"{base_url}/{p}", "daily", "0.9")

    seen = set()
    for _, row in df.iterrows():
        ticker = row["Ticker"]
        if ticker in seen:
            continue
        seen.add(ticker)
        slug = gerar_slug(row["Empresa"], ticker)
        add(f"{base_url}/acoes/{ticker}.html",              "daily",  "0.8")
        add(f"{base_url}/seo/vale-a-pena-{slug}.html",     "weekly", "0.7")
        add(f"{base_url}/seo/{slug}-ta-barato.html",       "weekly", "0.7")
        add(f"{base_url}/seo/{slug}-paga-dividendos.html", "weekly", "0.7")

    header = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    footer = '\n</urlset>\n'
    sitemap = header + "\n".join(urls) + footer

    with open("docs/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap)

    print(f"Sitemap gerado com {len(urls)} URLs unicas.")


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
# TEMPLATES
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
    url = f"https://tanoprecinho.site/{nome}.html"
    html = _aplicar_template(nome, titulo, conteudo, descricao, keywords, url)
    with open(f"docs/{nome}.html", "w", encoding="utf-8") as f:
        f.write(html)

def gerar_pagina(nome, titulo, conteudo, descricao="", keywords=""):
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
<a href="/index" style="color:#3b82f6">← Voltar ao ranking</a>
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
<h2>🔢 Como o Score é calculado</h2>
<p>O Score vai de 0 a 100 e é composto por critérios objetivos:</p>
<ul>
<li><strong>P/L baixo</strong> — quanto menor, maior a pontuação</li>
<li><strong>P/VP baixo</strong> — empresa negociada abaixo do patrimônio recebe mais pontos</li>
<li><strong>ROE alto</strong> — empresas mais eficientes pontuam mais</li>
<li><strong>Dividend Yield alto</strong> — bom pagamento de dividendos contribui positivamente</li>
<li><strong>Desconto em relação ao preço justo</strong> — quanto maior o desconto, maior o Score</li>
</ul>
<p>O Score final combina esses fatores com pesos específicos por setor.</p>
<hr style="margin:25px 0;border:1px solid #243247;">
<h2>🔎 Transparência</h2>
<p>Todas as análises são baseadas em critérios quantitativos e regras pré-definidas. Não há interferência manual nos rankings.</p>
<hr style="margin:25px 0;border:1px solid #243247;">
<h2>⚠️ Aviso importante</h2>
<p>Este site tem caráter exclusivamente informativo e educacional. <strong>Não constitui recomendação de compra ou venda de ativos.</strong></p>
<br>
<a href="index.html" style="color:#3b82f6">← Voltar ao ranking</a>
</div>
""",
    descricao="Conheça a missão do Tá no Precinho e como analisamos ações da bolsa de forma simples e transparente.",
    keywords="missão, análise de ações, bolsa brasileira, investimentos, educação financeira"
)

gerar_pagina_raiz(
    "pvp",
    "O que é P/VP",
    """
<div style="max-width:700px;margin:auto">
<h2>🏦 O que é P/VP?</h2>
<p>O indicador <strong>P/VP</strong> significa <strong>Preço sobre Valor Patrimonial</strong>. Indica se a ação está sendo negociada acima, abaixo ou próxima do valor contábil da empresa.</p>
<hr style="margin:25px 0;border:1px solid #243247;">
<h3>📊 Como interpretar o P/VP</h3>
<ul>
<li><strong>P/VP &lt; 1</strong> → A ação pode estar barata</li>
<li><strong>P/VP = 1</strong> → Preço próximo ao valor patrimonial</li>
<li><strong>P/VP &gt; 1</strong> → O mercado paga prêmio pela empresa</li>
</ul>
<hr style="margin:25px 0;border:1px solid #243247;">
<h3>⚠️ Cuidados ao usar o P/VP</h3>
<ul>
<li>Bancos e seguradoras → P/VP é muito relevante</li>
<li>Empresas de tecnologia → menos relevante</li>
<li>Empresas com prejuízo → pode distorcer análise</li>
</ul>
<hr style="margin:25px 0;border:1px solid #243247;">
<h3>⚠️ Aviso importante</h3>
<p>Este conteúdo é educativo e <strong>não constitui recomendação de investimento</strong>.</p>
<br>
<a href="index.html" style="color:#3b82f6">← Voltar ao ranking</a>
</div>
""",
    descricao="Entenda o que é P/VP (Preço sobre Valor Patrimonial), como interpretar e quando usar esse indicador.",
    keywords="PVP, preço sobre valor patrimonial, análise fundamentalista, ações baratas, valuation"
)

gerar_pagina_raiz(
    "on-pn",
    "Diferença entre ações ON e PN",
    """
<div style="max-width:700px;margin:auto">
<h2>📊 Diferença entre ações ON e PN</h2>
<p>Na bolsa brasileira, as ações podem ser classificadas em <strong>ON (Ordinárias)</strong> e <strong>PN (Preferenciais)</strong>.</p>
<hr style="margin:25px 0;border:1px solid #243247;">
<h3>🗳️ Ações ON (Ordinárias)</h3>
<ul>
<li>✔️ Direito a voto em assembleias</li>
<li>✔️ Tag along (proteção em caso de venda da empresa)</li>
</ul>
<p>Exemplo: PETR3, VALE3, ITUB3</p>
<hr style="margin:25px 0;border:1px solid #243247;">
<h3>💰 Ações PN (Preferenciais)</h3>
<ul>
<li>✔️ Prioridade no recebimento de dividendos</li>
<li>✔️ Geralmente mais líquidas no mercado</li>
</ul>
<p>Exemplo: PETR4, ITUB4, BBDC4</p>
<hr style="margin:25px 0;border:1px solid #243247;">
<h3>⚠️ Aviso importante</h3>
<p>Este conteúdo é educativo e <strong>não constitui recomendação de investimento</strong>.</p>
<br>
<a href="index.html" style="color:#3b82f6">← Voltar ao ranking</a>
</div>
""",
    descricao="Entenda a diferença entre ações ON e PN, direitos de voto, dividendos e qual escolher.",
    keywords="ações ON e PN, diferença ON PN, ações ordinárias e preferenciais"
)

gerar_pagina_raiz(
    "estrategia-investidor",
    "Estratégias para investir melhor em ações (2026)",
    """
<div style="max-width:800px;margin:auto">

<h1>📈 Como investir melhor em ações (estratégias reais)</h1>

<p>Investir bem não é sobre acertar a próxima ação que vai subir 100%.</p>
<p>É sobre <strong>eficiência</strong>: pagar menos imposto, errar menos e deixar o tempo trabalhar para você.</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h2>💰 1. O segredo: retorno líquido (não bruto)</h2>

<p>A maioria dos investidores foca só em retorno. Os melhores focam em:</p>

<ul>
<li>Impostos</li>
<li>Custos</li>
<li>Frequência de operações</li>
</ul>

<p>Pequenas melhorias aqui podem aumentar muito seu resultado no longo prazo.</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h2>🧾 2. Como pagar menos imposto (legalmente)</h2>

<h3>📌 Isenção de até R$ 20 mil/mês</h3>
<p>Se você vender até <strong>R$ 20.000 por mês em ações</strong>, você não paga imposto.</p>

<p><strong>Estratégia:</strong></p>
<ul>
<li>Evite vender tudo de uma vez</li>
<li>Divida vendas ao longo dos meses</li>
</ul>

<h3>📌 Compensação de prejuízo</h3>
<p>Se você teve prejuízo, pode usar isso para pagar menos imposto no futuro.</p>

<p><strong>Estratégia:</strong></p>
<ul>
<li>Realizar prejuízos de forma inteligente</li>
<li>Abater lucros futuros</li>
</ul>

<h3>📌 Dividendos</h3>
<p>Dividendos continuam sendo uma forma eficiente de gerar renda.</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h2>📊 3. Como comprar melhor</h2>

<h3>✔️ Nunca compre tudo de uma vez</h3>
<p>Compre aos poucos (preço médio).</p>

<h3>✔️ Use quedas a seu favor</h3>
<ul>
<li>Queda de 10% → compra leve</li>
<li>Queda de 20% → compra média</li>
<li>Queda de 30% → compra forte</li>
</ul>

<h3>✔️ Foque em poucas empresas boas</h3>
<p>5 a 12 boas ações são melhores do que 30 aleatórias.</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h2>🔄 4. Quando vender uma ação?</h2>

<p>Você não vende porque subiu ou caiu.</p>

<p>Você vende quando:</p>
<ul>
<li>A empresa piorou</li>
<li>A tese deixou de fazer sentido</li>
<li>Existe uma oportunidade melhor</li>
</ul>

<hr style="margin:25px 0;border:1px solid #243247;">

<h2>⚙️ 5. Estrutura inteligente (nível profissional)</h2>

<p>Organize sua carteira como um investidor profissional:</p>

<ul>
<li><strong>Core</strong> → longo prazo (não mexe)</li>
<li><strong>Oportunidades</strong> → onde você gira mais</li>
<li><strong>Renda</strong> → dividendos</li>
</ul>

<hr style="margin:25px 0;border:1px solid #243247;">

<h2>🧠 6. O que destrói seu resultado</h2>

<ul>
<li>Comprar no topo</li>
<li>Vender no pânico</li>
<li>Girar demais a carteira</li>
<li>Seguir hype</li>
</ul>

<h2>🚀 O que funciona de verdade</h2>

<ul>
<li>Consistência</li>
<li>Longo prazo</li>
<li>Reinvestimento</li>
<li>Disciplina</li>
</ul>

<hr style="margin:25px 0;border:1px solid #243247;">

<h2>📦 7. Estratégia simples (modelo pronto)</h2>

<p>Uma estratégia eficiente para a maioria dos investidores:</p>

<ul>
<li>60% → ações de qualidade (longo prazo)</li>
<li>20% → dividendos</li>
<li>20% → oportunidades</li>
</ul>

<p><strong>Regras:</strong></p>
<ul>
<li>Aportar todo mês</li>
<li>Reinvestir dividendos</li>
<li>Evitar giro excessivo</li>
<li>Revisar carteira a cada 3 meses</li>
</ul>

<hr style="margin:25px 0;border:1px solid #243247;">

<h2>⚠️ Aviso importante</h2>
<p>Este conteúdo é educativo e <strong>não constitui recomendação de investimento</strong>.</p>

<br>

<a href="index.html" style="color:#3b82f6">← Ver ranking de ações</a>

</div>
""",
    descricao="Aprenda estratégias para investir melhor em ações, pagar menos imposto e aumentar sua eficiência como investidor.",
    keywords="como investir melhor, estratégias ações, pagar menos imposto bolsa, investir 2026"
)



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
        f"análise {ticker}, dividendos {ticker}, vale a pena {ticker} 2026"
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
<p>O P/VP de <strong>{pvp}</strong> {'indica que a empresa negocia abaixo do valor patrimonial — sinal positivo para value investing.' if pvp < 1 else 'mostra que o mercado precifica a empresa acima do patrimônio líquido.'}</p>
</div>

<div class="card">
<h2>{ticker} paga bons dividendos?</h2>
<p>{avaliacao_dy}</p>
<p>{avaliacao_roe}</p>
</div>

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


def gerar_paginas_seo_ticker(row):
    ticker   = row["Ticker"]
    empresa  = limpar_nome_empresa(row["Empresa"])
    setor    = row["Setor"]
    slug     = gerar_slug(empresa, ticker)
    desconto = round(row["Desconto_%"], 2)
    pl       = round(row["PL"], 2)
    pvp      = round(row["PVP"], 2)
    roe      = round(row["ROE"] * 100, 2)
    dy       = round(row["DivYield"] * 100, 2)
    pjusto   = round(row["PrecoJusto"], 2)

    with open("docs/layout_base.html", "r", encoding="utf-8") as f:
        template = f.read()

    # PÁGINA 1: vale-a-pena
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
<p>O score fundamentalista atual é de <strong>{row["Score"]}/100</strong>.</p>
</div>
<div class="card">
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
<p>{"Com desconto de " + str(desconto) + "% em relação ao preço justo, existe potencial de valorização." if desconto > 10 else "A ação negocia próxima ou acima do preço justo estimado."}</p>
<p>⚠️ Esta análise é informativa e não constitui recomendação de investimento.</p>
</div>
<div class="card">
<ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:8px;">
  <li><a href="/acoes/{ticker}.html">📊 Análise completa de {ticker}</a></li>
  <li><a href="/seo/{slug}-ta-barato.html">💸 {ticker} está barata? Análise de valuation</a></li>
  <li><a href="/seo/{slug}-paga-dividendos.html">💰 {ticker} paga bons dividendos?</a></li>
</ul>
</div>
</div>"""

    html1 = template.replace("{{titulo}}", titulo1).replace("{{conteudo}}", conteudo1) \
                    .replace("{{descricao}}", desc1).replace("{{keywords}}", f"{ticker}, vale a pena {ticker}, {empresa} 2026") \
                    .replace("{{url}}", f"https://tanoprecinho.site/seo/{nome1}.html")
    with open(f"docs/seo/{nome1}.html", "w", encoding="utf-8") as f:
        f.write(html1)

    # PÁGINA 2: ta-barato
    nome2   = f"{slug}-ta-barato"
    titulo2 = f"{empresa} ({ticker}) está barata? Análise de valuation 2026"
    desc2   = f"Veja se {ticker} está barata: P/L {pl}, P/VP {pvp} e preço justo estimado em R$ {pjusto}. Atualizado hoje."
    schema2 = f"""<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article","headline":"{titulo2}",
"author":{{"@type":"Organization","name":"Tá no Precinho"}},
"dateModified":"{datetime.date.today().isoformat()}"}}
</script>"""

    if pl < 8:
        conclusao_pl = f"Um P/L de {pl} é considerado baixo — potencial sinal de subvalorização."
    elif pl < 15:
        conclusao_pl = f"Um P/L de {pl} é razoável para o setor de {setor}."
    else:
        conclusao_pl = f"Um P/L de {pl} está acima do múltiplo conservador de 15x."

    conteudo2 = f"""
{schema2}
<div style="max-width:780px;margin:auto">
<a href="/index.html" style="color:#94a3b8;font-size:13px;">← Ranking completo</a>
<div class="card" style="text-align:center;margin:16px 0">
<img src="../logos/{ticker}.png" alt="Logo {empresa}" loading="lazy"
     onerror="this.onerror=null;this.src='../logos/default.svg';"
     style="width:44px;height:44px;margin-bottom:8px">
<h1 style="margin:0;font-size:21px">{titulo2}</h1>
</div>
<div class="card">
<h2>Preço justo de {ticker}</h2>
<p>Preço justo estimado (P/L 15x): <strong>R$ {pjusto}</strong>.</p>
<p>{"Desconto atual de " + str(desconto) + "%." if desconto > 0 else "Ação negociando acima do preço justo estimado."}</p>
</div>
<div class="card">
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
</div>
<div class="card">
<p>⚠️ Esta análise é exclusivamente informativa e <strong>não constitui recomendação de investimento</strong>.</p>
</div>
<div class="card">
<ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:8px;">
  <li><a href="/acoes/{ticker}.html">📊 Análise completa de {ticker}</a></li>
  <li><a href="/seo/vale-a-pena-{slug}.html">🤔 Vale a pena investir em {empresa}?</a></li>
  <li><a href="/seo/{slug}-paga-dividendos.html">💰 {ticker} paga bons dividendos?</a></li>
</ul>
</div>
</div>"""

    html2 = template.replace("{{titulo}}", titulo2).replace("{{conteudo}}", conteudo2) \
                    .replace("{{descricao}}", desc2).replace("{{keywords}}", f"{ticker} está barata, valuation {ticker}, preço justo {ticker}") \
                    .replace("{{url}}", f"https://tanoprecinho.site/seo/{nome2}.html")
    with open(f"docs/seo/{nome2}.html", "w", encoding="utf-8") as f:
        f.write(html2)

    # PÁGINA 3: paga-dividendos
    nome3   = f"{slug}-paga-dividendos"
    titulo3 = f"{empresa} ({ticker}) paga bons dividendos em 2026?"
    desc3   = f"{ticker} tem Dividend Yield de {dy}% e ROE de {roe}%. Análise atualizada hoje."
    schema3 = f"""<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article","headline":"{titulo3}",
"author":{{"@type":"Organization","name":"Tá no Precinho"}},
"dateModified":"{datetime.date.today().isoformat()}"}}
</script>"""

    if dy >= 10:
        analise_dy = f"O Dividend Yield de <strong>{dy}%</strong> é muito elevado. {ticker} é uma das melhores pagadoras de dividendos do mercado."
    elif dy >= 6:
        analise_dy = f"O Dividend Yield de <strong>{dy}%</strong> é alto. Boa opção para quem busca renda passiva."
    elif dy >= 3:
        analise_dy = f"O Dividend Yield de <strong>{dy}%</strong> é moderado."
    else:
        analise_dy = f"O Dividend Yield de <strong>{dy}%</strong> é baixo. O foco da empresa parece ser crescimento."

    conteudo3 = f"""
{schema3}
<div style="max-width:780px;margin:auto">
<a href="/index.html" style="color:#94a3b8;font-size:13px;">← Ranking completo</a>
<div class="card" style="text-align:center;margin:16px 0">
<img src="../logos/{ticker}.png" alt="Logo {empresa}" loading="lazy"
     onerror="this.onerror=null;this.src='../logos/default.svg';"
     style="width:44px;height:44px;margin-bottom:8px">
<h1 style="margin:0;font-size:21px">{titulo3}</h1>
</div>
<div class="card">
<h2>Dividend Yield de {ticker}</h2>
<p>{analise_dy}</p>
</div>
<div class="card">
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;">
{gerar_metric("Dividend Yield", f"{dy}%")}
{gerar_metric("ROE", f"{roe}%")}
{gerar_metric("P/L", pl)}
{gerar_metric("Score", row["Score"])}
</div>
</div>
<div class="card">
<p>⚠️ Análise informativa. <strong>Não constitui recomendação de investimento.</strong></p>
</div>
<div class="card">
<ul style="list-style:none;padding:0;display:flex;flex-direction:column;gap:8px;">
  <li><a href="/acoes/{ticker}.html">📊 Análise completa de {ticker}</a></li>
  <li><a href="/seo/vale-a-pena-{slug}.html">🤔 Vale a pena investir em {empresa}?</a></li>
  <li><a href="/seo/{slug}-ta-barato.html">💸 {ticker} está barata? Valuation</a></li>
</ul>
</div>
</div>"""

    html3 = template.replace("{{titulo}}", titulo3).replace("{{conteudo}}", conteudo3) \
                    .replace("{{descricao}}", desc3).replace("{{keywords}}", f"{ticker} dividendos, dividend yield {ticker}") \
                    .replace("{{url}}", f"https://tanoprecinho.site/seo/{nome3}.html")
    with open(f"docs/seo/{nome3}.html", "w", encoding="utf-8") as f:
        f.write(html3)


# =========================
# GERAR PÁGINAS DE RANKING
# =========================

def gerar_paginas_ranking(df):

    top_div = df.sort_values("DivYield", ascending=False).head(20)
    lista_div = "".join([
        f"""
        <div style="background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);padding:14px;border-radius:12px;display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
        <div style="display:flex;align-items:center;gap:10px">
        <img src="../logos/{row['Ticker']}.png" alt="Logo {row['Empresa']}" loading="lazy"
             onerror="this.onerror=null;this.src='../logos/default.svg';" style="width:28px;height:28px">
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
        <img src="../logos/{row['Ticker']}.png" alt="Logo {row['Empresa']}" loading="lazy"
             onerror="this.onerror=null;this.src='../logos/default.svg';" style="width:28px;height:28px">
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

    # ── Páginas de investidores e livros (dentro da função) ──────────────

    gerar_pagina(
        "investidores",
        "Maiores investidores da bolsa",
        """
<div style="max-width:900px;margin:auto">
<h1>📚 Maiores investidores da bolsa</h1>
<div class="card">
<h2>💰 Aprenda com os melhores</h2>
<div style="display:flex;flex-direction:column;gap:10px;">
<a href="barsi-dividendos.html" style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px;background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);border-radius:10px;text-decoration:none;color:#e2e8f0;">
<span>💸 Luiz Barsi</span><span style="font-size:12px;color:#94a3b8;">Dividendos</span></a>
<a href="warren-buffett.html" style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px;background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);border-radius:10px;text-decoration:none;color:#e2e8f0;">
<span>💰 Warren Buffett</span><span style="font-size:12px;color:#94a3b8;">Value Investing</span></a>
<a href="benjamin-graham.html" style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px;background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);border-radius:10px;text-decoration:none;color:#e2e8f0;">
<span>📘 Benjamin Graham</span><span style="font-size:12px;color:#94a3b8;">Fundamentos</span></a>
<a href="peter-lynch.html" style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px;background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);border-radius:10px;text-decoration:none;color:#e2e8f0;">
<span>📈 Peter Lynch</span><span style="font-size:12px;color:#94a3b8;">Crescimento</span></a>
</div>
</div>
</div>

<div class="card">
<h2>O Básico de todo investidor</h2>
<nav class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>
</div>

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
<a href="seo/comparar.html">↔️ Comparar Ações</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>
""",
        descricao="Conheça os maiores investidores da bolsa e aprenda suas estratégias.",
        keywords="maiores investidores, luiz barsi, warren buffett, value investing"
    )

    gerar_pagina(
        "barsi-dividendos",
        "Como Luiz Barsi ficou bilionário com dividendos",
        """
<div style="max-width:900px;margin:auto">
<div class="card">
<h2>🇧🇷 Luiz Barsi — o investidor dos dividendos</h2>
<p>Luiz Barsi é considerado o maior investidor pessoa física do Brasil. Sua estratégia é simples: viver de dividendos.</p>
<p>Ao longo de décadas, Barsi construiu patrimônio investindo em empresas sólidas com foco em geração de caixa.</p>
</div>
<div class="card">
<h2>📈 A estratégia de Barsi</h2>
<ul>
<li>Foco em dividendos consistentes</li>
<li>Compra de empresas sólidas</li>
<li>Visão de longo prazo</li>
<li>Reinvestimento dos dividendos</li>
</ul>
</div>
<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">
<h2>📚 Quer aprender direto com ele?</h2>
<a href="https://amzn.to/47rV2Vj" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro recomendado</a>
<p style="font-size:12px;color:#94a3b8;margin-top:10px">*Link de afiliado</p>
</div>
<div class="card"><a href="../index.html">📊 Ver ranking de ações →</a></div>
<div class="card">
<h2>O Básico de todo investidor</h2>
<nav class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>
</div>

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
<a href="seo/comparar.html">↔️ Comparar Ações</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>
""",
        descricao="Aprenda como Luiz Barsi ficou bilionário investindo em dividendos.",
        keywords="luiz barsi, dividendos, renda passiva, investir em ações"
    )

    gerar_pagina(
        "warren-buffett",
        "Como Warren Buffett ficou bilionário investindo",
        """
<div style="max-width:900px;margin:auto">
<div class="card">
<h2>💰 Warren Buffett — o maior investidor do mundo</h2>
<p>Warren Buffett construiu sua fortuna aplicando os princípios do value investing.</p>
<p>Ele busca empresas sólidas com vantagem competitiva, comprando apenas quando estão abaixo do valor justo.</p>
</div>
<div class="card">
<h2>🧠 Filosofia de investimento</h2>
<ul>
<li>Comprar empresas com vantagem competitiva</li>
<li>Pensar no longo prazo</li>
<li>Evitar especulação</li>
<li>Investir no que entende</li>
</ul>
</div>
<div class="card">
<h2>📚 Quer aprender direto com ele?</h2>
<a href="https://amzn.to/4uT0Lh0" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro do Warren Buffett</a>
</div>
<div class="card"><a href="../index.html">← Ver ranking de ações</a></div>
<div class="card">
<h2>O Básico de todo investidor</h2>
<nav class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>
</div>

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
<a href="seo/comparar.html">↔️ Comparar Ações</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>
""",
        descricao="Conheça a estratégia de Warren Buffett.",
        keywords="warren buffett, value investing, melhores investidores"
    )

    gerar_pagina(
        "benjamin-graham",
        "Benjamin Graham — pai do value investing",
        """
<div style="max-width:900px;margin:auto">
<div class="card">
<h2>📘 Benjamin Graham — pai do value investing</h2>
<p>Benjamin Graham foi o criador da análise fundamentalista moderna e mentor de Warren Buffett.</p>
<p>Ele desenvolveu o conceito de comprar ações abaixo do valor justo, utilizando uma margem de segurança.</p>
</div>
<div class="card">
<h2>🧠 Princípios fundamentais</h2>
<ul>
<li>Comprar com margem de segurança</li>
<li>Focar no valor, não no preço</li>
<li>Ignorar emoções do mercado</li>
<li>Investir com disciplina</li>
</ul>
</div>
<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">
<h2>📚 Quer aprender direto com ele?</h2>
<a href="https://amzn.to/4bMAYOV" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro do Benjamin Graham</a>
</div>
<div class="card"><a href="../index.html">📊 Ver ações baratas agora →</a></div>
<div class="card">
<h2>O Básico de todo investidor</h2>
<nav class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>
</div>

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
<a href="seo/comparar.html">↔️ Comparar Ações</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>
""",
        descricao="Conheça Benjamin Graham e o conceito de value investing.",
        keywords="benjamin graham, value investing, investir em valor"
    )

    gerar_pagina(
        "peter-lynch",
        "Peter Lynch — investir no que você conhece",
        """
<div style="max-width:900px;margin:auto">
<div class="card">
<h2>📈 Peter Lynch — investir no que você conhece</h2>
<p>Peter Lynch ficou famoso por mostrar que qualquer pessoa pode investir bem observando o mundo ao seu redor.</p>
</div>
<div class="card">
<h2>🧠 Filosofia</h2>
<ul>
<li>Invista no que você conhece</li>
<li>Observe o dia a dia</li>
<li>Busque empresas em crescimento</li>
<li>Pense no longo prazo</li>
</ul>
</div>
<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">
<h2>📚 Quer aprender direto com ele?</h2>
<a href="https://amzn.to/47rVy5H" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro do Peter Lynch</a>
</div>
<div class="card"><a href="../index.html">📊 Ver ranking de ações →</a></div>
<div class="card">
<h2>O Básico de todo investidor</h2>
<nav class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>
</div>

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
<a href="seo/comparar.html">↔️ Comparar Ações</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>
""",
        descricao="Conheça a estratégia de Peter Lynch.",
        keywords="peter lynch, investir no que conhece, ações crescimento"
    )

    gerar_pagina(
        "pai-rico-pai-pobre",
        "Pai Rico, Pai Pobre — lições financeiras",
        """
<div style="max-width:900px;margin:auto">
<h1>💰 Pai Rico, Pai Pobre</h1>
<div class="card">
<h2>🧠 Principais ensinamentos</h2>
<ul>
<li>Ativos colocam dinheiro no bolso</li>
<li>Passivos tiram dinheiro do bolso</li>
<li>Trabalhe para aprender, não só para ganhar</li>
<li>Construa renda passiva</li>
</ul>
</div>
<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">
<h2>📚 Comece por aqui</h2>
<a href="https://amzn.to/3Pte87v" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro</a>
</div>
<div class="card"><a href="../index.html">📊 Ver ações para investir →</a></div>
</div>

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
<a href="seo/comparar.html">↔️ Comparar Ações</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>
""",
        descricao="Resumo do livro Pai Rico, Pai Pobre.",
        keywords="pai rico pai pobre resumo, educação financeira"
    )

    gerar_pagina(
        "homem-mais-rico-babilonia",
        "O Homem Mais Rico da Babilônia — princípios financeiros",
        """
<div style="max-width:900px;margin:auto">
<h1>🏺 O Homem Mais Rico da Babilônia</h1>
<div class="card">
<h2>💰 Regras clássicas</h2>
<ul>
<li>Pague a si mesmo primeiro</li>
<li>Controle seus gastos</li>
<li>Faça seu dinheiro trabalhar</li>
<li>Proteja seu patrimônio</li>
</ul>
</div>
<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">
<h2>📚 Leitura essencial</h2>
<a href="https://amzn.to/4dKRSjp" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro</a>
</div>
<div class="card"><a href="../index.html">📊 Ver oportunidades na bolsa →</a></div>
</div>

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
<a href="seo/comparar.html">↔️ Comparar Ações</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>
""",
        descricao="Aprenda os princípios do Homem Mais Rico da Babilônia.",
        keywords="homem mais rico da babilonia resumo"
    )

    gerar_pagina(
        "mente-milionaria",
        "Os Segredos da Mente Milionária",
        """
<div style="max-width:900px;margin:auto">
<h1>🧠 Os Segredos da Mente Milionária</h1>
<div class="card">
<h2>🧠 Ideia central</h2>
<p>Seu resultado financeiro é reflexo do seu modelo mental.</p>
</div>
<div class="card">
<h2>💡 Lições principais</h2>
<ul>
<li>Ricos pensam diferente</li>
<li>Assuma responsabilidade financeira</li>
<li>Foque em crescer</li>
<li>Construa ativos</li>
</ul>
</div>
<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">
<h2>📚 Comece a mudar sua mentalidade</h2>
<a href="https://amzn.to/4rW4VSI" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro</a>
</div>
<div class="card"><a href="../index.html">📊 Ver ranking de ações →</a></div>
</div>

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
<a href="seo/comparar.html">↔️ Comparar Ações</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>
""",
        descricao="Aprenda a mentalidade dos ricos.",
        keywords="mente milionaria, educação financeira mentalidade"
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
            <img src="../logos/{row['Ticker']}.png" alt="Logo {row['Empresa']}"
                 onerror="this.onerror=null;this.src='../logos/default.svg';" style="width:28px;height:28px">
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
# GERAR PÁGINA SETOR
# =========================

def gerar_paginas_setores(df):

    for setor in sorted(df["Setor"].dropna().unique()):

        df_setor = df[df["Setor"] == setor] \
            .sort_values("Score", ascending=False) \
            .head(20)

        if df_setor.empty:
            continue

        lista = "".join([
            f"""
            <a href="../acoes/{row['Ticker']}.html" style="text-decoration:none;color:inherit">
            <div style="background:rgba(30,41,59,0.6);
                        border:1px solid rgba(255,255,255,0.05);
                        padding:14px;
                        border-radius:12px;
                        display:flex;
                        align-items:center;
                        justify-content:space-between;
                        margin-bottom:10px;">
                
                <div style="display:flex;align-items:center;gap:10px">
                    <img src="../logos/{row['Ticker']}.png"
                         style="width:28px;height:28px"
                         onerror="this.onerror=null;this.src='../logos/default.svg';">

                    <div>
                        <div style="font-weight:600">{row['Empresa']}</div>
                        <div style="font-size:12px;color:#cbd5e1">
                            {row['Ticker']}
                        </div>
                    </div>
                </div>

                <div style="text-align:right">
                    <div style="color:#22c55e;font-weight:700">
                        {round(row['Score'],0)}
                    </div>
                    <div style="font-size:11px;color:#cbd5e1">
                        Score
                    </div>
                </div>

            </div>
            </a>
            """
            for _, row in df_setor.iterrows()
        ])

        slug_setor = setor.lower().replace(" ", "-")

        gerar_pagina(
            f"melhores-acoes-setor-{slug_setor}",
            f"Melhores ações do setor {setor}",
            f"""
<div class="card">
<h1>🏢 Melhores ações do setor {setor}</h1>
<p style="color:#cbd5e1;font-size:14px">
Ranking atualizado das melhores empresas do setor {setor} com base em análise fundamentalista.
</p>

{lista}

<p style="margin-top:20px;font-size:13px;color:#cbd5e1">
⚠️ Conteúdo educativo. Não constitui recomendação de investimento.
</p>
</div>

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

""",
            descricao=f"Veja as melhores ações do setor {setor} na bolsa brasileira.",
            keywords=f"ações setor {setor}, melhores ações {setor}, investir em {setor}"
        )

# =========================
# GERAR PÁGINA CATEGORIA
# =========================

def gerar_paginas_categorias(df):

    for categoria in sorted(df["Categoria"].dropna().unique()):

        df_cat = df[df["Categoria"] == categoria] \
            .sort_values("Score", ascending=False) \
            .head(20)

        if df_cat.empty:
            continue

        lista = "".join([
            f"""
            <a href="../acoes/{row['Ticker']}.html" style="text-decoration:none;color:inherit">
            <div style="background:rgba(30,41,59,0.6);
                        border:1px solid rgba(255,255,255,0.05);
                        padding:14px;
                        border-radius:12px;
                        display:flex;
                        align-items:center;
                        justify-content:space-between;
                        margin-bottom:10px;">
                
                <div style="display:flex;align-items:center;gap:10px">
                    <img src="../logos/{row['Ticker']}.png"
                         style="width:28px;height:28px"
                         onerror="this.onerror=null;this.src='../logos/default.svg';">

                    <div>
                        <div style="font-weight:600">{row['Empresa']}</div>
                        <div style="font-size:12px;color:#cbd5e1">
                            {row['Ticker']}
                        </div>
                    </div>
                </div>

                <div style="text-align:right">
                    <div style="color:#22c55e;font-weight:700">
                        {round(row['Score'],0)}
                    </div>
                    <div style="font-size:11px;color:#cbd5e1">
                        Score
                    </div>
                </div>

            </div>
            </a>
            """
            for _, row in df_cat.iterrows()
        ])

        slug = categoria.lower().replace(" ", "-")

        gerar_pagina(
            f"melhores-acoes-{slug}",
            f"Melhores ações {categoria}",
            f"""
<div class="card">
<h1>🏆 Melhores ações {categoria}</h1>

<p style="color:#cbd5e1;font-size:14px">
Ranking das melhores {categoria.lower()} da bolsa baseado em Score fundamentalista.
</p>

{lista}

<p style="margin-top:20px;font-size:13px;color:#cbd5e1">
⚠️ Conteúdo educativo. Não constitui recomendação de investimento.
</p>
</div>

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
""",
            descricao=f"Veja as melhores ações {categoria} da bolsa brasileira.",
            keywords=f"{categoria}, melhores {categoria}, ações {categoria}"
        )

# =========================
# GERAR PÁGINA COMPARAR
# =========================

def gerar_comparar(df):
    """Gera docs/seo/comparar.html — ferramenta visual de comparação"""
    import json as _j

    # Médias por setor
    s_df = (df.groupby("Setor")
              .agg(PL=("PL","mean"), PVP=("PVP","mean"), ROE=("ROE","mean"),
                   DivYield=("DivYield","mean"), Desc=("Desconto_%","mean"), Score=("Score","mean"))
              .round(2).reset_index())
    setor_json = _j.dumps([
        {"Setor": r["Setor"], "PL": round(r["PL"],2), "PVP": round(r["PVP"],2),
         "ROE": round(r["ROE"],4), "DivYield": round(r["DivYield"],4),
         "Desconto_%": round(r["Desc"],2), "Score": round(r["Score"],1)}
        for _, r in s_df.iterrows()], ensure_ascii=False)

    # Médias por categoria
    c_df = (df.groupby("Categoria")
              .agg(PL=("PL","mean"), PVP=("PVP","mean"), ROE=("ROE","mean"),
                   DivYield=("DivYield","mean"), Desc=("Desconto_%","mean"), Score=("Score","mean"))
              .round(2).reset_index())
    cat_json = _j.dumps([
        {"Categoria": r["Categoria"], "PL": round(r["PL"],2), "PVP": round(r["PVP"],2),
         "ROE": round(r["ROE"],4), "DivYield": round(r["DivYield"],4),
         "Desconto_%": round(r["Desc"],2), "Score": round(r["Score"],1)}
        for _, r in c_df.iterrows()], ensure_ascii=False)

    # Top 80 ações por score para os selects
    cols = ["Ticker","Empresa","Setor","PL","PVP","ROE","DivYield","Score","Desconto_%"]
    acoes_json = _j.dumps([
        {"Ticker": r["Ticker"], "Empresa": r["Empresa"], "Setor": r["Setor"],
         "PL": round(r["PL"],2), "PVP": round(r["PVP"],2),
         "ROE": round(r["ROE"],4), "DivYield": round(r["DivYield"],4),
         "Score": int(r["Score"]), "Desconto_%": round(r["Desconto_%"],2)}
        for _, r in df.nlargest(80,"Score")[cols].iterrows()], ensure_ascii=False)

    gerar_pagina(
        "comparar",
        "Comparar ações da bolsa brasileira",
        f"""
<style>
/* ── COMPARAR — estilos específicos desta página ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

.cmp-hero{{
  text-align:center;padding:40px 20px 32px;
  background:linear-gradient(145deg,rgba(20,40,80,0.55),rgba(10,20,40,0.4));
  border:1px solid rgba(100,150,220,0.14);border-radius:18px;
  margin-bottom:24px;position:relative;overflow:hidden;
}}
.cmp-hero::before{{
  content:'';position:absolute;top:-40px;right:-40px;width:180px;height:180px;
  background:radial-gradient(circle,rgba(96,165,250,0.09),transparent 70%);
  border-radius:50%;pointer-events:none;
}}
.cmp-hero h2{{
  font-family:'DM Serif Display',serif;font-size:clamp(22px,4vw,34px);
  letter-spacing:-.4px;color:#fff;margin-bottom:10px;
}}
.cmp-hero p{{color:#6b8fad;font-size:14px;max-width:460px;margin:0 auto 20px;}}
.cmp-badges{{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;}}
.cmp-badge{{display:inline-flex;align-items:center;gap:5px;
  background:rgba(17,30,48,0.9);border:1px solid rgba(100,150,220,0.15);
  border-radius:20px;padding:6px 14px;font-size:12px;color:#6b8fad;}}
.cmp-badge strong{{color:#dce8f8;}}

/* Glossário */
.cmp-gloss{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:24px;}}
.cmp-pill{{
  background:rgba(17,30,48,0.9);border:1px solid rgba(100,150,220,0.13);
  border-radius:8px;padding:7px 14px;font-size:12px;color:#6b8fad;
  cursor:pointer;transition:all .18s;position:relative;
}}
.cmp-pill:hover,.cmp-pill:focus{{
  border-color:rgba(96,165,250,0.35);color:#dce8f8;outline:none;
}}
.cmp-tip{{
  display:none;position:absolute;bottom:calc(100% + 8px);left:50%;
  transform:translateX(-50%);background:#1e3a5f;
  border:1px solid rgba(96,165,250,0.25);border-radius:8px;
  padding:10px 14px;width:210px;font-size:12px;color:#dce8f8;
  line-height:1.55;z-index:100;white-space:normal;text-align:left;pointer-events:none;
}}
.cmp-pill:hover .cmp-tip,.cmp-pill:focus .cmp-tip{{display:block;}}

/* Widget compare */
.cmp-widget{{
  background:rgba(17,30,48,0.95);border:1px solid rgba(100,150,220,0.13);
  border-radius:18px;padding:24px;margin-bottom:22px;
  box-shadow:0 8px 36px rgba(0,0,0,0.4);
}}
.cmp-selects{{
  display:grid;grid-template-columns:1fr 48px 1fr;
  align-items:end;gap:12px;margin-bottom:16px;
}}
.cmp-grp{{display:flex;flex-direction:column;gap:6px;}}
.cmp-grp label{{
  font-size:11px;font-weight:600;letter-spacing:1.5px;
  text-transform:uppercase;color:#6b8fad;
}}
.cmp-select{{
  width:100%;padding:10px 36px 10px 12px;
  background:#060d1a;color:#dce8f8;
  border:1px solid rgba(100,150,220,0.16);border-radius:9px;
  font-family:'DM Sans',sans-serif;font-size:13px;cursor:pointer;
  appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='11' height='7' fill='none'%3E%3Cpath d='M1 1l4.5 4.5L10 1' stroke='%236b8fad' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 12px center;
  transition:border-color .18s;
}}
.cmp-select:hover{{border-color:rgba(96,165,250,0.3);}}
.cmp-select:focus{{outline:2px solid #60a5fa;outline-offset:2px;border-color:#60a5fa;}}
.cmp-vs{{
  display:flex;align-items:center;justify-content:center;
  font-family:'DM Serif Display',serif;font-size:16px;font-style:italic;
  color:#60a5fa;background:rgba(96,165,250,0.09);
  border:1px solid rgba(96,165,250,0.2);border-radius:50%;
  width:48px;height:48px;flex-shrink:0;
}}
.cmp-btn{{
  width:100%;padding:13px;background:#60a5fa;color:#000;
  font-family:'DM Sans',sans-serif;font-size:14px;font-weight:700;
  border:none;border-radius:9px;cursor:pointer;transition:all .18s;
}}
.cmp-btn:hover{{background:#93c5fd;transform:translateY(-1px);}}
.cmp-btn:focus{{outline:2px solid #fff;outline-offset:2px;}}

/* Resultado */
.cmp-result{{
  display:grid;grid-template-columns:1fr 1fr;gap:14px;
  margin-top:20px;animation:cmpFade .32s ease both;
}}
@keyframes cmpFade{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}
.cmp-col{{
  background:#060d1a;border:1px solid rgba(100,150,220,0.13);
  border-radius:13px;padding:20px;
}}
.cmp-col.win{{
  border-color:rgba(52,211,153,0.38);
  background:rgba(52,211,153,0.04);
}}
.cmp-win-badge{{
  display:inline-flex;align-items:center;gap:5px;
  background:rgba(52,211,153,0.1);color:#34d399;
  border:1px solid rgba(52,211,153,0.28);
  font-size:11px;font-weight:700;letter-spacing:.8px;
  text-transform:uppercase;padding:4px 11px;border-radius:20px;margin-bottom:12px;
}}
.cmp-ticker{{
  font-family:'DM Serif Display',serif;font-size:22px;color:#fff;margin-bottom:3px;
}}
.cmp-empresa{{font-size:11px;color:#6b8fad;margin-bottom:16px;text-transform:uppercase;letter-spacing:.5px;}}
.cmp-metric{{
  display:flex;justify-content:space-between;align-items:center;
  padding:8px 0;border-bottom:1px solid rgba(100,150,220,0.1);font-size:13px;
}}
.cmp-metric:last-child{{border-bottom:none;}}
.cmp-ml{{color:#6b8fad;}}
.cmp-mv{{font-weight:600;color:#dce8f8;}}
.cmp-mv.g{{color:#34d399;}}
.cmp-mv.r{{color:#f87171;}}
.cmp-verdict{{
  background:rgba(96,165,250,0.07);border:1px solid rgba(96,165,250,0.18);
  border-radius:10px;padding:14px 16px;margin-top:16px;
  font-size:13px;line-height:1.6;color:#dce8f8;
}}
.cmp-verdict strong{{color:#60a5fa;}}
.cmp-empty{{
  text-align:center;padding:28px;color:#6b8fad;font-size:14px;
  border:1px dashed rgba(100,150,220,0.18);border-radius:10px;margin-top:16px;
}}

/* Cards setor/categoria */
.cmp-grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:22px;}}
.cmp-panel{{
  background:rgba(17,30,48,0.95);border:1px solid rgba(100,150,220,0.13);
  border-radius:18px;padding:22px;
}}
.cmp-panel h3{{
  font-family:'DM Serif Display',serif;font-size:18px;color:#fff;margin-bottom:16px;
}}
.cmp-card{{
  background:#060d1a;border:1px solid rgba(100,150,220,0.1);
  border-radius:11px;padding:14px;margin-bottom:9px;
  transition:border-color .18s,transform .18s;
}}
.cmp-card:last-child{{margin-bottom:0;}}
.cmp-card:hover{{border-color:rgba(100,150,220,0.28);transform:translateX(3px);}}
.cmp-card-name{{font-size:13px;font-weight:600;color:#dce8f8;margin-bottom:10px;}}
.cmp-mrow{{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:9px;}}
.cmp-mpill{{background:rgba(22,36,55,0.9);border-radius:6px;padding:6px 8px;text-align:center;}}
.cmp-mpill .pl{{font-size:10px;letter-spacing:.6px;text-transform:uppercase;color:#6b8fad;display:block;margin-bottom:2px;}}
.cmp-mpill .pv{{font-size:12px;font-weight:600;color:#dce8f8;}}
.pv.pg{{color:#34d399;}}.pv.pb{{color:#60a5fa;}}.pv.py{{color:#fbbf24;}}
.cmp-sbar-top{{display:flex;justify-content:space-between;font-size:11px;color:#6b8fad;margin-bottom:4px;}}
.cmp-sbar-track{{height:4px;background:rgba(255,255,255,0.07);border-radius:99px;overflow:hidden;}}
.cmp-sbar-fill{{height:100%;border-radius:99px;background:linear-gradient(90deg,#60a5fa,#34d399);width:0%;transition:width .85s cubic-bezier(.4,0,.2,1);}}

@media(max-width:640px){{
  .cmp-selects{{grid-template-columns:1fr;}}
  .cmp-vs{{display:none;}}
  .cmp-result,.cmp-grid{{grid-template-columns:1fr;}}
  .cmp-mrow{{grid-template-columns:repeat(2,1fr);}}
}}
</style>

<!-- HERO -->
<div class="cmp-hero">
  <h2>📊 Comparar Ações da Bolsa</h2>
  <p>Escolha duas ações e compare lado a lado — P/L, ROE, Dividendos e Score. <em>Simples para qualquer investidor.</em></p>
  <div class="cmp-badges">
    <div class="cmp-badge">🔄 <strong>Atualizado hoje</strong></div>
    <div class="cmp-badge">📈 <strong>Análise fundamentalista</strong></div>
    <div class="cmp-badge">🆓 <strong>Gratuito</strong></div>
  </div>
</div>

<!-- GLOSSÁRIO -->
<p style="font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#6b8fad;margin-bottom:14px;">O que cada indicador significa?</p>
<div class="cmp-gloss" role="list">
  <div class="cmp-pill" tabindex="0" role="listitem">P/L
    <div class="cmp-tip"><strong>Preço / Lucro</strong><br>Quanto o mercado paga pelo lucro da empresa.<br>🟢 Menor = mais barata &nbsp; 🔴 Maior = mais cara</div>
  </div>
  <div class="cmp-pill" tabindex="0" role="listitem">ROE
    <div class="cmp-tip"><strong>Retorno sobre Patrimônio</strong><br>Quanto a empresa lucra com o que ela tem.<br>🟢 Maior = mais eficiente</div>
  </div>
  <div class="cmp-pill" tabindex="0" role="listitem">Dividend Yield
    <div class="cmp-tip"><strong>Rendimento em Dividendos</strong><br>Quanto você recebe em dividendos por R$100 investidos.<br>Ex: 8% = R$8 ao ano</div>
  </div>
  <div class="cmp-pill" tabindex="0" role="listitem">Desconto %
    <div class="cmp-tip"><strong>Desconto vs. Preço Justo</strong><br>Quanto a ação está abaixo do valor estimado.<br>🟢 Positivo = pode estar barata</div>
  </div>
  <div class="cmp-pill" tabindex="0" role="listitem">Score
    <div class="cmp-tip"><strong>Score Fundamentalista (0–100)</strong><br>Nossa nota combinando todos os indicadores.<br>🟢 70+ = boa oportunidade<br>🟡 50–70 = razoável<br>🔴 Abaixo de 50 = cautela</div>
  </div>
</div>

<!-- WIDGET DE COMPARAÇÃO -->
<div class="cmp-widget">
  <p style="font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#6b8fad;margin-bottom:14px;">Comparação direta entre ações</p>

  <div class="cmp-selects">
    <div class="cmp-grp">
      <label for="cmp1">1ª Ação</label>
      <select id="cmp1" class="cmp-select" aria-label="Selecione a primeira ação"></select>
    </div>
    <div class="cmp-vs" aria-hidden="true">vs</div>
    <div class="cmp-grp">
      <label for="cmp2">2ª Ação</label>
      <select id="cmp2" class="cmp-select" aria-label="Selecione a segunda ação"></select>
    </div>
  </div>

  <button class="cmp-btn" onclick="cmpComparar()" aria-label="Comparar ações selecionadas">
    ⚡ Comparar agora
  </button>

  <div id="cmp-resultado" role="region" aria-live="polite" aria-label="Resultado da comparação">
    <div class="cmp-empty">Selecione duas ações acima e clique em <strong>Comparar agora</strong>.</div>
  </div>
</div>

<!-- SETORES E CATEGORIAS -->
<div class="cmp-grid">
  <section class="cmp-panel">
    <h3>🏢 Desempenho por Setor</h3>
    <div id="cmp-setores" role="list" aria-label="Indicadores médios por setor"></div>
  </section>
  <section class="cmp-panel">
    <h3>🏷 Por Tamanho de Empresa</h3>
    <div id="cmp-cats" role="list" aria-label="Indicadores médios por categoria"></div>
  </section>

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
    <a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
    </nav>
    </div>

</div>

<script>
var cmpAcoes  = {acoes_json};
var cmpSetores = {setor_json};
var cmpCats   = {cat_json};

(function init() {{
  var s1=document.getElementById('cmp1'), s2=document.getElementById('cmp2');
  cmpAcoes.forEach(function(a,i) {{
    s1.add(new Option(a.Ticker+' — '+a.Empresa, a.Ticker));
    s2.add(new Option(a.Ticker+' — '+a.Empresa, a.Ticker));
  }});
  if (s2.options.length>1) s2.selectedIndex=1;
  cmpRenderCards(cmpSetores,'cmp-setores');
  cmpRenderCards(cmpCats,'cmp-cats');
}})();

function cmpRenderCards(data, id) {{
  var el = document.getElementById(id);

  el.innerHTML = data.map(function(d) {{
    var isSetor = !!d.Setor;
    var name = d.Setor || d.Categoria;

    // slug SEO
    var slug = name.toLowerCase().replace(/\s+/g, "-");

    // link correto
    var link = isSetor
      ? "seo/melhores-acoes-setor-" + slug + ".html"
      : "seo/melhores-acoes-" + slug + ".html";

    var sc = d.Score;
    var pct = Math.min(sc, 100).toFixed(0);
    var lbl = sc >= 65 ? '🟢 Bom' : sc >= 50 ? '🟡 Regular' : '🔴 Baixo';

    var slug = name.toLowerCase().replace(/\s+/g, "-");

    var link = d.Setor
    ? "seo/melhores-acoes-setor-" + slug + ".html"
    : "seo/melhores-acoes-" + slug + ".html";

    return `
    <a href="${{link}}" style="text-decoration:none;color:inherit;display:block">

        <div class="cmp-card" role="listitem" aria-label="${{name}}: Score ${{sc}}">

        <div class="cmp-card-name">
            ${{name}}
        </div>

        <div class="cmp-mrow">
            <div class="cmp-mpill">
            <span class="pl">P/L</span>
            <span class="pv">${{d.PL}}</span>
            </div>

            <div class="cmp-mpill">
            <span class="pl">ROE</span>
            <span class="pv pg">${{Math.round(d.ROE * 100)}}%</span>
            </div>

            <div class="cmp-mpill">
            <span class="pl">DY</span>
            <span class="pv pb">${{Math.round(d.DivYield * 100)}}%</span>
            </div>
        </div>

        <div>
            <div class="cmp-sbar-top">
            <span>Score — ${{lbl}}</span>
            <span>${{sc}}</span>
            </div>

            <div class="cmp-sbar-track">
            <div class="cmp-sbar-fill" data-w="${{pct}}%"></div>
            </div>
        </div>

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
        <a href="seo/comparar.html">↔️ Comparar Ações</a>
        <a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
        </nav>
        </div>

        </div>

    </a>

        
    `;

  }}).join('');

  requestAnimationFrame(function() {{
    el.querySelectorAll('.cmp-sbar-fill').forEach(function(b){{
      b.style.width = b.dataset.w;
    }});
  }});
}}

  requestAnimationFrame(function() {{
    el.querySelectorAll('.cmp-sbar-fill').forEach(function(b){{
      b.style.width = b.dataset.w;
    }});
  }});
}}

function cmpComparar() {{
  var t1=document.getElementById('cmp1').value, t2=document.getElementById('cmp2').value;
  var a1=cmpAcoes.find(function(a){{return a.Ticker===t1;}}),
      a2=cmpAcoes.find(function(a){{return a.Ticker===t2;}});
  if (!a1||!a2) return;

  function cls(v1,v2,hi) {{
    if (v1===v2) return ['',''];
    return hi?(v1>v2?['g','r']:['r','g']):(v1<v2?['g','r']:['r','g']);
  }}
  var plc=cls(a1.PL,a2.PL,false), roec=cls(a1.ROE,a2.ROE,true),
      dyc=cls(a1.DivYield,a2.DivYield,true), dsc=cls(a1['Desconto_%'],a2['Desconto_%'],true),
      scc=cls(a1.Score,a2.Score,true);
  var win=a1.Score>a2.Score?1:a2.Score>a1.Score?2:0;

  function buildCol(a,b,p,rc,dc,dy,sc,w) {{
    var badge=w?'<div class="cmp-win-badge">✦ Maior Score</div>':'';
    return '<div class="cmp-col'+(w?' win':'')+'">'+badge
      +'<div class="cmp-ticker">'+a.Ticker+'</div>'
      +'<div class="cmp-empresa">'+a.Empresa+' &middot; '+a.Setor+'</div>'
      +'<div class="cmp-metric"><span class="cmp-ml">P/L <small style="font-weight:400">(↓ melhor)</small></span><span class="cmp-mv '+p+'">'+a.PL.toFixed(2)+'</span></div>'
      +'<div class="cmp-metric"><span class="cmp-ml">ROE <small style="font-weight:400">(↑ melhor)</small></span><span class="cmp-mv '+rc+'">'+Math.round(a.ROE*1000)/10+'%</span></div>'
      +'<div class="cmp-metric"><span class="cmp-ml">Dividend Yield</span><span class="cmp-mv '+dy+'">'+Math.round(a.DivYield*1000)/10+'%</span></div>'
      +'<div class="cmp-metric"><span class="cmp-ml">Desconto</span><span class="cmp-mv '+dc+'">'+a['Desconto_%'].toFixed(1)+'%</span></div>'
      +'<div class="cmp-metric"><span class="cmp-ml">Score (0–100)</span><span class="cmp-mv '+sc+'">'+a.Score+'</span></div>'
      +'</div>';
  }}

  var c1=buildCol(a1,a2,plc[0],roec[0],dsc[0],dyc[0],scc[0],win===1);
  var c2=buildCol(a2,a1,plc[1],roec[1],dsc[1],dyc[1],scc[1],win===2);

  // Texto de conclusão legível para leigo
  function resumo(a,b) {{
    var pts=[];
    if (a.Score>b.Score) pts.push('score mais alto ('+a.Score+' vs '+b.Score+')');
    if (a['Desconto_%']>b['Desconto_%']) pts.push('maior desconto em relação ao preço justo ('+a['Desconto_%'].toFixed(1)+'% vs '+b['Desconto_%'].toFixed(1)+'%)');
    if (a.DivYield>b.DivYield) pts.push('mais dividendos ('+Math.round(a.DivYield*1000)/10+'% vs '+Math.round(b.DivYield*1000)/10+'%)');
    if (a.ROE>b.ROE) pts.push('melhor rentabilidade (ROE '+Math.round(a.ROE*1000)/10+'%)');
    if (pts.length===0) return 'As duas ações estão empatadas nos principais indicadores.';
    return '<strong>'+a.Ticker+'</strong> se destaca por ter '+pts.join(', ')+'. Mas a decisão final depende do seu perfil e objetivos.';
  }}

  var vtext=win===0
    ? 'As duas ações estão muito próximas. Analise com calma antes de decidir.'
    : resumo(win===1?a1:a2, win===1?a2:a1);

  document.getElementById('cmp-resultado').innerHTML=
    '<div class="cmp-result">'+c1+c2+'</div>'
    +'<div class="cmp-verdict" role="note" aria-label="Conclusão">💡 '+vtext+'</div>';
}}
</script>
""",
        descricao="Compare ações da bolsa brasileira por P/L, ROE, Dividend Yield e Score. Ferramenta gratuita e atualizada diariamente.",
        keywords="comparar ações, comparar ações bolsa, análise fundamentalista comparar"
    )
    print("comparar.html gerado.")


# =========================
# GERAR PÁGINA SIMULADOR
# =========================


def gerar_simulador(df):
    """
    Gera a página simulador-pro.html com o top-50 ativos por Score.
    Inclui:
      - Filtros de Setor e Categoria na seleção de ativos
      - Gráfico de pizza com divisão percentual por setor no resultado
    Usa .replace() para injetar o JSON — sem f-string no HTML para evitar
    conflitos com chaves CSS/JS.
    """
    

    top = df.nlargest(100, "Score")

    # Garante que todas as colunas opcionais existam com fallback seguro
    def safe_get(row, col, default="Outros"):
        val = row.get(col, default)
        if val is None or (isinstance(val, float) and __import__("math").isnan(val)):
            return default
        return str(val).strip() or default

    dados = json.dumps([
        {
            "ticker":    row["Ticker"],
            "empresa":   row["Empresa"],
            "dy":        round(float(row["DivYield"]), 4),
            "score":     int(row["Score"]),
            "preco":     round(float(row["Preco"]), 2),
            "setor":     safe_get(row, "Setor",      "Outros"),
            "categoria": safe_get(row, "Categoria",  "Ação"),
        }
        for _, row in top.iterrows()
    ], ensure_ascii=False)

    # Injetar JSON no template via marcador — seguro com qualquer conteúdo CSS/JS
    conteudo = HTML_TEMPLATE.replace("__DADOS_JSON__", dados)

    gerar_pagina(
        "simulador-pro",
        "Simulador de Carteira — TanoPrecinho",
        conteudo,
        descricao="Simule o crescimento da sua carteira de ações com benchmarks reais.",
        keywords="simulador de investimentos, carteira de ações, renda passiva, B3, bolsa",
    )

    print("simulador-pro.html gerado.")


# ── Template HTML inline ──────────────────────────────────────────────────────
# O marcador __DADOS_JSON__ é substituído em runtime com o JSON dos ativos.
# Não usar f-string: o HTML contém 200+ pares de chaves CSS/JS.
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Simulador de Carteira — TanoPrecinho</title>

<link rel="preconnect" href="https://fonts.googleapis.com">

<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">

<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-JXK8PRLVRV"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-JXK8PRLVRV');
</script>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body>

<div class="bg-grid"></div>

<div class="page">

  <!-- HEADER -->
  <header class="header">
    <div class="header-inner">
      <a href="../index.html" class="logo-link">← voltar</a>
      <div class="header-title">
        <span class="pill">BETA</span>
        <h1>Simulador de Carteira</h1>
      </div>
    </div>
  </header>

  <!-- STEPS -->
  <div class="steps-bar">
    <div class="step active" data-step="1"><span>1</span> Capital</div>
    <div class="step-sep"></div>
    <div class="step" data-step="2"><span>2</span> Ativos</div>
    <div class="step-sep"></div>
    <div class="step" data-step="3"><span>3</span> Resultado</div>
  </div>

  <!-- PASSO 1: Capital -->
  <section class="panel" id="panel-1">
    <div class="panel-head">
      <div class="panel-num">01</div>
      <div>
        <h2>Quanto você vai investir?</h2>
        <p>Defina seu capital inicial, aporte mensal e horizonte de tempo.</p>
      </div>
    </div>

    <div class="inputs-row">
      <div class="input-block">
        <label>Valor inicial</label>
        <div class="input-wrap">
          <span class="prefix">R$</span>
          <input type="number" id="valor" placeholder="10.000" min="0" step="100">
        </div>
      </div>
      <div class="input-block">
        <label>Aporte mensal</label>
        <div class="input-wrap">
          <span class="prefix">R$</span>
          <input type="number" id="aporte" placeholder="1.000" min="0" step="100">
        </div>
      </div>
      <div class="input-block">
        <label>Tempo de investimento</label>
        <div class="input-wrap">
          <input type="number" id="anos" placeholder="10" min="1" max="40" step="1">
          <span class="suffix">anos</span>
        </div>
        <div class="slider-row">
          <input type="range" id="anos-slider" min="1" max="40" value="10" class="slider">
          <div class="slider-labels">
            <span>1</span><span>10</span><span>20</span><span>30</span><span>40</span>
          </div>
        </div>
      </div>
    </div>

    <div class="benchmarks-block">
      <h3>Comparar com</h3>
      <div class="bench-pills">
        <label class="bench-pill active">
          <input type="checkbox" id="cdi" checked>
          <span class="dot" style="background:#facc15"></span> CDI (11% a.a.)
        </label>
        <label class="bench-pill active">
          <input type="checkbox" id="ibov" checked>
          <span class="dot" style="background:#60a5fa"></span> Ibovespa (10% a.a.)
        </label>
        <label class="bench-pill">
          <input type="checkbox" id="sp500">
          <span class="dot" style="background:#f472b6"></span> S&P 500 (9% a.a.)
        </label>
        <label class="bench-pill">
          <input type="checkbox" id="dolar">
          <span class="dot" style="background:#a78bfa"></span> Dólar (6% a.a.)
        </label>
      </div>
    </div>

    <button class="btn-next" onclick="irParaAtivos()">
      Escolher ativos <span>→</span>
    </button>
  </section>

  <!-- PASSO 2: Ativos -->
  <section class="panel hidden" id="panel-2">
    <div class="panel-head">
      <div class="panel-num">02</div>
      <div>
        <h2>Selecione os ativos</h2>
        <p>Escolha até 10 ativos para compor sua carteira simulada.</p>
      </div>
    </div>

    <!-- FILTROS: busca + setor + categoria -->
    <div class="filtros-row">
      <div class="search-wrap">
        <span>🔍</span>
        <input type="text" id="busca" placeholder="Buscar ticker ou empresa..." oninput="filtrarAtivos()">
      </div>
      <select id="filtro-setor" class="select-filtro" onchange="filtrarAtivos()">
        <option value="">Todos os setores</option>
      </select>
      <select id="filtro-categoria" class="select-filtro" onchange="filtrarAtivos()">
        <option value="">Todas as categorias</option>
      </select>
      <div id="selecionados-count" class="count-badge">0 selecionados</div>
    </div>

    <div id="ativos-grid" class="ativos-grid"></div>

    <div class="nav-btns">
      <button class="btn-back" onclick="irParaStep(1)">← Voltar</button>
      <button class="btn-next" onclick="simular()">Simular carteira →</button>
    </div>
  </section>

  <!-- PASSO 3: Resultado -->
  <section class="panel hidden" id="panel-3">
    <div class="panel-head">
      <div class="panel-num">03</div>
      <div>
        <h2>Resultado da simulação</h2>
        <p id="resumo-params">—</p>
      </div>
    </div>

    <div class="metricas-grid" id="metricas"></div>

    <!-- Gráfico de linha: evolução patrimonial -->
    <div class="chart-card">
      <div class="chart-header">
        <h3>Evolução patrimonial</h3>
        <div id="chart-legend" class="chart-legend"></div>
      </div>
      <div class="chart-wrap">
        <canvas id="grafico"></canvas>
      </div>
    </div>

    <!-- Gráfico de pizza: divisão por setor -->
    <div class="charts-row">
      <div class="chart-card chart-card-pie">
        <div class="chart-header">
          <h3>Divisão por setor</h3>
          <span class="chart-subtitle">% de ativos na carteira</span>
        </div>
        <div class="pie-wrap">
          <canvas id="grafico-pizza"></canvas>
        </div>
        <div id="pizza-legend" class="pizza-legend"></div>
      </div>
    </div>

    <div class="ativos-result-grid" id="ativos-result"></div>

    <div class="nav-btns">
      <button class="btn-back" onclick="irParaStep(2)">← Ajustar ativos</button>
      <button class="btn-next" onclick="irParaStep(1)">Nova simulação ↺</button>
    </div>
  </section>

</div>

<script>
// ─────────────────────────────────────────────
// DADOS (injetados pelo Python em produção)
// ─────────────────────────────────────────────
const DADOS = __DADOS_JSON__;

// ─────────────────────────────────────────────
// ESTADO
// ─────────────────────────────────────────────
let selecionados    = new Set();
let chartInstance   = null;
let pizzaInstance   = null;

// ─────────────────────────────────────────────
// STEPS
// ─────────────────────────────────────────────
function irParaStep(n) {
  document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
  document.getElementById(`panel-${n}`).classList.remove('hidden');
  document.querySelectorAll('.step').forEach(s => {
    const sn = parseInt(s.dataset.step);
    s.classList.toggle('active', sn <= n);
    s.classList.toggle('done', sn < n);
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function irParaAtivos() {
  const valor = parseFloat(document.getElementById('valor').value);
  const anos  = parseFloat(document.getElementById('anos').value);
  if (!valor || valor <= 0 || !anos || anos <= 0) {
    shakePanelError('panel-1');
    return;
  }
  popularFiltros();
  renderAtivos();
  irParaStep(2);
}

function shakePanelError(id) {
  const el = document.getElementById(id);
  el.classList.add('shake');
  setTimeout(() => el.classList.remove('shake'), 500);
}

// ─────────────────────────────────────────────
// SLIDER SYNC
// ─────────────────────────────────────────────
document.getElementById('anos').addEventListener('input', e => {
  document.getElementById('anos-slider').value = e.target.value;
});
document.getElementById('anos-slider').addEventListener('input', e => {
  document.getElementById('anos').value = e.target.value;
});

// Bench pills toggle visual
document.querySelectorAll('.bench-pill input').forEach(cb => {
  cb.addEventListener('change', () => {
    cb.closest('.bench-pill').classList.toggle('active', cb.checked);
  });
});

// ─────────────────────────────────────────────
// POPULAR FILTROS DE SETOR E CATEGORIA
// ─────────────────────────────────────────────
function popularFiltros() {
  const setores     = [...new Set(DADOS.map(a => a.setor).filter(Boolean))].sort();
  const categorias  = [...new Set(DADOS.map(a => a.categoria).filter(Boolean))].sort();

  const selSetor = document.getElementById('filtro-setor');
  const selCat   = document.getElementById('filtro-categoria');

  // Preserva seleção atual ao re-popular
  const setorAtual = selSetor.value;
  const catAtual   = selCat.value;

  selSetor.innerHTML = '<option value="">Todos os setores</option>' +
    setores.map(s => `<option value="${s}"${s === setorAtual ? ' selected' : ''}>${s}</option>`).join('');

  selCat.innerHTML = '<option value="">Todas as categorias</option>' +
    categorias.map(c => `<option value="${c}"${c === catAtual ? ' selected' : ''}>${c}</option>`).join('');
}

// ─────────────────────────────────────────────
// RENDER ATIVOS COM FILTROS
// ─────────────────────────────────────────────
let dadosFiltrados = [...DADOS];

function filtrarAtivos() {
  const q      = document.getElementById('busca').value.toLowerCase().trim();
  const setor  = document.getElementById('filtro-setor').value;
  const cat    = document.getElementById('filtro-categoria').value;

  dadosFiltrados = DADOS.filter(a => {
    const matchTexto = !q ||
      a.ticker.toLowerCase().includes(q) ||
      a.empresa.toLowerCase().includes(q);
    const matchSetor = !setor || a.setor === setor;
    const matchCat   = !cat   || a.categoria === cat;
    return matchTexto && matchSetor && matchCat;
  });

  renderAtivos();
}

function renderAtivos() {
  const grid = document.getElementById('ativos-grid');
  if (dadosFiltrados.length === 0) {
    grid.innerHTML = '<div class="empty-state">Nenhum ativo encontrado para os filtros selecionados.</div>';
    atualizarContador();
    return;
  }

  grid.innerHTML = dadosFiltrados.map(a => {
    const sel    = selecionados.has(a.ticker);
    const dyPct  = (a.dy * 100).toFixed(2);
    return `
    <div class="ativo-card ${sel ? 'sel' : ''}" onclick="toggleAtivo('${a.ticker}')" data-ticker="${a.ticker}">
      <div class="ativo-top">
        <img src="../logos/${a.ticker}.png"
          onerror="this.onerror=null;this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 40 40%22><rect width=%2240%22 height=%2240%22 rx=%228%22 fill=%22%231e293b%22/><text x=%2250%25%22 y=%2254%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-size=%2213%22 fill=%22%2394a3b8%22 font-family=%22monospace%22>${a.ticker[0]}</text></svg>'"
          class="ativo-logo" alt="${a.ticker}">
        <div class="ativo-info">
          <strong>${a.ticker}</strong>
          <small>${a.empresa}</small>
        </div>
        <div class="check-icon">${sel ? '✓' : ''}</div>
      </div>
      <div class="ativo-bottom">
        <div class="ativo-stat">
          <span class="stat-label">DY</span>
          <span class="stat-val dy">${dyPct}%</span>
        </div>
        <div class="ativo-stat">
          <span class="stat-label">Score</span>
          <span class="stat-val">${a.score}</span>
        </div>
        <div class="ativo-stat">
          <span class="stat-label">Preço</span>
          <span class="stat-val">R$${a.preco}</span>
        </div>
      </div>
      <div class="setor-tag">${a.setor}</div>
      <div class="cat-tag">${a.categoria}</div>
    </div>`;
  }).join('');

  atualizarContador();
}

function toggleAtivo(ticker) {
  if (selecionados.has(ticker)) {
    selecionados.delete(ticker);
  } else {
    if (selecionados.size >= 10) {
      alert('Máximo de 10 ativos por simulação.');
      return;
    }
    selecionados.add(ticker);
  }
  const card = document.querySelector(`.ativo-card[data-ticker="${ticker}"]`);
  if (card) {
    card.classList.toggle('sel', selecionados.has(ticker));
    const icon = card.querySelector('.check-icon');
    if (icon) icon.textContent = selecionados.has(ticker) ? '✓' : '';
  }
  atualizarContador();
}

function atualizarContador() {
  const n = selecionados.size;
  document.getElementById('selecionados-count').textContent =
    n === 0 ? 'Nenhum selecionado' : `${n} selecionado${n > 1 ? 's' : ''}`;
}

// ─────────────────────────────────────────────
// SIMULAÇÃO
// ─────────────────────────────────────────────
function simular() {
  if (selecionados.size === 0) { shakePanelError('panel-2'); return; }

  const valor  = parseFloat(document.getElementById('valor').value)  || 0;
  const aporte = parseFloat(document.getElementById('aporte').value) || 0;
  const anos   = parseFloat(document.getElementById('anos').value)   || 10;
  const meses  = Math.round(anos * 12);

  const ativos  = DADOS.filter(d => selecionados.has(d.ticker));
  const dyMedio = ativos.reduce((s, a) => s + a.dy, 0) / ativos.length;

  // Séries mensais
  const series = { carteira: [], cdi: [], ibov: [], sp500: [], dolar: [] };
  const taxas  = { cdi: 0.11, ibov: 0.10, sp500: 0.09, dolar: 0.06 };

  let totCarteira = valor;
  for (let i = 0; i < meses; i++) {
    totCarteira += aporte;
    totCarteira *= (1 + dyMedio / 12);
    series.carteira.push(totCarteira);

    for (const [key, taxa] of Object.entries(taxas)) {
      let t = series[key].length > 0 ? series[key][series[key].length - 1] : valor;
      t += aporte;
      t *= (1 + taxa / 12);
      series[key].push(t);
    }
  }

  const finalCarteira  = series.carteira[meses - 1];
  const totalInvestido = valor + aporte * meses;
  const rendaMensal    = (finalCarteira * dyMedio) / 12;
  const ganho          = finalCarteira - totalInvestido;
  const ganhoPerc      = ((finalCarteira / totalInvestido - 1) * 100).toFixed(1);

  // Métricas
  document.getElementById('metricas').innerHTML = `
    <div class="metrica-card highlight">
      <div class="metrica-label">Patrimônio final</div>
      <div class="metrica-val">${fmt(finalCarteira)}</div>
    </div>
    <div class="metrica-card">
      <div class="metrica-label">Total investido</div>
      <div class="metrica-val dim">${fmt(totalInvestido)}</div>
    </div>
    <div class="metrica-card green">
      <div class="metrica-label">Ganho</div>
      <div class="metrica-val">${fmt(ganho)} <span class="badge-perc">+${ganhoPerc}%</span></div>
    </div>
    <div class="metrica-card green">
      <div class="metrica-label">Renda mensal estimada</div>
      <div class="metrica-val">${fmt(rendaMensal)}</div>
      <div class="metrica-sub">DY médio: ${(dyMedio * 100).toFixed(2)}% a.a.</div>
    </div>
  `;

  // Resumo
  document.getElementById('resumo-params').textContent =
    `Capital inicial ${fmt(valor)} + aportes de ${fmt(aporte)}/mês por ${anos} anos`;

  // Ativos resultado
  document.getElementById('ativos-result').innerHTML =
    `<div class="ativos-result-title">Ativos selecionados</div>` +
    ativos.map(a => `
    <div class="ativo-result-row">
      <img src="../logos/${a.ticker}.png"
        onerror="this.onerror=null;this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 40 40%22><rect width=%2240%22 height=%2240%22 rx=%228%22 fill=%22%231e293b%22/><text x=%2250%25%22 y=%2254%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 font-size=%2213%22 fill=%22%2394a3b8%22 font-family=%22monospace%22>${a.ticker[0]}</text></svg>'"
        class="ativo-logo-sm">
      <span class="ativo-ticker-sm">${a.ticker}</span>
      <span class="ativo-emp-sm">${a.empresa}</span>
      <span class="setor-badge">${a.setor}</span>
      <span class="cat-badge">${a.categoria}</span>
      <span class="dy-badge">${(a.dy * 100).toFixed(2)}% DY</span>
    </div>`).join('');

  renderGrafico(series, meses, anos);
  renderGraficoPizza(ativos);
  irParaStep(3);
}

// ─────────────────────────────────────────────
// GRÁFICO DE LINHA — Evolução patrimonial
// ─────────────────────────────────────────────
const CORES = {
  carteira: '#22c55e',
  cdi:      '#facc15',
  ibov:     '#60a5fa',
  sp500:    '#f472b6',
  dolar:    '#a78bfa',
};

function renderGrafico(series, meses, anos) {
  const ctx = document.getElementById('grafico').getContext('2d');
  if (chartInstance) { chartInstance.destroy(); chartInstance = null; }

  const labels = Array.from({ length: meses }, (_, i) => {
    const a = Math.floor(i / 12) + 1;
    return i % 12 === 0 ? `Ano ${a}` : '';
  });

  const datasets = [{
    label: 'Sua carteira',
    data: series.carteira,
    borderColor: CORES.carteira,
    backgroundColor: 'rgba(34,197,94,0.08)',
    borderWidth: 2.5,
    fill: true,
    tension: 0.4,
    pointRadius: 0,
    pointHoverRadius: 5,
  }];

  const benchActive = {
    cdi:   document.getElementById('cdi').checked,
    ibov:  document.getElementById('ibov').checked,
    sp500: document.getElementById('sp500').checked,
    dolar: document.getElementById('dolar').checked,
  };
  const benchLabels = { cdi: 'CDI', ibov: 'Ibovespa', sp500: 'S&P 500', dolar: 'Dólar' };

  for (const [key, active] of Object.entries(benchActive)) {
    if (!active) continue;
    datasets.push({
      label: benchLabels[key],
      data: series[key],
      borderColor: CORES[key],
      backgroundColor: 'transparent',
      borderWidth: 1.5,
      borderDash: [4, 4],
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 4,
      fill: false,
    });
  }

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          borderColor: '#1e293b',
          borderWidth: 1,
          padding: 12,
          callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.raw)}` }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#475569', font: { family: 'DM Mono', size: 11 } }
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: {
            color: '#475569',
            font: { family: 'DM Mono', size: 11 },
            callback: v => fmtShort(v)
          }
        }
      }
    }
  });

  // Legenda manual
  const leg = document.getElementById('chart-legend');
  leg.innerHTML = datasets.map(d => `
    <div class="leg-item">
      <span class="leg-dot" style="background:${d.borderColor}"></span>
      ${d.label}
    </div>`).join('');
}

// ─────────────────────────────────────────────
// GRÁFICO DE PIZZA — Divisão por setor
// ─────────────────────────────────────────────
const PIZZA_CORES = [
  '#22c55e','#60a5fa','#facc15','#f472b6','#a78bfa',
  '#fb923c','#34d399','#f87171','#38bdf8','#c084fc',
  '#fbbf24','#4ade80','#818cf8','#e879f9','#2dd4bf',
];

function renderGraficoPizza(ativos) {
  const ctx = document.getElementById('grafico-pizza').getContext('2d');
  if (pizzaInstance) { pizzaInstance.destroy(); pizzaInstance = null; }

  // Conta ativos por setor
  const contagem = {};
  ativos.forEach(a => {
    const s = a.setor || 'Outros';
    contagem[s] = (contagem[s] || 0) + 1;
  });

  const total   = ativos.length;
  const labels  = Object.keys(contagem);
  const valores = Object.values(contagem);
  const cores   = labels.map((_, i) => PIZZA_CORES[i % PIZZA_CORES.length]);

  pizzaInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: valores,
        backgroundColor: cores,
        borderColor: '#020617',
        borderWidth: 3,
        hoverOffset: 8,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          borderColor: '#1e293b',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: ctx => {
              const pct = ((ctx.raw / total) * 100).toFixed(1);
              return ` ${ctx.label}: ${ctx.raw} ativo${ctx.raw > 1 ? 's' : ''} (${pct}%)`;
            }
          }
        }
      }
    }
  });

  // Legenda personalizada
  const legEl = document.getElementById('pizza-legend');
  legEl.innerHTML = labels.map((label, i) => {
    const pct = ((valores[i] / total) * 100).toFixed(1);
    return `
      <div class="pizza-leg-item">
        <span class="pizza-leg-dot" style="background:${cores[i]}"></span>
        <span class="pizza-leg-label">${label}</span>
        <span class="pizza-leg-pct">${pct}%</span>
      </div>`;
  }).join('');
}

// ─────────────────────────────────────────────
// UTILS
// ─────────────────────────────────────────────
function fmt(v) {
  return 'R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtShort(v) {
  if (v >= 1e6) return 'R$ ' + (v / 1e6).toFixed(1) + 'M';
  if (v >= 1e3) return 'R$ ' + (v / 1e3).toFixed(0) + 'K';
  return 'R$ ' + v.toFixed(0);
}

// init
popularFiltros();
renderAtivos();
</script>

<style>
/* ─── RESET & BASE ─── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:       #020617;
  --surface:  #0d1526;
  --surface2: #111827;
  --border:   #1e293b;
  --border2:  #263148;
  --text:     #f1f5f9;
  --muted:    #64748b;
  --accent:   #22c55e;
  --accent2:  #16a34a;
  --danger:   #ef4444;
  --yellow:   #facc15;
  --blue:     #60a5fa;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'DM Sans', sans-serif;
  font-size: 15px;
  min-height: 100vh;
  overflow-x: hidden;
}

/* ─── BG GRID ─── */
.bg-grid {
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(34,197,94,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34,197,94,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

/* ─── PAGE ─── */
.page {
  position: relative;
  z-index: 1;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px 80px;
}
@media (max-width: 768px) {
  .page { padding: 16px 12px 60px; }
}

/* ─── HEADER ─── */
.header { margin-bottom: 32px; }
.header-inner {
  display: flex;
  align-items: center;
  gap: 20px;
}
.logo-link {
  color: var(--muted);
  text-decoration: none;
  font-family: 'DM Mono', monospace;
  font-size: 13px;
  transition: color .2s;
  white-space: nowrap;
}
.logo-link:hover { color: var(--accent); }
.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-title h1 {
  font-family: 'Syne', sans-serif;
  font-size: clamp(20px, 4vw, 28px);
  font-weight: 800;
  letter-spacing: -0.5px;
}
.pill {
  background: rgba(34,197,94,0.15);
  color: var(--accent);
  border: 1px solid rgba(34,197,94,0.3);
  border-radius: 99px;
  padding: 2px 10px;
  font-size: 11px;
  font-family: 'DM Mono', monospace;
  letter-spacing: 1px;
}

/* ─── STEPS BAR ─── */
.steps-bar {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 32px;
  font-family: 'DM Mono', monospace;
  font-size: 12px;
}
.step {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  transition: color .3s;
}
.step span {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--surface2);
  border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px;
  transition: all .3s;
}
.step.active { color: var(--text); }
.step.active span {
  background: var(--accent);
  border-color: var(--accent);
  color: #000;
  font-weight: 700;
}
.step.done span {
  background: rgba(34,197,94,0.2);
  border-color: var(--accent);
  color: var(--accent);
}
.step-sep {
  flex: 1;
  height: 1px;
  background: var(--border);
  margin: 0 12px;
  max-width: 80px;
}

/* ─── PANEL ─── */
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 32px;
}
@media (max-width: 768px) {
  .panel { padding: 20px 16px; border-radius: 16px; }
}
.panel.hidden { display: none; }

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes shake {
  0%,100% { transform: translateX(0); }
  20%     { transform: translateX(-8px); }
  40%     { transform: translateX(8px); }
  60%     { transform: translateX(-5px); }
  80%     { transform: translateX(5px); }
}
.shake { animation: shake .45s ease; }

.panel-head {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  margin-bottom: 28px;
}
.panel-num {
  font-family: 'Syne', sans-serif;
  font-size: 48px;
  font-weight: 800;
  color: rgba(34,197,94,0.15);
  line-height: 1;
  min-width: 64px;
  letter-spacing: -2px;
}
.panel-head h2 {
  font-family: 'Syne', sans-serif;
  font-size: clamp(18px, 3vw, 24px);
  font-weight: 700;
  margin-bottom: 4px;
}
.panel-head p { color: var(--muted); font-size: 14px; }

/* ─── INPUTS ─── */
.inputs-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
}
@media(max-width: 640px) { .inputs-row { grid-template-columns: 1fr; } }

.input-block label {
  display: block;
  font-size: 12px;
  color: var(--muted);
  font-family: 'DM Mono', monospace;
  letter-spacing: .5px;
  margin-bottom: 8px;
  text-transform: uppercase;
}
.input-wrap {
  display: flex;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color .2s;
}
.input-wrap:focus-within { border-color: var(--accent); }
.prefix, .suffix {
  padding: 12px 14px;
  color: var(--muted);
  font-family: 'DM Mono', monospace;
  font-size: 13px;
  background: var(--surface2);
  border-right: 1px solid var(--border);
}
.suffix { border-right: none; border-left: 1px solid var(--border); }
.input-wrap input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font-size: 15px;
  padding: 12px 14px;
  font-family: 'DM Mono', monospace;
  width: 100%;
}
input[type=number]::-webkit-inner-spin-button { opacity: 0; }

/* Slider */
.slider-row { margin-top: 10px; }
.slider {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 4px;
  background: var(--border2);
  outline: none;
  cursor: pointer;
}
.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
  border: 2px solid var(--bg);
  box-shadow: 0 0 0 2px rgba(34,197,94,0.3);
}
.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 11px;
  color: var(--muted);
  font-family: 'DM Mono', monospace;
}

/* ─── BENCHMARKS ─── */
.benchmarks-block { margin-bottom: 28px; }
.benchmarks-block h3 {
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  font-family: 'DM Mono', monospace;
  letter-spacing: .5px;
  margin-bottom: 12px;
}
.bench-pills { display: flex; flex-wrap: wrap; gap: 8px; }
.bench-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 99px;
  border: 1px solid var(--border2);
  cursor: pointer;
  font-size: 13px;
  color: var(--muted);
  transition: all .2s;
}
.bench-pill input { display: none; }
.bench-pill.active { border-color: var(--border2); color: var(--text); background: var(--surface2); }
.dot { width: 8px; height: 8px; border-radius: 50%; }

/* ─── BOTÕES ─── */
.btn-next {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #000;
  font-family: 'Syne', sans-serif;
  font-weight: 700;
  font-size: 15px;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  transition: all .2s;
  letter-spacing: .5px;
}
.btn-next:hover { filter: brightness(1.1); transform: translateY(-1px); box-shadow: 0 8px 24px rgba(34,197,94,0.25); }
.btn-back {
  padding: 14px 24px;
  background: transparent;
  color: var(--muted);
  font-family: 'Syne', sans-serif;
  font-weight: 600;
  font-size: 14px;
  border: 1px solid var(--border2);
  border-radius: 14px;
  cursor: pointer;
  transition: all .2s;
}
.btn-back:hover { color: var(--text); border-color: var(--text); }
.nav-btns { display: flex; gap: 12px; margin-top: 32px; }
.nav-btns .btn-next { flex: 1; }

/* ─── FILTROS ─── */
.filtros-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.search-wrap {
  flex: 1;
  min-width: 160px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 12px;
  padding: 10px 16px;
  transition: border-color .2s;
}
.search-wrap:focus-within { border-color: var(--accent); }
.search-wrap input {
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font-size: 14px;
  width: 100%;
}

/* Select de filtro */
.select-filtro {
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 12px;
  color: var(--text);
  font-family: 'DM Mono', monospace;
  font-size: 12px;
  padding: 10px 14px;
  cursor: pointer;
  outline: none;
  transition: border-color .2s;
  min-width: 130px;
  max-width: 190px;
  flex-shrink: 0;
}
.select-filtro:focus { border-color: var(--accent); }
.select-filtro option {
  background: var(--surface2);
  color: var(--text);
}

.count-badge {
  font-size: 12px;
  font-family: 'DM Mono', monospace;
  color: var(--accent);
  background: rgba(34,197,94,0.1);
  border: 1px solid rgba(34,197,94,0.2);
  padding: 8px 14px;
  border-radius: 99px;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Estado vazio */
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px 20px;
  color: var(--muted);
  font-size: 14px;
  font-family: 'DM Mono', monospace;
}

/* ─── ATIVOS GRID ─── */
.ativos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
  max-height: 460px;
  overflow-y: auto;
  padding-right: 4px;
  margin-bottom: 8px;
}
.ativos-grid::-webkit-scrollbar { width: 4px; }
.ativos-grid::-webkit-scrollbar-track { background: transparent; }
.ativos-grid::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }

.ativo-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px;
  cursor: pointer;
  transition: all .18s;
  position: relative;
  overflow: hidden;
}
.ativo-card:hover { border-color: var(--accent); transform: translateY(-2px); }
.ativo-card.sel {
  border-color: var(--accent);
  background: rgba(34,197,94,0.06);
}

.ativo-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.ativo-logo {
  width: 32px; height: 32px;
  border-radius: 8px;
  object-fit: contain;
  background: var(--surface2);
  flex-shrink: 0;
}
.ativo-info strong {
  display: block;
  font-size: 13px;
  font-family: 'DM Mono', monospace;
  font-weight: 500;
}
.ativo-info small {
  display: block;
  font-size: 11px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
}
.check-icon {
  margin-left: auto;
  color: var(--accent);
  font-weight: 700;
  font-size: 14px;
  min-width: 16px;
  text-align: center;
}

.ativo-bottom {
  display: flex;
  gap: 6px;
  justify-content: space-between;
  margin-bottom: 6px;
}
.ativo-stat { text-align: center; flex: 1; }
.stat-label {
  display: block;
  font-size: 10px;
  color: var(--muted);
  font-family: 'DM Mono', monospace;
  margin-bottom: 2px;
}
.stat-val {
  font-size: 12px;
  font-family: 'DM Mono', monospace;
  font-weight: 500;
}
.stat-val.dy { color: var(--accent); }

.setor-tag {
  font-size: 9px;
  font-family: 'DM Mono', monospace;
  color: var(--muted);
  background: var(--surface2);
  border-radius: 99px;
  padding: 2px 7px;
  opacity: 0.8;
  display: inline-block;
  margin-top: 2px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cat-tag {
  font-size: 9px;
  font-family: 'DM Mono', monospace;
  color: #60a5fa;
  background: rgba(96,165,250,0.08);
  border: 1px solid rgba(96,165,250,0.2);
  border-radius: 99px;
  padding: 2px 7px;
  display: inline-block;
  margin-top: 3px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ─── MÉTRICAS ─── */
.metricas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 28px;
}
.metrica-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
}
.metrica-card.highlight {
  border-color: rgba(34,197,94,0.4);
  background: rgba(34,197,94,0.04);
}
.metrica-card.green .metrica-val { color: var(--accent); }
.metrica-label {
  font-size: 11px;
  font-family: 'DM Mono', monospace;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .5px;
  margin-bottom: 8px;
}
.metrica-val {
  font-family: 'Syne', sans-serif;
  font-size: clamp(16px, 2.5vw, 22px);
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}
.metrica-val.dim { color: var(--muted); }
.metrica-sub { font-size: 12px; color: var(--muted); margin-top: 4px; }
.badge-perc {
  font-size: 12px;
  background: rgba(34,197,94,0.15);
  color: var(--accent);
  border-radius: 99px;
  padding: 2px 8px;
}

/* ─── CHARTS ROW ─── */
.charts-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  margin-bottom: 24px;
}
@media (min-width: 768px) {
  .charts-row { grid-template-columns: 1fr; }
}

/* ─── CHART CARD ─── */
.chart-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}
.chart-card-pie { margin-bottom: 0; }
.chart-subtitle {
  font-size: 12px;
  font-family: 'DM Mono', monospace;
  color: var(--muted);
}
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}
.chart-header h3 {
  font-family: 'Syne', sans-serif;
  font-size: 16px;
  font-weight: 700;
}
.chart-legend { display: flex; flex-wrap: wrap; gap: 14px; }
.leg-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-family: 'DM Mono', monospace;
  color: var(--muted);
}
.leg-dot { width: 10px; height: 10px; border-radius: 50%; }

.chart-wrap {
  position: relative;
  width: 100%;
  height: 280px;
}
@media (min-width: 768px)  { .chart-wrap { height: 380px; } }
@media (min-width: 1200px) { .chart-wrap { height: 420px; } }

/* ─── PIE CHART ─── */
.pie-wrap {
  position: relative;
  width: 100%;
  height: 260px;
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}
.pie-wrap canvas {
  max-width: 260px;
}
.pizza-legend {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}
.pizza-leg-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-family: 'DM Mono', monospace;
}
.pizza-leg-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pizza-leg-label {
  flex: 1;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pizza-leg-pct {
  color: var(--text);
  font-weight: 500;
}

/* ─── ATIVOS RESULT ─── */
.ativos-result-grid {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
}
.ativos-result-title {
  padding: 14px 20px;
  font-size: 12px;
  font-family: 'DM Mono', monospace;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .5px;
  border-bottom: 1px solid var(--border);
}
.ativo-result-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border);
  transition: background .15s;
  flex-wrap: wrap;
}
.ativo-result-row:last-child { border-bottom: none; }
.ativo-result-row:hover { background: var(--surface2); }
.ativo-logo-sm {
  width: 28px; height: 28px;
  border-radius: 6px;
  object-fit: contain;
  background: var(--surface2);
  flex-shrink: 0;
}
.ativo-ticker-sm {
  font-family: 'DM Mono', monospace;
  font-weight: 500;
  font-size: 13px;
  min-width: 52px;
}
.ativo-emp-sm { font-size: 13px; color: var(--muted); flex: 1; min-width: 80px; }
.setor-badge {
  font-size: 11px;
  font-family: 'DM Mono', monospace;
  color: var(--muted);
  background: var(--surface2);
  border: 1px solid var(--border2);
  padding: 3px 9px;
  border-radius: 99px;
}
.cat-badge {
  font-size: 11px;
  font-family: 'DM Mono', monospace;
  color: #60a5fa;
  background: rgba(96,165,250,0.08);
  border: 1px solid rgba(96,165,250,0.2);
  padding: 3px 9px;
  border-radius: 99px;
}
.dy-badge {
  font-size: 12px;
  font-family: 'DM Mono', monospace;
  color: var(--accent);
  background: rgba(34,197,94,0.1);
  border: 1px solid rgba(34,197,94,0.2);
  padding: 4px 10px;
  border-radius: 99px;
}

/* ─── MISC ─── */
@media (max-width: 640px) {
  .header-inner { flex-direction: column; align-items: flex-start; gap: 12px; }
}
html, body { max-width: 100%; overflow-x: hidden; }
.chart-legend { justify-content: flex-start; }
</style>
</body>
</html>
"""


# =========================
# SETUP DIRETÓRIOS
# =========================

os.makedirs("docs", exist_ok=True)
os.makedirs("docs/acoes", exist_ok=True)
os.makedirs("docs/seo", exist_ok=True)

hoje    = datetime.date.today()
data_br = hoje.strftime("%d/%m/%Y")

df.to_csv("docs/ranking.csv", index=False)

setores    = sorted(df["Setor"].unique())
categorias = sorted(df["Categoria"].unique())

logger.info("Gerando site...")

for _, row in df.iterrows():
    gerar_pagina_acao(row)
    gerar_paginas_seo_ticker(row)

gerar_paginas_ranking(df)
gerar_paginas_high_intent(df)
gerar_paginas_setores(df)
gerar_paginas_categorias(df)
gerar_simulador(df)  
gerar_sitemap(df)

# =========================
# HTML PRINCIPAL — INDEX
# =========================

setores    = sorted(df["Setor"].unique())
categorias = sorted(df["Categoria"].unique())

html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5213961841779335" crossorigin="anonymous"></script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Ranking automático das ações brasileiras mais baratas baseado em análise fundamentalista. Atualizado diariamente.">
<meta name="keywords" content="ações baratas, bolsa brasileira, value investing, ranking ações, B3">
<link rel="canonical" href="https://tanoprecinho.site/">
<meta name="robots" content="index, follow">
<meta property="og:title" content="Tá no Precinho? - Ranking de ações brasileiras">
<meta property="og:description" content="Descubra quais ações podem estar baratas hoje segundo análise fundamentalista.">
<meta property="og:image" content="https://tanoprecinho.site/images/og-image.jpg">
<title>Tá no Precinho? | Ranking de ações da bolsa brasileira</title>

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
    padding:14px;
    border-radius:12px;
}}

/* Opção A — barras horizontais com logo */
.bar-row{{
    display:flex;
    align-items:center;
    gap:10px;
    margin-bottom:11px;
}}
.bar-row:last-child{{ margin-bottom:0; }}
.bar-logo{{
    width:28px;
    height:28px;
    border-radius:6px;
    background:#0f172a;
    border:1px solid rgba(255,255,255,0.08);
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:9px;
    font-weight:700;
    color:var(--muted);
    flex-shrink:0;
    overflow:hidden;
}}
.bar-logo img{{
    width:100%;
    height:100%;
    object-fit:contain;
}}
.bar-info{{ flex:1;min-width:0; }}
.bar-label{{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:4px;
}}
.bar-ticker{{ font-size:12px;font-weight:700;color:var(--text); }}
.bar-value{{ font-size:12px;font-weight:700; }}
.bar-track{{
    height:5px;
    background:rgba(255,255,255,0.06);
    border-radius:99px;
    overflow:hidden;
}}
.bar-fill{{
    height:100%;
    border-radius:99px;
    transition:width 0.9s cubic-bezier(0.4,0,0.2,1);
}}
.bar-empresa{{
    font-size:10px;
    color:var(--muted);
    margin-top:2px;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
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

// ─────────────────────────────────────────────
// CORREÇÃO BUG 2: todas as variáveis declaradas
// DENTRO do callback do filter, não fora dele.
// ─────────────────────────────────────────────
function aplicarFiltros() {{
    const categoria   = document.getElementById("filtroCategoria").value;
    const setorFiltro = document.getElementById("filtroSetor").value;
    const scoreMin    = parseFloat(document.getElementById("filtroScore").value) || 0;
    let quantidade    = parseInt(document.getElementById("filtroQuantidade").value);
    if (isNaN(quantidade)) quantidade = 9999;
    const periodo     = parseInt(document.getElementById("filtroPeriodo").value) || 0;

    const linhas    = Array.from(document.querySelectorAll("tbody tr"));
    const filtradas = linhas.filter(linha => {{
        const setorLinha     = linha.dataset.setor;
        const categoriaLinha = linha.dataset.categoria;
        const scoreLinha     = parseFloat(linha.dataset.score) || 0;
        const variacaoLinha  = parseFloat(linha.dataset.variacao) || 0;

        if (setorFiltro !== "Todos" && setorLinha !== setorFiltro) return false;
        if (categoria   !== "Todos" && categoriaLinha !== categoria) return false;
        if (scoreLinha  < scoreMin) return false;
        if (periodo > 0 && variacaoLinha === 0) return false;

        return true;
    }});

    linhas.forEach(l => l.style.display = "none");
    filtradas.slice(0, quantidade).forEach(l => {{ l.style.display = ""; }});
}}

function ordenarTabela(coluna) {{
    const tabela = document.querySelector("tbody");
    const linhas = Array.from(tabela.querySelectorAll("tr"));
    ordemAsc = !ordemAsc;
    linhas.sort((a, b) => {{
        const valA = a.children[coluna].innerText.replace('%','').replace(',','.');
        const valB = b.children[coluna].innerText.replace('%','').replace(',','.');
        return ordemAsc
            ? parseFloat(valA) - parseFloat(valB)
            : parseFloat(valB) - parseFloat(valA);
    }});
    linhas.forEach(l => tabela.appendChild(l));
}}

// ─────────────────────────────────────────────
// CORREÇÃO BUG 1: variáveis JSON injetadas com
// chave simples (não dupla) no f-string Python.
// CORREÇÃO BUG 7: try/catch para JSON inválido.
// ─────────────────────────────────────────────
let dados = {{ top: [], blue: [], mid: [], small: [] }};
try {{
    dados = {{
        top:   {top10_json},
        blue:  {top_blue_json},
        mid:   {top_mid_json},
        small: {top_small_json}
    }};
}} catch(e) {{
    console.error("Erro ao carregar dados dos gráficos:", e);
}}

function renderBarras(containerId, items, cor) {{
    const container = document.getElementById(containerId);
    if (!container) return;
    if (!items || items.length === 0) {{
        container.innerHTML = "<div style='color:#94a3b8;font-size:12px'>Sem dados</div>";
        return;
    }}
    const max = Math.max(...items.map(d => d.desconto));
    container.innerHTML = items.map(d => {{
        const largura = max > 0 ? (d.desconto / max * 100) : 0;
        return `
        <div class="bar-row" onclick="window.location='acoes/${{d.ticker}}.html'">
          <div class="bar-logo">
            <img src="logos/${{d.ticker}}.png" loading="lazy"
                 onerror="this.onerror=null;this.src='logos/default.svg';">
          </div>
          <div class="bar-info">
            <div class="bar-label">
              <span>${{d.ticker}}</span>
              <span style="color:${{cor}}">${{d.desconto}}%</span>
            </div>
            <div class="bar-track">
              <div class="bar-fill" style="width:${{largura.toFixed(1)}}%;background:${{cor}}"></div>
            </div>
            <div style="font-size:10px;color:#94a3b8">${{d.empresa}}</div>
          </div>
        </div>`;
    }}).join('');
}}

function aceitarCookies() {{
    localStorage.setItem("cookies_consent","accepted");
    document.getElementById("cookie-banner").style.display = "none";
}}

function recusarCookies() {{
    localStorage.setItem("cookies_consent","rejected");
    document.getElementById("cookie-banner").style.display = "none";
}}

document.addEventListener("DOMContentLoaded", () => {{
    const consent = localStorage.getItem("cookies_consent");
    if (!consent) document.getElementById("cookie-banner").style.display = "block";

    aplicarFiltros();

    renderBarras("barras-top",   dados.top,   "#ef4444");
    renderBarras("barras-blue",  dados.blue,  "#3b82f6");
    renderBarras("barras-mid",   dados.mid,   "#22c55e");
    renderBarras("barras-small", dados.small, "#facc15");
}});

</script>
</head>

<body>
<div class="container">

<nav aria-label="Menu principal">
<div style="margin-bottom:20px" class="menu">
  <a href="index.html">Ranking</a>
  <a href="missao.html">Nossa missão</a>
  <a href="fundamentalista.html">Análise Fundamentalista</a>
  <a href="pl.html">O que é P/L</a>
  <a href="pvp.html">O que é P/VP</a>
  <a href="roe.html">O que é ROE</a>
  <a href="on-pn.html">Diferença entre ações ON e PN</a>
  <a href="dividend-yield.html">Dividend Yield</a>
  <a href="estrategia-investidor.html">Como Investir Melhor em Ações</a>
  <a href="doacoes.html">💚 Apoie o Projeto</a>
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

<div class="stats" role="region" aria-label="Estatísticas gerais">
<div class="stat-box"><div class="stat-num">{universo_b3}</div><div class="stat-label">📊 Ativos B3</div></div>
<div class="stat-box"><div class="stat-num">{acoes_coletadas}</div><div class="stat-label">🔎 Ações analisadas</div></div>
<div class="stat-box"><div class="stat-num">{pagadoras_div}</div><div class="stat-label">💰 Pagadoras de dividendos</div></div>
<div class="stat-box"><div class="stat-num">{score_alto}</div><div class="stat-label">🏆 Score ≥ 70</div></div>
</div>

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
    html += f"<option>{s}</option>\n"

html += """</select>
</div>

<div class="filter-group">
<label for="filtroCategoria">Categoria</label>
<select id="filtroCategoria" onchange="aplicarFiltros()">
<option>Todos</option>
"""

for c in categorias:
    html += f"<option>{c}</option>\n"

html += f"""</select>
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

<div class="card">
<h2>📊 Ranking visual</h2>
<div class="grid">
<div class="grafico-box"><h3>Mais descontadas 🔥</h3><div id="barras-top"></div></div>
<div class="grafico-box"><h3>Blue Chips 🏦</h3><div id="barras-blue"></div></div>
<div class="grafico-box"><h3>Mid Caps 📈</h3><div id="barras-mid"></div></div>
<div class="grafico-box"><h3>Small Caps 🚀</h3><div id="barras-small"></div></div>
</div>
</div>

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
<a href="seo/comparar.html">↔️ Comparar Ações</a>
<a href="seo/simulador-pro.html">📊 Simular carteira de ações</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>

<div class="card" role="region" aria-label="Ranking de ações">
<h2>📋 Ranking</h2>
<p style="color:#22c55e;font-size:13px;margin-bottom:6px">Atualizado hoje • Dados em tempo real</p>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Ranking das ações mais descontadas da bolsa com base em análise fundamentalista.</p>

<div class="aviso-risco" role="note" aria-label="Aviso de risco">
  ⚠️ <span><strong>Atenção:</strong> Este ranking é informativo e educacional. <strong>Não constitui recomendação de investimento.</strong></span>
</div>

<details>
<summary>📊 Como funciona o ranking?</summary>
<div style="font-size:14px;color:#cbd5e1;line-height:1.7;padding:10px 0;">
<p>Utilizamos critérios amplamente usados por investidores de longo prazo:</p>
<ul>
<li><strong>P/L</strong> – quanto o mercado paga pelo lucro</li>
<li><strong>P/VP</strong> – relação preço/patrimônio</li>
<li><strong>ROE</strong> – eficiência da empresa</li>
<li><strong>Dividend Yield</strong> – retorno em dividendos</li>
</ul>
<p>O preço justo utiliza um múltiplo conservador de <strong>P/L = 15</strong>.</p>
<p><a href="missao.html" style="color:#3b82f6">Ver como o Score é calculado →</a></p>
</div>
</details>

<br>

<table role="grid" aria-label="Tabela de ranking de ações">
<caption style="text-align:left;font-size:13px;color:#cbd5e1;margin-bottom:8px;caption-side:top;">
  Ranking das ações mais descontadas — clique no cabeçalho para ordenar
</caption>
<thead>
<tr>
<th scope="col" onclick="ordenarTabela(0)">Ticker ↕</th>
<th scope="col" onclick="ordenarTabela(1)">Setor ↕</th>
<th scope="col" onclick="ordenarTabela(2)">Categoria ↕</th>
<th scope="col" onclick="ordenarTabela(3)">P/L ↕</th>
<th scope="col" onclick="ordenarTabela(4)">P/VP ↕</th>
<th scope="col" onclick="ordenarTabela(5)">ROE ↕</th>
<th scope="col" onclick="ordenarTabela(6)">DY ↕</th>
<th scope="col" onclick="ordenarTabela(7)">Score ↕</th>
<th scope="col" onclick="ordenarTabela(8)">Desconto % ↕</th>
<th scope="col" onclick="ordenarTabela(9)">Preço Justo ↕</th>
<th scope="col">Risco</th>
</tr>
</thead>
<tbody>
"""

for i, (_, row) in enumerate(df.iterrows(), start=1):
    roe     = round((row["ROE"] or 0) * 100, 2)
    dy      = round((row["DivYield"] or 0) * 100, 2)
    desconto = round(row["Desconto_%"], 2)
    medalhas = ["🥇", "🥈", "🥉"]
    icone   = medalhas[i-1] if i <= 3 else ""

    tag = ""
    if row["DivYield"] > 0.08:
        tag = '<span style="background:#22c55e20;color:#22c55e;padding:2px 8px;border-radius:6px;font-size:11px;margin-left:6px;">ALTO DY</span>'

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
<img src="logos/{row['Ticker']}.png"
     alt="Logo {row['Empresa']}"
     loading="lazy"
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

<div class="card" role="region" aria-label="Conteúdo educativo">
<h2>📚 Aprenda análise fundamentalista</h2>
<nav aria-label="Guias educativos" class="menu">
<a href="missao.html">Nossa missão</a>
<a href="fundamentalista.html">O que é análise fundamentalista</a>
<a href="pl.html">O que é P/L</a>
<a href="roe.html">O que é ROE</a>
<a href="dividend-yield.html">O que é Dividend Yield</a>
<a href="estrategia-investidor.html">Como Investir Melhor em Ações</a>
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
<a href="doacoes.html">💚 Apoie o Projeto</a>
</nav>
<div class="footer-copy">© Tá no Precinho, 2026 — Todos os direitos reservados.</div>
</div>
</footer>

<div id="cookie-banner" role="dialog" aria-label="Aviso de cookies" aria-modal="true">
<div class="cookie-box">
<p>Utilizamos cookies para melhorar sua experiência.
<a href="/cookies.html">Política de Cookies</a>.</p>
<div class="cookie-buttons">
<button onclick="aceitarCookies()" class="cookie-accept">Aceitar</button>
<button onclick="recusarCookies()" class="cookie-reject">Recusar</button>
</div>
</div>
</div>

</div>
</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Site atualizado com sucesso.")
