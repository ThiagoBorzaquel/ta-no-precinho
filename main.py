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

    def add(loc, freq="daily", pri="0.7"):
        urls.append(f"  <url><loc>{loc}</loc><changefreq>{freq}</changefreq><priority>{pri}</priority></url>")

    # HOME
    add(f"{base_url}/", "daily", "1.0")

    # PÁGINAS EDUCATIVAS E LEGAIS — fora do loop, 1x no sitemap
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

    # PÁGINAS DE RANKING FIXAS — fora do loop, 1x no sitemap
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

    # PÁGINAS POR AÇÃO — 1 entrada por ticker
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

gerar_pagina_raiz(
    "pvp",
    "O que é P/VP",
    """
<div style="max-width:700px;margin:auto">

<h2>🏦 O que é P/VP?</h2>

<p>
O indicador <strong>P/VP</strong> significa <strong>Preço sobre Valor Patrimonial</strong>.
Ele mostra quanto o mercado está pagando em relação ao patrimônio líquido da empresa.
</p>

<p>
Em outras palavras: indica se a ação está sendo negociada acima, abaixo ou próxima do valor contábil da empresa.
</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>📊 Como interpretar o P/VP</h3>

<ul>
<li><strong>P/VP &lt; 1</strong> → A ação pode estar barata (negociando abaixo do patrimônio)</li>
<li><strong>P/VP = 1</strong> → Preço próximo ao valor patrimonial</li>
<li><strong>P/VP &gt; 1</strong> → O mercado paga prêmio pela empresa</li>
</ul>

<p>
Exemplo: um P/VP de <strong>0,8</strong> significa que o mercado está pagando R$ 0,80 para cada R$ 1,00 de patrimônio da empresa.
</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>🧠 Quando o P/VP baixo é bom?</h3>

<p>
Um P/VP baixo pode indicar uma oportunidade — mas nem sempre.
</p>

<ul>
<li>✔️ Pode significar ação barata</li>
<li>❌ Pode indicar problemas na empresa</li>
</ul>

<p>
Por isso, o P/VP nunca deve ser analisado sozinho.
</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>⚠️ Cuidados ao usar o P/VP</h3>

<ul>
<li>Bancos e seguradoras → P/VP é muito relevante</li>
<li>Empresas de tecnologia → menos relevante</li>
<li>Empresas com prejuízo → pode distorcer análise</li>
</ul>

<p>
Sempre combine com outros indicadores como:
</p>

<ul>
<li>P/L (Preço sobre Lucro)</li>
<li>ROE (Retorno sobre patrimônio)</li>
<li>Dividend Yield</li>
</ul>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>💡 Resumo simples</h3>

<p>
O P/VP mostra quanto você está pagando pelo patrimônio da empresa.
</p>

<ul>
<li>P/VP baixo → pode ser oportunidade</li>
<li>P/VP alto → mercado enxerga valor ou crescimento</li>
</ul>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>⚠️ Aviso importante</h3>

<p>
Este conteúdo é educativo e <strong>não constitui recomendação de investimento</strong>.
Sempre analise o contexto completo antes de investir.
</p>

<br>

<a href="index.html" style="color:#3b82f6">← Voltar ao ranking</a>

</div>
""",
    descricao="Entenda o que é P/VP (Preço sobre Valor Patrimonial), como interpretar e quando usar esse indicador na análise de ações.",
    keywords="PVP, preço sobre valor patrimonial, análise fundamentalista, ações baratas, valuation"
)

gerar_pagina_raiz(
    "on-pn",
    "Diferença entre ações ON e PN",
    """
<div style="max-width:700px;margin:auto">

<h2>📊 Diferença entre ações ON e PN</h2>

<p>
Na bolsa brasileira, as ações podem ser classificadas em dois tipos principais:
<strong>ON (Ordinárias)</strong> e <strong>PN (Preferenciais)</strong>.
</p>

<p>
A principal diferença entre elas está nos <strong>direitos do acionista</strong>.
</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>🗳️ Ações ON (Ordinárias)</h3>

<p>
As ações ON dão ao investidor o <strong>direito de voto</strong> nas decisões da empresa.
</p>

<ul>
<li>✔️ Direito a voto em assembleias</li>
<li>✔️ Participação nas decisões importantes</li>
<li>✔️ Tag along (proteção em caso de venda da empresa)</li>
</ul>

<p>
Exemplo: PETR3, VALE3, ITUB3
</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>💰 Ações PN (Preferenciais)</h3>

<p>
As ações PN normalmente <strong>não dão direito a voto</strong>, mas oferecem prioridade na distribuição de dividendos.
</p>

<ul>
<li>✔️ Prioridade no recebimento de dividendos</li>
<li>✔️ Menor participação nas decisões</li>
<li>✔️ Geralmente mais líquidas no mercado</li>
</ul>

<p>
Exemplo: PETR4, ITUB4, BBDC4
</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>⚖️ Comparação rápida</h3>

<div style="background:#020617;padding:14px;border-radius:14px">

<div style="display:flex;justify-content:space-between;margin-bottom:8px">
<span>Direito a voto</span>
<strong>ON ✔️ | PN ❌</strong>
</div>

<div style="display:flex;justify-content:space-between;margin-bottom:8px">
<span>Dividendos</span>
<strong>ON normal | PN prioridade</strong>
</div>

<div style="display:flex;justify-content:space-between;margin-bottom:8px">
<span>Liquidez</span>
<strong>ON menor | PN maior</strong>
</div>

</div>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>🧠 Qual é melhor: ON ou PN?</h3>

<p>
Depende do seu objetivo como investidor:
</p>

<ul>
<li>📊 <strong>Quer participar da empresa?</strong> → ON</li>
<li>💰 <strong>Quer mais dividendos?</strong> → PN</li>
</ul>

<p>
Na prática, muitos investidores preferem PN pela liquidez e dividendos,
mas ações ON podem oferecer mais segurança em casos de mudança de controle.
</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>⚠️ Importante: Tag Along</h3>

<p>
O tag along protege o investidor em caso de venda da empresa.
</p>

<ul>
<li>ON → geralmente 100% de tag along</li>
<li>PN → pode ser menor ou inexistente</li>
</ul>

<p>
Isso significa que ações ON costumam ter <strong>mais proteção jurídica</strong>.
</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>💡 Resumo simples</h3>

<ul>
<li>ON = poder de decisão</li>
<li>PN = prioridade em dividendos</li>
</ul>

<p>
Ambas podem ser boas — o importante é analisar a empresa como um todo.
</p>

<hr style="margin:25px 0;border:1px solid #243247;">

<h3>⚠️ Aviso importante</h3>

<p>
Este conteúdo é educativo e <strong>não constitui recomendação de investimento</strong>.
</p>

<br>

<a href="index.html" style="color:#3b82f6">← Voltar ao ranking</a>

</div>
""",
    descricao="Entenda a diferença entre ações ON e PN, direitos de voto, dividendos e qual escolher na bolsa brasileira.",
    keywords="ações ON e PN, diferença ON PN, ações ordinárias e preferenciais, PETR3 PETR4 diferença"
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
         loading="lazy"
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
         loading="lazy"
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

    gerar_pagina(
    "investidores",
    "Maiores investidores da bolsa",
    """
<div style="max-width:900px;margin:auto">

<h1>📚 Maiores investidores da bolsa</h1>

<p style="color:#cbd5e1">
Conheça os maiores investidores da história e aprenda as estratégias que fizeram eles acumularem patrimônio.
</p>

<div class="card">

<h2 style="margin-bottom:12px;">💰 Aprenda com os melhores</h2>

<div style="display:flex;flex-direction:column;gap:10px;">

<a href="barsi-dividendos.html" style="
display:flex;
justify-content:space-between;
align-items:center;
padding:12px 14px;
background:rgba(30,41,59,0.6);
border:1px solid rgba(255,255,255,0.05);
border-radius:10px;
text-decoration:none;
color:#e2e8f0;
transition:0.2s;
">

<span>💸 Luiz Barsi</span>
<span style="font-size:12px;color:#94a3b8;">Dividendos</span>

</a>

<a href="warren-buffett.html" style="
display:flex;
justify-content:space-between;
align-items:center;
padding:12px 14px;
background:rgba(30,41,59,0.6);
border:1px solid rgba(255,255,255,0.05);
border-radius:10px;
text-decoration:none;
color:#e2e8f0;
transition:0.2s;
">

<span>💰 Warren Buffett</span>
<span style="font-size:12px;color:#94a3b8;">Value Investing</span>

</a>

<a href="benjamin-graham.html" style="
display:flex;
justify-content:space-between;
align-items:center;
padding:12px 14px;
background:rgba(30,41,59,0.6);
border:1px solid rgba(255,255,255,0.05);
border-radius:10px;
text-decoration:none;
color:#e2e8f0;
transition:0.2s;
">

<span>📘 Benjamin Graham</span>
<span style="font-size:12px;color:#94a3b8;">Fundamentos</span>

</a>

<a href="peter-lynch.html" style="
display:flex;
justify-content:space-between;
align-items:center;
padding:12px 14px;
background:rgba(30,41,59,0.6);
border:1px solid rgba(255,255,255,0.05);
border-radius:10px;
text-decoration:none;
color:#e2e8f0;
transition:0.2s;
">

<span>📈 Peter Lynch</span>
<span style="font-size:12px;color:#94a3b8;">Crescimento</span>

</a>

</div>

</div>

<div class="card">
<h3>📊 Quer ver ações baratas agora?</h3>
<a href="../index.html" style="display:inline-block;margin-top:10px;padding:12px 18px;background:#22c55e;color:white;border-radius:8px;text-decoration:none;font-weight:600;">
Ver ranking atualizado →
</a>
</div>

<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Explore rankings prontos com as melhores ações da bolsa hoje.</p>
<nav aria-label="Paginas de livros" class="menu">
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

<p>
💸 Luiz Barsi é considerado o maior investidor pessoa física do Brasil.
Sua estratégia é simples e extremamente poderosa: viver de dividendos.
</p>

<p>
Ao longo de décadas, Barsi construiu patrimônio investindo em empresas sólidas,
com foco em geração de caixa e pagamento consistente de dividendos.
</p>

<p>
Sua filosofia não envolve especulação ou tentar prever o mercado.
Ele compra boas empresas e mantém posição por muitos anos.
</p>

<p>
A ideia central é clara:
<strong>construir renda passiva crescente ao longo do tempo.</strong>
</p>

</div>

<div class="card">

<h2>📈 A estratégia de Barsi</h2>

<ul>
<li>Foco em dividendos consistentes</li>
<li>Compra de empresas sólidas</li>
<li>Visão de longo prazo</li>
<li>Reinvestimento dos dividendos</li>
</ul>

<p>
Barsi nunca tentou prever o mercado. Ele apenas acumulou boas empresas ao longo do tempo.
</p>

</div>

<div class="card">

<h2>🧠 O segredo</h2>

<p>
O maior diferencial de Barsi não foi inteligência fora da curva.
Foi disciplina.
</p>

<p>
Enquanto a maioria tenta ganhar dinheiro rápido, ele focou em renda passiva consistente.
</p>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Quer aprender direto com ele?</h2>

<p>
Se você quer entender exatamente como Barsi pensa e investe, esse é o melhor ponto de partida:
</p>

<a href="https://amzn.to/47rV2Vj" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro recomendado
</a>

<p style="font-size:12px;color:#94a3b8;margin-top:10px">
*Link de afiliado — você apoia o projeto sem pagar nada a mais
</p>

</div>

<div class="card">

<h3>📊 Veja ações com dividendos agora</h3>

<a href="../index.html" style="display:inline-block;margin-top:10px;padding:12px 18px;background:#3b82f6;color:white;border-radius:8px;text-decoration:none;font-weight:600;">
Ver ranking →
</a>

</div>

<<div class="card">
<h2>O Basico de todo investidor</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Antes de escolher ações, os melhores investidores dominam o essencial:
mentalidade, disciplina e visão de longo prazo.</p>
<nav aria-label="O Basico de todo investidor" class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>

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

<p>
Warren Buffett é conhecido como o maior investidor da história.
Ele construiu sua fortuna aplicando os princípios do value investing.
</p>

<p>
Buffett busca empresas sólidas, com vantagem competitiva e boa gestão,
comprando apenas quando estão abaixo do valor justo.
</p>

<p>
Ele evita riscos desnecessários e acredita que o tempo é o maior aliado do investidor.
</p>

<p>
Sua frase mais famosa resume bem sua estratégia:
<strong>"Se você não pretende manter uma ação por 10 anos, não compre por 10 minutos."</strong>
</p>

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

<p>
Se você quer entender exatamente como Buffet pensa e investe, esse é o melhor ponto de partida:
</p>

<a href="https://amzn.to/4uT0Lh0" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro do Warren Buffett
</a>

</div>

<div class="card">
<a href="../index.html">← Ver ranking de ações</a>
</div>

<<div class="card">
<h2>O Basico de todo investidor</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Antes de escolher ações, os melhores investidores dominam o essencial:
mentalidade, disciplina e visão de longo prazo.</p>
<nav aria-label="O Basico de todo investidor" class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>

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

<p>
Benjamin Graham foi o criador da análise fundamentalista moderna
e mentor de Warren Buffett.
</p>

<p>
Ele desenvolveu o conceito de comprar ações abaixo do valor justo,
utilizando uma margem de segurança para reduzir riscos.
</p>

<p>
Graham via o mercado como emocional e irracional no curto prazo,
mas eficiente no longo prazo.
</p>

<p>
Seu ensinamento principal:
<strong>o preço é o que você paga, o valor é o que você recebe.</strong>
</p>

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

<div class="card">

<h2>📊 O conceito de margem de segurança</h2>

<p>
Graham defendia que o investidor deve comprar ativos com desconto em relação ao valor justo.
Isso reduz risco e aumenta o potencial de retorno.
</p>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Quer aprender direto com ele?</h2>

<p>
Se você quer entender exatamente como Graham pensa e investe, esse é o melhor ponto de partida:
</p>


<a href="https://amzn.to/4bMAYOV" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro do Benjamin Graham
</a>

</div>

<div class="card">
<a href="../index.html">📊 Ver ações baratas agora →</a>
</div>

<<div class="card">
<h2>O Basico de todo investidor</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Antes de escolher ações, os melhores investidores dominam o essencial:
mentalidade, disciplina e visão de longo prazo.</p>
<nav aria-label="O Basico de todo investidor" class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>

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

<p>
Peter Lynch ficou famoso por mostrar que qualquer pessoa pode investir bem,
desde que observe o mundo ao seu redor.
</p>

<p>
Sua estratégia é baseada em identificar empresas que fazem parte do seu dia a dia
antes que o mercado perceba seu potencial.
</p>

<p>
Ele acredita que investidores comuns têm vantagem,
pois conseguem enxergar tendências no consumo antes dos grandes fundos.
</p>

<p>
A ideia principal é simples:
<strong>invista em negócios que você entende.</strong>
</p>

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

<div class="card">

<h2>🔍 Exemplo prático</h2>

<p>
Se você percebe que uma marca está crescendo e sendo cada vez mais usada,
isso pode ser um sinal de oportunidade.
</p>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Quer aprender direto com ele?</h2>

<p>
Se você quer entender exatamente como Lynch pensa e investe, esse é o melhor ponto de partida:
</p>

<a href="https://amzn.to/47rVy5H" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro do Peter Lynch
</a>

</div>

<div class="card">
<a href="../index.html">📊 Ver ranking de ações →</a>
</div>

<div class="card">
<h2>O Basico de todo investidor</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Antes de escolher ações, os melhores investidores dominam o essencial:
mentalidade, disciplina e visão de longo prazo.</p>
<nav aria-label="O Basico de todo investidor" class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>

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

<p style="color:#cbd5e1">
A escola prepara as crianças para o mundo real? Essa é a primeira pergunta com a qual o leitor se depara neste livro. O recado é ousado e direto: boa formação e notas altas não bastam para assegurar o sucesso de alguém. O mundo mudou; a maioria dos jovens tem cartão de crédito, antes mesmo de concluir os estudos, e nunca teve aula sobre dinheiro, investimentos, juros etc. Ou seja, eles vão para a escola, mas continuam financeiramente improficientes, despreparados para enfrentar um mundo que valoriza mais as despesas do que a poupança.

Para o autor, o conselho mais perigoso que se pode dar a um jovem nos dias de hoje é: “Vá para a escola, tire notas altas e depois procure um trabalho seguro.” O fato é que agora as regras são outras, e não existe mais emprego garantido para ninguém. Pai Rico, Pai Pobre demonstra que a questão não é ser empregado ou empregador, mas ter o controle do próprio destino ou delegá-lo a alguém. É essa a tese de Robert Kiyosaki neste livro substancial e visionário. Para ele, a formação proporcionada pelo sistema educacional não prepara os jovens para o mundo que encontrarão depois de formados.
</p>

<div class="card">

<h2>🧠 Principais ensinamentos</h2>

<ul>
<li>Ativos colocam dinheiro no bolso</li>
<li>Passivos tiram dinheiro do bolso</li>
<li>Trabalhe para aprender, não só para ganhar</li>
<li>Construa renda passiva</li>
</ul>

</div>

<div class="card">

<h2>💡 Mentalidade</h2>

<p>
O livro mostra a diferença entre pensar como pobre e pensar como rico.
</p>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Comece por aqui</h2>

<a href="https://amzn.to/3Pte87v" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro
</a>

</div>

<div class="card">
<a href="../index.html">📊 Ver ações para investir →</a>
</div>

<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Explore rankings prontos com as melhores ações da bolsa hoje.</p>
<nav aria-label="Paginas de livros" class="menu">
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

<p style="color:#cbd5e1">
Baseando-se nos segredos de sucesso dos antigos babilônicos ― os habitantes da cidade mais rica e próspera de seu tempo ―, George S. Clason mostra soluções ao mesmo tempo sábias e muito atuais para evitar a falta de dinheiro, como não desperdiçar recursos durante tempos de opulência, buscar conhecimento e informação em vez de apenas lucro, assegurar uma renda para o futuro, manter a pontualidade no pagamento de dívidas e, sobretudo, cultivar as próprias aptidões, tornando-se cada vez mais habilidoso e consciente.
</p>

<div class="card">

<h2>💰 Regras clássicas</h2>

<ul>
<li>Pague a si mesmo primeiro</li>
<li>Controle seus gastos</li>
<li>Faça seu dinheiro trabalhar</li>
<li>Proteja seu patrimônio</li>
</ul>

</div>

<div class="card">

<h2>📊 Por que funciona?</h2>

<p>
Porque os princípios são simples, mas consistentes ao longo do tempo.
</p>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Leitura essencial</h2>

<a href="https://amzn.to/4dKRSjp" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro
</a>

</div>

<div class="card">
<a href="../index.html">📊 Ver oportunidades na bolsa →</a>
</div>

<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Explore rankings prontos com as melhores ações da bolsa hoje.</p>
<nav aria-label="Rpaginas de livros" class="menu">
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

<p style="color:#cbd5e1">
"T. Harv Eker desmistifica o motivo pelo qual algumas pessoas estão destinadas à riqueza e outras a uma vida de dureza. Se você quer conhecer as causas fundamentais do sucesso, leia este livro." – Robert G. Allen, autor de O milionário em um minuto


Se as suas finanças andam na corda bamba, talvez esteja na hora de você refletir sobre o que T. Harv Eker chama de "o seu modelo de dinheiro" – um conjunto de crenças que cada um de nós alimenta desde a infância e que molda o nosso destino financeiro, quase sempre nos levando para uma situação difícil.

Nesse livro, Eker mostra como substituir uma mentalidade destrutiva – que você talvez nem perceba que tem – pelos "arquivos de riqueza", 17 modos de pensar e agir que distinguem os ricos das demais pessoas. Alguns desses princípios fundamentais são:

• Ou você controla o seu dinheiro ou ele controlará você.

• O hábito de administrar as finanças é mais importante do que a quantidade de dinheiro que você tem.

• A sua motivação para enriquecer é crucial: se ela possui uma raiz negativa, como o medo, a raiva ou a necessidade de provar algo a si mesmo, o dinheiro nunca lhe trará felicidade.

• O segredo do sucesso não é tentar evitar os problemas nem se livrar deles, mas crescer pessoalmente para se tornar maior do que qualquer adversidade.

• Os gastos excessivos têm pouco a ver com o que você está comprando e tudo a ver com a falta de satisfação na sua vida.

O autor também ensina um método eficiente de administrar o dinheiro. Você aprenderá a estabelecer sua remuneração pelos resultados que apresenta e não pelas horas que trabalha. Além disso, saberá como aumentar o seu patrimônio líquido – a verdadeira medida da riqueza.

A ideia é fazer o seu dinheiro trabalhar para você tanto quanto você trabalha para ele. Para isso, é necessário poupar e investir em vez de gastar. "Enriquecer não diz respeito somente a ficar rico em termos financeiros", diz Eker. "É mais do que isso: trata-se da pessoa que você se torna para alcançar esse objetivo."
</p>

<div class="card">

<h2>🧠 Ideia central</h2>

<p>
Seu resultado financeiro é reflexo do seu modelo mental.
</p>

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
👉 Ver livro
</a>

</div>

<div class="card">
<a href="../index.html">📊 Ver ranking de ações →</a>
</div>

<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Explore rankings prontos com as melhores ações da bolsa hoje.</p>
<nav aria-label="paginas de livros" class="menu">
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
<link rel="canonical" href="https://tanoprecinho.site/">
<meta name="robots" content="index, follow">
<meta property="og:title" content="Tá no Precinho? - Ranking de ações brasileiras">
<meta property="og:description" content="Descubra quais ações podem estar baratas hoje segundo análise fundamentalista.">
<meta property="og:image" content="https://tanoprecinho.site/images/og-image.jpg">
<title>Tá no Precinho? | Ranking de ações da bolsa brasileira</title>
<script defer src="https://cdn.jsdelivr.net/npm/chart.js"></script>

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

// Aplicar filtros assim que o DOM estiver pronto, sem esperar imagens/scripts
document.addEventListener("DOMContentLoaded", function() {{
    if ("requestIdleCallback" in window) {{
        requestIdleCallback(aplicarFiltros);
    }} else {{
        setTimeout(aplicarFiltros, 1);
    }}
}});

// Carregar gráficos só quando ficarem visíveis (IntersectionObserver)
// Evita bloquear o LCP com Chart.js no carregamento inicial
var graficosCarregados = {{}};

var graficosData = {{
    "graficoTop10": {{ labels: {list(top10["Ticker"])}, data: {list(top10["Desconto_%"])}, cor: "#ef4444" }},
    "graficoBlue":  {{ labels: {list(top_blue["Ticker"])}, data: {list(top_blue["Desconto_%"])}, cor: "#3b82f6" }},
    "graficoMid":   {{ labels: {list(top_mid["Ticker"])}, data: {list(top_mid["Desconto_%"])}, cor: "#22c55e" }},
    "graficoSmall": {{ labels: {list(top_small["Ticker"])}, data: {list(top_small["Desconto_%"])}, cor: "#facc15" }}
}};

document.addEventListener("DOMContentLoaded", function() {{
    if (!("IntersectionObserver" in window)) {{
        // Fallback para browsers antigos
        Object.keys(graficosData).forEach(function(id) {{
            var g = graficosData[id];
            criarGrafico(id, g.labels, g.data, g.cor);
        }});
        return;
    }}

    var observer = new IntersectionObserver(function(entries) {{
        entries.forEach(function(entry) {{
            if (entry.isIntersecting && !graficosCarregados[entry.target.id]) {{
                graficosCarregados[entry.target.id] = true;
                var g = graficosData[entry.target.id];
                if (g) criarGrafico(entry.target.id, g.labels, g.data, g.cor);
                observer.unobserve(entry.target);
            }}
        }});
    }}, {{ rootMargin: "200px" }});

    ["graficoTop10", "graficoBlue", "graficoMid", "graficoSmall"].forEach(function(id) {{
        var el = document.getElementById(id);
        if (el) observer.observe(el);
    }});
}});

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

document.addEventListener("DOMContentLoaded", verificarCookies);

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
  <a href="pvp.html">O que é P/VP</a>
  <a href="roe.html">O que é ROE</a>
  <a href="on-pn.html">Diferença entre ações ON e PN</a>
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
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
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

<details>
<summary>📊 Como funciona o ranking?</summary>
<div style="font-size:14px;color:#cbd5e1;line-height:1.7;padding:10px 0;">
<p>Este site analisa automaticamente centenas de ações da bolsa brasileira e organiza tudo em um ranking simples.</p>
<p>Utilizamos critérios amplamente usados por investidores de longo prazo:</p>
<ul>
<li><strong>P/L</strong> – quanto o mercado paga pelo lucro</li>
<li><strong>P/VP</strong> – relação preço/patrimônio</li>
<li><strong>ROE</strong> – eficiência da empresa</li>
<li><strong>Dividend Yield</strong> – retorno em dividendos</li>
</ul>
<p>O preço justo utiliza um múltiplo conservador de <strong>P/L = 15</strong>, ajustado por setor.</p>
<p>Quanto maior o desconto e melhor o score, maior a posição no ranking.</p>
<p><a href="missao.html" style="color:#3b82f6">Ver como o Score é calculado →</a></p>
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