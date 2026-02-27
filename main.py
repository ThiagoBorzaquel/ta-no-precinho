import yfinance as yf
import pandas as pd
import time
import os
import datetime

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
# LISTA IBOV (fixa segura)
# =========================

def get_ibov_tickers():
  return [
        "AALR3","ABCB4","ABEV3","ADMF3","AERI3","AGRO3","ALUP11","AMER3","AZUL4","B3SA3","BBAS3","BBSE3","BBDC4","BPAC11","BRAP4","BRFS3","BRKM5","BEEF3","CAML3","CCRO3","CIEL3","CMIN3","COGN3","CPFE3","CPLE6","CSAN3","CYRE3","DXCO3","ELET3","ELET6","EMBR3","ENGI11","ENEV3","EGIE3","FLRY3","GGBR4","GOAU4","HAPV3","IGTA3","IRBR3","ITAU4","ITSA4","JBSS3", "KLBN11", "LAME4", "LREN3", "MGLU3", "MRVE3", "MULT3", "PARD3", "PCAR3", "PETR3", "PETR4", "PRIO3", "RADL3", "RAIZ4", "RENT3", "SULA11", "SUZB3", "TAEE11", "TOTS3", "TRPL4", "UGPA3", "USIM5", "VALE3", "VIVT3", "WEGE3", "YDUQ2"

    ]

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
# SCORE VALUE
# =========================

def value_score(row):
    score = 0

    if 0 < row["PL"] < 10:
        score += 25

    if 0 < row["PVP"] < 1.5:
        score += 25

    if row["ROE"] > 0.15:
        score += 20

    if row["DivYield"] > 0.05:
        score += 15

    if row["MarketCap"] > 10_000_000_000:
        score += 15

    return score

# =========================
# PREÇO JUSTO
# =========================

def calcular_preco_justo(row):

    preco = row["Preco"]
    pl = row["PL"]

    if preco <= 0 or pl <= 0:
        return 0

    pl_justo = 15  # múltiplo conservador

    preco_justo = preco * (pl_justo / pl)

    return round(preco_justo, 2)

# =========================
# COLETA FUNDAMENTALISTA
# =========================

def get_stock_data(tickers):

    dados = []

    for ticker in tickers:
        try:
            acao = yf.Ticker(f"{ticker}.SA")
            info = acao.info

            market_cap = info.get("marketCap")
            preco = info.get("currentPrice")

            if not market_cap or not preco:
                continue

            dados.append({
                "Ticker": ticker,
                "setor_original": info.get("sector", "Não informado"),
                "Setor": traducao_setores.get(info.get("sector", "Não informado"), info.get("sector", "Não informado")),
                "PL": info.get("trailingPE") or 0,
                "PVP": info.get("priceToBook") or 0,
                "ROE": info.get("returnOnEquity") or 0,
                "DivYield": info.get("dividendYield") or 0,
                "MarketCap": market_cap,
                "Preco": preco,
                "Categoria": classificar_cap(market_cap)
            })

            time.sleep(0.3)

        except Exception:
            continue

    return pd.DataFrame(dados)

# =========================
# EXECUÇÃO PRINCIPAL
# =========================

print("Buscando dados do IBOV...")

tickers = get_ibov_tickers()
df = get_stock_data(tickers)

if df.empty:
    print("Nenhum dado válido encontrado.")
    exit()

# Score
df["Score"] = df.apply(value_score, axis=1)

# Preço justo
df["PrecoJusto"] = df.apply(calcular_preco_justo, axis=1)

# Desconto %
df["Desconto_%"] = (
    (df["PrecoJusto"] - df["Preco"]) / df["PrecoJusto"]
) * 100

df["Desconto_%"] = df["Desconto_%"].round(2)

# Ordenar por maior desconto
df = df.sort_values("Desconto_%", ascending=False)

top10 = df.sort_values("Desconto_%", ascending=False).head(10)

top_blue = df[df["Categoria"] == "Blue Chips"].sort_values("Desconto_%", ascending=False).head(5)
top_mid = df[df["Categoria"] == "Mid Caps"].sort_values("Desconto_%", ascending=False).head(5)
top_small = df[df["Categoria"] == "Small Caps"].sort_values("Desconto_%", ascending=False).head(5)

# =========================
# GERAR SITE
# =========================

os.makedirs("docs", exist_ok=True)

hoje = datetime.date.today()
data_br = hoje.strftime("%d/%m/%Y")

df.to_csv(f"docs/ranking_{hoje}.csv", index=False)

setores = sorted(df["Setor"].unique())
categorias = sorted(df["Categoria"].unique())

# =========================
# HTML SaaS Moderno
# =========================

setores = sorted(df["Setor"].unique())
categorias = sorted(df["Categoria"].unique())

html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tá no Precinho?</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

:root {{
    --bg: #0f172a;
    --card: #1e293b;
    --card-light: #0f172a;
    --accent: #3b82f6;
    --text: #e2e8f0;
    --muted: #94a3b8;
}}

body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
}}

.container {{
    max-width: 1200px;
    margin: auto;
    padding: 25px 16px;
}}

h1 {{
    font-size: 26px;
    margin-bottom: 5px;
}}

.subtitle {{
    color: var(--muted);
    margin-bottom: 25px;
    font-size: 14px;
}}

.card {{
    background: var(--card);
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 20px;
}}

.filters {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}}

select, input {{
    padding: 8px;
    border-radius: 8px;
    border: none;
    font-size: 14px;
}}

.table-wrapper {{
    overflow-x: auto;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 900px;
}}

th {{
    background: #334155;
    padding: 10px;
    cursor: pointer;
    position: relative;
    font-size: 14px;
}}

th span {{
    font-size: 10px;
    margin-left: 5px;
    opacity: 0.6;
}}

th.active span {{
    opacity: 1;
    color: var(--accent);
}}

td {{
    padding: 8px;
    text-align: center;
    font-size: 13px;
}}

tr:nth-child(even) {{
    background: var(--card-light);
}}

.badge {{
    padding: 4px 8px;
    border-radius: 8px;
    font-size: 11px;
    background: var(--accent);
}}

.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 15px;
}}

.grafico-box {{
    background: var(--card-light);
    padding: 12px;
    border-radius: 12px;
}}

.footer {{
    margin-top: 30px;
    font-size: 12px;
    color: var(--muted);
    text-align: center;
}}

@media(max-width: 600px) {{
    h1 {{
        font-size: 22px;
    }}

    .filters {{
        flex-direction: column;
    }}

    select, input {{
        width: 100%;
    }}
}}

</style>

<script>

let ordemAsc = false;

function aplicarFiltros() {{
    let setor = document.getElementById("filtroSetor").value;
    let categoria = document.getElementById("filtroCategoria").value;
    let scoreMin = parseFloat(document.getElementById("filtroScore").value) || 0;

    let linhas = document.querySelectorAll("tbody tr");

    linhas.forEach(linha => {{
        let setorLinha = linha.dataset.setor;
        let categoriaLinha = linha.dataset.categoria;
        let scoreLinha = parseFloat(linha.dataset.score);

        let mostrar = true;

        if (setor !== "Todos" && setorLinha !== setor)
            mostrar = false;

        if (categoria !== "Todos" && categoriaLinha !== categoria)
            mostrar = false;

        if (scoreLinha < scoreMin)
            mostrar = false;

        linha.style.display = mostrar ? "" : "none";
    }});
}}

function ordenarTabela(coluna, thElement) {{
    let tabela = document.querySelector("tbody");
    let linhas = Array.from(tabela.querySelectorAll("tr"));

    ordemAsc = !ordemAsc;

    document.querySelectorAll("th").forEach(th => th.classList.remove("active"));
    thElement.classList.add("active");

    linhas.sort((a, b) => {{
        let valA = a.children[coluna].innerText.replace('%','').replace(',','.');
        let valB = b.children[coluna].innerText.replace('%','').replace(',','.');

        return ordemAsc 
            ? parseFloat(valA) - parseFloat(valB)
            : parseFloat(valB) - parseFloat(valA);
    }});

    linhas.forEach(l => tabela.appendChild(l));
}}

</script>

</head>
<body>

<div class="container">

<h1>📉 Tá no Precinho?</h1>
<div class="subtitle">
Ações do IBOV negociadas com desconto segundo métricas fundamentalistas.<br>
Atualizado em {data_br}
</div>

<div class="card">
<div class="filters">

<div>
<label>Setor</label><br>
<select id="filtroSetor" onchange="aplicarFiltros()">
<option>Todos</option>
"""

for s in sorted(df["Setor"].unique()):
    html += f"<option>{s}</option>"

html += """
</select>
</div>

<div>
<label>Categoria</label><br>
<select id="filtroCategoria" onchange="aplicarFiltros()">
<option>Todos</option>
"""

for c in sorted(df["Categoria"].unique()):
    html += f"<option>{c}</option>"

html += """
</select>
</div>

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
<h3>Top 10 Geral</h3>
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

<div class="table-wrapper">
<table>
<thead>
<tr>
<th onclick="ordenarTabela(0,this)">Ticker</th>
<th onclick="ordenarTabela(1,this)">Setor</th>
<th onclick="ordenarTabela(2,this)">Categoria</th>
<th onclick="ordenarTabela(3,this)">P/L <span>↕</span></th>
<th onclick="ordenarTabela(4,this)">P/VP <span>↕</span></th>
<th onclick="ordenarTabela(5,this)">ROE <span>↕</span></th>
<th onclick="ordenarTabela(6,this)">DY <span>↕</span></th>
<th onclick="ordenarTabela(7,this)">Score <span>↕</span></th>
<th onclick="ordenarTabela(8,this)">Desconto % <span>↕</span></th>
</tr>
</thead>
<tbody>
"""

for _, row in df.iterrows():
    roe = round((row["ROE"] or 0) * 100, 2)
    dy = round((row["DivYield"] or 0) * 100, 2)
    desconto = round(row["Desconto_%"], 2)

    html += f"""
<tr data-setor="{row['Setor']}" data-categoria="{row['Categoria']}" data-score="{row['Score']}">
<td><strong>{row['Ticker']}</strong></td>
<td>{row['Setor']}</td>
<td><span class="badge">{row['Categoria']}</span></td>
<td>{round(row['PL'],2)}</td>
<td>{round(row['PVP'],2)}</td>
<td>{roe}%</td>
<td>{dy}%</td>
<td>{row['Score']}</td>
<td>{desconto}%</td>
</tr>
"""

html += f"""
</tbody>
</table>
</div>
</div>

<div class="footer">
⚠️ Não constitui recomendação de investimento.<br>
<a href="ranking_{hoje}.csv" style="color:#3b82f6;">Baixar CSV</a>
</div>

</div>

<script>

function criarGrafico(id, labels, data) {{
    new Chart(document.getElementById(id), {{
        type: 'bar',
        data: {{
            labels: labels,
            datasets: [{{
                data: data
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{ y: {{ beginAtZero: true }} }}
        }}
    }});
}}

criarGrafico("graficoTop10",
{list(top10["Ticker"])},
{list(top10["Desconto_%"])}
);

criarGrafico("graficoBlue",
{list(top_blue["Ticker"])},
{list(top_blue["Desconto_%"])}
);

criarGrafico("graficoMid",
{list(top_mid["Ticker"])},
{list(top_mid["Desconto_%"])}
);

criarGrafico("graficoSmall",
{list(top_small["Ticker"])},
{list(top_small["Desconto_%"])}
);

</script>

</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Site atualizado com preço justo e desconto.")