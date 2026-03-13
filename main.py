import yfinance as yf
import pandas as pd
import time
import os
import datetime
from tqdm import tqdm
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from scripts.collect_data import get_stock_data
from scripts.validate_data import validar_dados
from scripts.scoring import value_score
from scripts.scoring import calcular_preco_justo
from scripts.scoring import calcular_desconto
from scripts.scoring import calcular_risco, farol_risco
from scripts.scoring import calcular_ranking
from scripts.logger import logger
from scripts.logo_manager import preparar_logos
from scripts.collect_data import get_b3_tickers, get_stock_data,filtrar_acoes_validas
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



# =========================
# LISTA IBOV
# =========================


cores_categoria = {
    "Blue Chips": "#3b82f6",   # azul
    "Mid Caps": "#22c55e",     # verde
    "Small Caps": "#facc15"    # amarelo
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


# remover duplicados
tickers = sorted(set(tickers))


logger.info(f"{len(tickers)} Ativos encontrados para análise.")

universo_b3 = len(tickers)

print("Ações filtradas:", universo_b3)

# =========================
# COLETA FUNDAMENTALISTA
# =========================

df = get_stock_data(tickers, traducao_setores, classificar_cap)

logger.info(f"{len(df)} empresas coletadas com dados fundamentalistas.")

df = validar_dados(df)

logger.info(f"{len(df)} empresas com dados válidos após validação.")

acoes_coletadas = len(df)

if df.empty:
    print("Nenhum dado válido encontrado.")
    exit()



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

# =========================
# ESTATÍSTICAS
# =========================

total_acoes = len(df)

pagadoras_div = len(df[df["DivYield"] > 0])

score_alto = len(df[df["Score"] >= 70])

# Preço justo
df["LucroPorAcao"] = df["Preco"] / df["PL"]
df["PrecoJusto"] = df["LucroPorAcao"] * 15  # múltiplo conservador de P/L = 15


# Desconto %
df["Desconto_%"] = df.apply(calcular_desconto, axis=1)

# Ordenar por maior desconto

df["Ranking"] = df.apply(calcular_ranking, axis=1)

# calcular histórico primeiro

historico = carregar_historico(365)

# depois filtrar
top_n = 100
df = df.nlargest(top_n, "Desconto_%")



# Risco
df["Risco"] = df.apply(calcular_risco, axis=1)

df["Farol"] = df["Risco"].apply(farol_risco)

def garantir_colunas(df):

    colunas = [
        "Desconto_%",
        "Ranking",
        "Risco",
        "Farol"
    ]

    for c in colunas:
        if c not in df.columns:
            df[c] = 0

    return df

# Salvar historico
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

# baixar e preparar logos
preparar_logos(df)

# garantir colunas para o site
df = garantir_colunas(df)

top10 = df.nlargest(5, "Desconto_%")

top_blue = df[df["Categoria"] == "Blue Chips"].sort_values("Desconto_%", ascending=False).head(5)
top_mid = df[df["Categoria"] == "Mid Caps"].sort_values("Desconto_%", ascending=False).head(5)
top_small = df[df["Categoria"] == "Small Caps"].sort_values("Desconto_%", ascending=False).head(5)


print("Empresas após filtros:", len(df))

total_acoes = len(df)
pagadoras_div = len(df[df["DivYield"] > 0])
score_alto = len(df[df["Score"] >= 70])

print(f"{len(df)} empresas válidas encontradas.")



# =========================
# GERAR SITE
# =========================


os.makedirs("docs", exist_ok=True)

hoje = datetime.date.today()
data_br = hoje.strftime("%d/%m/%Y")

df.to_csv("docs/ranking.csv", index=False)

setores = sorted(df["Setor"].unique())
categorias = sorted(df["Categoria"].unique())

top3 = df.head(3)

logger.info("Gerando site...")

# =========================
# HTML SaaS Moderno
# =========================

setores = sorted(df["Setor"].unique())
categorias = sorted(df["Categoria"].unique())

html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<script async
src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=SEU_ID"
crossorigin="anonymous"></script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tá no Precinho?</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

:root{{
    --bg:#0f172a;
    --card:#1e293b;
    --card-light:#0f172a;
    --accent:#3b82f6;
    --text:#e2e8f0;
    --muted:#94a3b8;
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

h1{{
    margin-top:0;
}}

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
}}

.table-wrapper{{
    overflow-x:auto;
}}

table{{
    width:100%;
    border-collapse:collapse;
}}

th{{
    background:#334155;
    padding:10px;
    cursor:pointer;
    font-size:14px;
}}

td{{
    padding:8px;
    text-align:center;
    font-size:13px;
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

canvas{{
    max-height:250px;
}}

.footer{{
    margin-top:30px;
    font-size:12px;
    color:var(--muted);
    text-align:center;
}}

.metric-grid{{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:6px;
}}

.secondary{{
    font-size:11px;
    color:var(--muted);
}}

.ranking-card{{
    max-width:340px;
    margin:12px auto;
    padding:14px;
    border-radius:12px;
}}

.ranking-grid{{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:6px;
    font-size:12px;
}}

.ranking-title{{
    font-size:14px;
    margin-bottom:6px;
}}

.ranking-company{{
    font-size:11px;
    color:#94a3b8;
}}

.ranking-info{{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:6px;
    font-size:12px;
}}

.ranking-info div{{
    display:flex;
    justify-content:space-between;
}}

/* MOBILE */

@media(max-width:768px){{

h1{{
    font-size:22px;
}}

.subtitle{{
    font-size:13px;
}}

.filters{{
    grid-template-columns:1fr;
}}

select,input{{
    width:100%;
    padding:10px;
}}

thead{{
    display:none;
}}

table,tbody,tr,td{{
    display:block;
    width:100%;
}}

tr{{
    background:var(--card);
    margin-bottom:14px;
    padding:14px;
    border-radius:14px;
    box-shadow:0 4px 14px rgba(0,0,0,0.35);
}}

td{{
    display:flex;
    justify-content:space-between;
    padding:6px 0;
    font-size:13px;
}}

td:first-child{{
    display:block;
    font-size:16px;
    font-weight:bold;
    margin-bottom:6px;
    text-align:left;
}}

td:nth-child(4)::before{{content:"P/L";}}
td:nth-child(5)::before{{content:"P/VP";}}
td:nth-child(6)::before{{content:"ROE";}}
td:nth-child(7)::before{{content:"Dividend Yield";}}
td:nth-child(8)::before{{content:"Score";}}
td:nth-child(9)::before{{content:"Desconto";}}
td:nth-child(10)::before{{content:"Preço justo";}}
td:nth-child(11)::before{{content:"Risco";}}

td::before{{
    font-weight:600;
    color:var(--muted);
}}

}}

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

    filtradas.slice(0, quantidade).forEach(l => {{
        l.style.display = "";
    }});

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
            datasets: [{{
                data: data,
                backgroundColor: cor,
                borderRadius: 6
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ 
                legend: {{ display: false }} 
            }},
            scales: {{ 
                y: {{ beginAtZero: true }} 
            }}
        }}
    }});
}}



window.onload = function() {{
    criarGrafico("graficoTop10",
    {list(top10["Ticker"])},
    {list(top10["Desconto_%"])},
    "#ef4444"   // vermelho destaque
);

criarGrafico("graficoBlue",
    {list(top_blue["Ticker"])},
    {list(top_blue["Desconto_%"])},
    "#3b82f6"
);

criarGrafico("graficoMid",
    {list(top_mid["Ticker"])},
    {list(top_mid["Desconto_%"])},
    "#22c55e"
);

criarGrafico("graficoSmall",
    {list(top_small["Ticker"])},
    {list(top_small["Desconto_%"])},
    "#facc15"
);

    aplicarFiltros();
}};



</script>

</head>

<meta name="description" content="Ranking automático das ações brasileiras mais baratas baseado em análise fundamentalista. Atualizado diariamente.">

<meta name="keywords" content="ações baratas, bolsa brasileira, value investing, ranking ações, B3">

<meta property="og:title" content="Tá no Precinho? - Ranking de ações brasileiras">
<meta property="og:description" content="Descubra quais ações podem estar baratas hoje segundo análise fundamentalista.">
<meta property="og:image" content="https://ta-noprecinho.com/images/og-image.jpg">

<body>

<div class="container">

<h1>📉 Tá no Precinho?</h1>

<div class="subtitle">
Este site analisa automaticamente centenas de ações da bolsa brasileira e identifica empresas que podem estar sendo negociadas abaixo do valor justo com base em indicadores fundamentalistas.
O ranking utiliza métricas como:
• P/L
• P/VP
• ROE
• Dividend Yield
<br>
Atualizado automaticamente todos os dias.
<br>
<br>
Atualizado em {data_br}
</div>

<div class="stats">

<div class="stat-box">
<div class="stat-num">{universo_b3}</div>
<div class="stat-label">📊 Universo B3</div>
</div>

<div class="stat-box">
<div class="stat-num">{acoes_analisadas}</div>
<div class="stat-label">🔎 Ações analisadas</div>
</div>

<div class="stat-box">
<div class="stat-num">{pagadoras_div}</div>
<div class="stat-label">💰 Pagadoras de dividendos</div>
</div>

<div class="stat-box">
<div class="stat-num">{score_alto}</div>
<div class="stat-label">🏆 Score ≥ 70</div>
</div>

</div>

<div class="card">
<div class="filters">

<div>
<label>Quantidade</label><br>
<select id="filtroQuantidade" onchange="aplicarFiltros()">
<option value="20" selected>20</option>
<option value="30">30</option>
<option value="40">40</option>
<option value="50">50</option>
<option value="100">100</option>
<option value="9999">Todos</option>
</select>
</div>

<div>
<label>Setor</label><br>
<select id="filtroSetor" onchange="aplicarFiltros()">
<option>Todos</option>
"""

for s in setores:
    html += f"<option>{s}</option>"


html += """
</select>
</div>

<div>
<label>Categoria</label><br>
<select id="filtroCategoria" onchange="aplicarFiltros()">
<option>Todos</option>
"""


for c in categorias:
    html += f"<option>{c}</option>"

html += """
</select>
</div>

<div>
<label>Período</label><br>
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
"""

html += """


<div>
<label>Score mínimo</label><br>
<input type="number" id="filtroScore" onchange="aplicarFiltros()" placeholder="Ex: 50">
</div>


</div>
</div>

<div class="card">
<h2>📊 Gráficos</h2>
<div class="grid">

<div class="grafico-box">
<h3>Mais descontadas do dia🔥</h3>
<canvas id="graficoTop10"></canvas>
</div>

<div class="grafico-box">
<h3>Blue Chips</h3>
<canvas id="graficoBlue"></canvas>
</div>

<div class="grafico-box">
<h3>Mid Caps</h3>
<canvas id="graficoMid"></canvas>
</div>

<div class="grafico-box">
<h3>Small Caps</h3>
<canvas id="graficoSmall"></canvas>
</div>

</div>
</div>

<div class="card">
<h2>📋 Ranking</h2>

<div class="card">

<h3>📊 Como funciona o ranking?</h3>

<p style="font-size:13px;color:#94a3b8;line-height:1.6">

O ranking utiliza um score fundamentalista baseado em métricas de valor:

<br><br>

• P/L abaixo de 10<br>
• P/VP abaixo de 1.5<br>
• ROE acima de 15%<br>
• Dividend Yield acima de 5%<br>
• Market Cap acima de 1 bilhão

<br><br>

O preço justo é estimado utilizando um múltiplo conservador de <strong>P/L = 15</strong>.

<br>

O desconto mostra quanto a ação está negociando abaixo desse preço estimado.

</p>


</div>

<table>
<thead>
<tr>
<th onclick="ordenarTabela(0)">Ticker</th>
<th onclick="ordenarTabela(1)">Setor</th>
<th onclick="ordenarTabela(2)">Categoria</th>
<th onclick="ordenarTabela(3)">P/L</th>
<th onclick="ordenarTabela(4)">P/VP</th>
<th onclick="ordenarTabela(5)">ROE</th>
<th onclick="ordenarTabela(6)">DY</th>
<th onclick="ordenarTabela(7)">Score</th>
<th onclick="ordenarTabela(8)">Desconto %</th>
<th onclick="ordenarTabela(9)">Preço Justo</th>
<th>Risco</th>


</tr>
</thead>
<tbody>
"""

for i, (_, row) in enumerate(df.iterrows(), start=1):

    roe = round((row["ROE"] or 0) * 100, 2)
    dy = round((row["DivYield"] or 0) * 100, 2)
    desconto = round(row["Desconto_%"], 2)


    html += f"""
    
<tr data-setor="{row['Setor']}"
    data-categoria="{row['Categoria']}"
    data-score="{row['Score']}"
    data-variacao="{row['Variacao_%']}">

<td>
<span style="color:#94a3b8;font-size:12px">#{i}</span>
<div style="display:flex;align-items:center;gap:8px">

<img src="logos/{row['Ticker']}.png"
onerror="this.onerror=null;this.src='logos/default.svg';"
style="width:20px;height:20px;object-fit:contain">

<strong>{row['Ticker']}</strong>

</div>
<span style="font-size:11px;color:#94a3b8">{row['Empresa']}</span>
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
<td style="color:{'#22c55e' if desconto > 0 else '#ef4444'}">{desconto}%</td>
<td>R$ {round(row["PrecoJusto"],2)}</td>
<td title="{row['Risco']}" style="text-align:center;">
<span style="font-size:18px;display:inline-block;">
{row["Farol"]}
</span>
</td>
 

</tr>
"""

html += f"""
</tbody>
</table>

<div class="footer">
⚠️ Este ranking utiliza dados públicos do Yahoo Finance e aplica critérios quantitativos próprios. Não constitui recomendação de investimento.<br>
<a href="ranking.csv" style="color:#3b82f6;">Baixar CSV</a>
</div>
<div class="footer">
<footer>
        <span>
            &copy; Tá no precinho?, 2026 - Todos os direitos reservados.
        </span>
    </footer>

</div>

</body>
</html>
"""



with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Site atualizado com preço justo e desconto.")