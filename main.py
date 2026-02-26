
import yfinance as yf
import pandas as pd
import time
import os
import matplotlib.pyplot as plt
import datetime


# =========================
# LISTA IBOV (FIXA)
# =========================

def get_ibov_tickers():
    return [
        "PETR4","VALE3","ITUB4","BBDC4","BBAS3",
        "WEGE3","MGLU3","SUZB3","RENT3","PRIO3",
        "GGBR4","CSNA3","JBSS3","RADL3","EQTL3",
        "RAIL3","LREN3","ELET3","EMBR3","HAPV3",
        "VIVT3","TIMS3","BRFS3","AZUL4","CMIG4",
        "CPFE3","UGPA3","MULT3","CYRE3","HYPE3"
    ]


# =========================
# COLETA DADOS
# =========================

def get_stock_data(tickers):

    dados = []

    for ticker in tickers:
        try:
            acao = yf.Ticker(f"{ticker}.SA")
            info = acao.info

            dados.append({
                "Ticker": ticker,
                "Setor": info.get("sector"),
                "PL": info.get("trailingPE") or 0,
                "PVP": info.get("priceToBook") or 0,
                "ROE": info.get("returnOnEquity") or 0,
                "DivYield": info.get("dividendYield") or 0,
                "MarketCap": info.get("marketCap") or 0
            })

            time.sleep(0.4)

        except Exception as e:
            print(f"Erro em {ticker}: {e}")

    return pd.DataFrame(dados)


# =========================
# SCORE (SIMPLIFICADO)
# =========================

def calculate_score(row):

    score = 0

    if row["PL"] > 0 and row["PL"] < 10:
        score += 2

    if row["PVP"] > 0 and row["PVP"] < 1.5:
        score += 2

    if row["ROE"] > 0.15:
        score += 2

    if row["DivYield"] > 0.05:
        score += 2

    return score


# =========================
# EXECUÇÃO PRINCIPAL
# =========================

print("Buscando dados do IBOV...")

tickers = get_ibov_tickers()
df = get_stock_data(tickers)

df["Score"] = df.apply(calculate_score, axis=1)
df = df.sort_values("Score", ascending=False)

top10 = df.head(10)

# =========================
# DATA
# =========================

hoje = datetime.date.today()
data_br = hoje.strftime("%d/%m/%Y")

# =========================
# CRIAR PASTA DOCS
# =========================

os.makedirs("docs", exist_ok=True)

csv_path = f"docs/ranking_{hoje}.csv"
top10.to_csv(csv_path, index=False)

# =========================
# GRÁFICO
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
# HTML PROFISSIONAL
# =========================

html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Tá no Precinho?</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 40px;
    background-color: #f4f6f9;
}}

h1 {{
    color: #1f2937;
}}

table {{
    border-collapse: collapse;
    width: 100%;
    background: white;
}}

th, td {{
    padding: 10px;
    text-align: center;
}}

th {{
    background-color: #111827;
    color: white;
}}

tr:nth-child(even) {{
    background-color: #f2f2f2;
}}

.footer {{
    margin-top: 40px;
    font-size: 14px;
    color: #6b7280;
}}
</style>
</head>

<body>

<h1>📉 Tá no Precinho?</h1>

<p>
Plataforma que exibe ações do IBOVESPA negociadas com maior desconto
segundo métricas fundamentalistas inspiradas em Value Investing.
</p>

<p><strong>Data da atualização:</strong> {data_br}</p>

<h2>🏆 Top 10 Ações com Maior Score</h2>

<table>
<tr>
<th>Ticker</th>
<th>Setor</th>
<th>P/L</th>
<th>P/VP</th>
<th>ROE</th>
<th>Div Yield</th>
<th>Score</th>
</tr>
"""

for _, row in top10.iterrows():

    roe = round((row["ROE"] or 0) * 100, 2)
    dy = round((row["DivYield"] or 0) * 100, 2)

    html += f"""
<tr>
<td>{row["Ticker"]}</td>
<td>{row["Setor"] or "-"}</td>
<td>{round(row["PL"],2)}</td>
<td>{round(row["PVP"],2)}</td>
<td>{roe}%</td>
<td>{dy}%</td>
<td><strong>{row["Score"]}</strong></td>
</tr>
"""

html += f"""
</table>

<h2>📊 Visualização</h2>
<img src="grafico.png" width="700">

<h2>⬇️ Download</h2>

Thiago Borzaquel, [26/02/2026 13:18]
<p><a href="ranking_{hoje}.csv">Baixar ranking em CSV</a></p>

<div class="footer">
⚠️ Este site não constitui recomendação de investimento.  
Dados públicos com finalidade exclusivamente educacional.
</div>

</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Site gerado com sucesso em /docs")