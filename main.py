import yfinance as yf
import pandas as pd
import time
import os
import datetime
import matplotlib.pyplot as plt

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

    if row["PL"] > 0 and row["PL"] < 10:
        score += 25

    if row["PVP"] > 0 and row["PVP"] < 1.5:
        score += 25

    if row["ROE"] > 0.15:
        score += 20

    if row["DivYield"] > 0.05:
        score += 15

    if row["MarketCap"] > 10_000_000_000:
        score += 15

    return score

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

            if not market_cap:
                continue

            dados.append({
                "Ticker": ticker,
                "Setor": info.get("sector", "Não informado"),
                "PL": info.get("trailingPE") or 0,
                "PVP": info.get("priceToBook") or 0,
                "ROE": info.get("returnOnEquity") or 0,
                "DivYield": info.get("dividendYield") or 0,
                "MarketCap": market_cap,
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
    print("Nenhum dado válido encontrado. Encerrando execução.")
    exit()

df["Score"] = df.apply(value_score, axis=1)
df = df.sort_values("Score", ascending=False)

top10 = df.head(10)

# =========================
# PREPARAR PASTA DOCS
# =========================

os.makedirs("docs", exist_ok=True)

hoje = datetime.date.today()
data_br = hoje.strftime("%d/%m/%Y")

csv_path = f"docs/ranking_{hoje}.csv"
df.to_csv(csv_path, index=False)

# =========================
# GERAR GRÁFICO
# =========================

plt.figure(figsize=(10,5))
plt.bar(top10["Ticker"], top10["Score"])
plt.xticks(rotation=45)
plt.title("Top 10 - Tá no Precinho?")
plt.tight_layout()
plt.savefig("docs/grafico.png")
plt.close()

print("Gráfico gerado.")

# =========================
# GERAR HTML
# =========================

setores_unicos = sorted(df["Setor"].dropna().unique())

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
    margin-bottom: 5px;
}}

.subtitle {{
    color: #94a3b8;
    margin-bottom: 30px;
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
}}

td {{
    padding: 8px;
    text-align: center;
}}

tr:nth-child(even) {{
    background: #1e293b;
}}

.badge {{
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 12px;
    background: #2563eb;
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
    let scoreMin = parseFloat(document.getElementById("filtroScore").value) || 0;

    let linhas = document.querySelectorAll("tbody tr");

    linhas.forEach(linha => {{
        let setorLinha = linha.getAttribute("data-setor");
        let categoriaLinha = linha.getAttribute("data-categoria");
        let scoreLinha = parseFloat(linha.getAttribute("data-score"));

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
</script>

</head>
<body>

<div class="container">

<h1>📉 Tá no Precinho?</h1>
<div class="subtitle">
Ações do IBOV negociadas com desconto segundo métricas fundamentalistas.
<br>Atualizado em {data_br}
</div>

<div class="card">
<div class="filters">
    <div>
        <label>Setor</label><br>
        <select id="filtroSetor" onchange="aplicarFiltros()">
            <option>Todos</option>
"""

for s in setores_unicos:
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
<h2>🏆 Top 10 Score</h2>
<canvas id="grafico"></canvas>
</div>

<div class="card">
<h2>📊 Ranking Completo</h2>
<table>
<thead>
<tr>
<th>Ticker</th>
<th>Setor</th>
<th>Categoria</th>
<th>P/L</th>
<th>P/VP</th>
<th>ROE</th>
<th>DY</th>
<th>Score</th>
</tr>
</thead>
<tbody>
"""

for _, row in df.iterrows():
    roe = round((row["ROE"] or 0) * 100, 2)
    dy = round((row["DivYield"] or 0) * 100, 2)

    html += f"""
<tr data-setor="{row['Setor']}" data-categoria="{row['Categoria']}" data-score="{row['Score']}">
<td><strong>{row['Ticker']}</strong></td>
<td>{row['Setor']}</td>
<td><span class="badge">{row['Categoria']}</span></td>
<td>{round(row['PL'],2)}</td>
<td>{round(row['PVP'],2)}</td>
<td>{roe}%</td>
<td>{dy}%</td>
<td><strong>{row['Score']}</strong></td>
</tr>
"""

html += f"""
</tbody>
</table>
</div>

<div class="footer">
⚠️ Não constitui recomendação de investimento. Dados públicos para fins educacionais.
<br>
<a href="ranking_{hoje}.csv" style="color:#38bdf8;">Baixar CSV</a>
</div>

</div>

<script>
const ctx = document.getElementById('grafico');

new Chart(ctx, {{
    type: 'bar',
    data: {{
        labels: {list(top10["Ticker"])},
        datasets: [{{
            label: 'Score',
            data: {list(top10["Score"])},
            borderWidth: 1
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
</script>

</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Site gerado com sucesso em /docs")