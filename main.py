import yfinance as yf
import pandas as pd
import time
import os
import datetime

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
        return "Large Cap"
    elif market_cap >= 10_000_000_000:
        return "Mid Cap"
    else:
        return "Small Cap"

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
                "Setor": info.get("sector", "Não informado"),
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

top10 = df.head(10)

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
body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
}}

.container {{
    max-width: 1200px;
    margin: auto;
    padding: 40px 20px;
}}

h1 {{
    font-size: 32px;
}}

.subtitle {{
    color: #94a3b8;
    margin-bottom: 25px;
}}

.card {{
    background: #1e293b;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 25px;
}}

.filters {{
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
}}

select, input {{
    padding: 8px;
    border-radius: 6px;
    border: none;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th {{
    background: #334155;
    padding: 10px;
    cursor: pointer;
}}

td {{
    padding: 8px;
    text-align: center;
}}

tr:nth-child(even) {{
    background: #1e293b;
}}

.green {{
    color: #22c55e;
    font-weight: bold;
}}

.red {{
    color: #ef4444;
    font-weight: bold;
}}

.footer {{
    margin-top: 40px;
    font-size: 13px;
    color: #64748b;
}}
</style>

<script>
function aplicarFiltros() {{
    let setor = document.getElementById("filtroSetor").value;
    let categoria = document.getElementById("filtroCategoria").value;
    let descontoMin = parseFloat(document.getElementById("filtroDesconto").value) || -999;

    let linhas = document.querySelectorAll("tbody tr");

    linhas.forEach(linha => {{
        let setorLinha = linha.dataset.setor;
        let categoriaLinha = linha.dataset.categoria;
        let descontoLinha = parseFloat(linha.dataset.desconto);

        let mostrar = true;

        if (setor !== "Todos" && setorLinha !== setor)
            mostrar = false;

        if (categoria !== "Todos" && categoriaLinha !== categoria)
            mostrar = false;

        if (descontoLinha < descontoMin)
            mostrar = false;

        linha.style.display = mostrar ? "" : "none";
    }});
}}

function ordenarTabela(coluna) {{
    let tabela = document.getElementById("tabela");
    let linhas = Array.from(tabela.rows).slice(1);

    let asc = tabela.dataset.sortAsc === "true";
    tabela.dataset.sortAsc = !asc;

    linhas.sort((a, b) => {{
        let valA = a.cells[coluna].innerText.replace("R$ ","").replace("%","");
        let valB = b.cells[coluna].innerText.replace("R$ ","").replace("%","");

        return asc ? valA - valB : valB - valA;
    }});

    linhas.forEach(l => tabela.appendChild(l));
}}
</script>

</head>

<body>

<div class="container">

<h1>📉 Tá no Precinho?</h1>
<div class="subtitle">
Ações com estimativa de preço justo<br>
Atualizado em {data_br}
</div>

<div class="card">
<div class="filters">

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
<label>Desconto mínimo (%)</label><br>
<input type="number" id="filtroDesconto" onchange="aplicarFiltros()">
</div>

</div>
</div>

<div class="card">
<h2>🏆 Top 10 Maiores Descontos</h2>
<canvas id="grafico"></canvas>
</div>

<div class="card">
<h2>📊 Ranking Completo</h2>
<table id="tabela" data-sort-asc="false">
<thead>
<tr>
<th onclick="ordenarTabela(0)">Ticker</th>
<th onclick="ordenarTabela(1)">Preço</th>
<th onclick="ordenarTabela(2)">Preço Justo</th>
<th onclick="ordenarTabela(3)">Desconto %</th>
<th onclick="ordenarTabela(4)">Categoria</th>
<th onclick="ordenarTabela(5)">Score</th>
</tr>
</thead>
<tbody>
"""

for _, row in df.iterrows():
    desconto_class = "green" if row["Desconto_%"] > 0 else "red"

    html += f"""
<tr data-setor="{row['Setor']}" data-categoria="{row['Categoria']}" data-desconto="{row['Desconto_%']}">
<td><strong>{row['Ticker']}</strong></td>
<td>R$ {round(row['Preco'],2)}</td>
<td>R$ {row['PrecoJusto']}</td>
<td class="{desconto_class}">{row['Desconto_%']}%</td>
<td>{row['Categoria']}</td>
<td>{row['Score']}</td>
</tr>
"""

html += f"""
</tbody>
</table>
</div>

<div class="footer">
⚠️ Modelo simplificado. Não é recomendação.
<br>
<a href="ranking_{hoje}.csv" style="color:#38bdf8;">Baixar CSV</a>
</div>

</div>

<script>
new Chart(document.getElementById('grafico'), {{
    type: 'bar',
    data: {{
        labels: {list(top10["Ticker"])},
        datasets: [{{
            label: 'Desconto %',
            data: {list(top10["Desconto_%"])},
        }}]
    }},
    options: {{
        responsive: true,
        scales: {{
            y: {{ beginAtZero: true }}
        }}
    }}
}});
</script>

</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Site atualizado com preço justo e desconto.")