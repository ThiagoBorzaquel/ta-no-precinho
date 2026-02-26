import os
import datetime
import locale
import pandas as pd
import matplotlib.pyplot as plt

from data.market_data import get_stock_data
from analysis.scoring import value_score

# ==============================
# CONFIGURAÇÃO DE DATA BRASIL
# ==============================

hoje = datetime.date.today()
data_formatada = hoje.strftime("%d/%m/%Y")

# ==============================
# LISTA INICIAL (SIMPLIFICADA)
# ==============================

tickers = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3",
    "WEGE3", "MGLU3", "SUZB3", "RENT3",
    "PRIO3", "GGBR4", "CSNA3",
    "JBSS3", "RADL3", "EQTL3"
]

# ==============================
# COLETA DE DADOS
# ==============================

df = get_stock_data(tickers)

# Remove possíveis linhas vazias
df = df.dropna()

# Aplica Score
df["Score"] = df.apply(value_score, axis=1)

# Ordena
df = df.sort_values("Score", ascending=False)

# Top 10
top10 = df.head(10)

# ==============================
# CRIAR PASTA DOCS
# ==============================

os.makedirs("docs", exist_ok=True)

# ==============================
# SALVAR CSV
# ==============================

csv_path = f"docs/ranking_{hoje}.csv"
top10.to_csv(csv_path, index=False)

# ==============================
# GERAR GRÁFICO
# ==============================

plt.figure()
plt.bar(top10["Ticker"], top10["Score"])
plt.xticks(rotation=45)
plt.title("Top 10 - Tá no Precinho?")
plt.tight_layout()
plt.savefig("docs/grafico.png")
plt.close()

# ==============================
# GERAR HTML
# ==============================

html = f"""
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Tá no Precinho?</title>

<style>
body {{
    font-family: Arial, sans-serif;
    margin: 40px;
    background-color: #f4f4f4;
}}

h1 {{
    color: #1e3a8a;
}}

table {{
    border-collapse: collapse;
    background: white;
}}

th {{
    background-color: #1e3a8a;
    color: white;
}}

th, td {{
    padding: 8px 12px;
    text-align: center;
}}

tr:nth-child(even) {{
    background-color: #f2f2f2;
}}

a {{
    color: #1e3a8a;
}}

.disclaimer {{
    margin-top: 40px;
    font-size: 12px;
    color: gray;
}}
</style>
</head>

<body>

<h1>📉 Tá no Precinho?</h1>

<p>
Plataforma educacional que exibe ações brasileiras negociadas com desconto,
com base em métricas fundamentalistas inspiradas na filosofia de investimento
de longo prazo.
</p>

<p><b>Data da atualização:</b> {data_formatada}</p>

<h2>Top 10 Ações com Maior Desconto</h2>

<table border="1">
<tr>
<th>Ticker</th>
<th>Setor</th>
<th>P/L</th>
<th>P/VP</th>
<th>ROE</th>
<th>Dividend Yield</th>
<th>Score</th>
</tr>
"""

for _, row in top10.iterrows():
    html += f"""
<tr>
<td>{row.get('Ticker', '')}</td>
<td>{row.get('Setor', '')}</td>
<td>{round(row.get('PL', 0), 2)}</td>
<td>{round(row.get('PVP', 0), 2)}</td>
<td>{round(row.get('ROE', 0) * 100, 2)}%</td>
<td>{round(row.get('DivYield', 0) * 100, 2)}%</td>
<td>{row.get('Score', 0)}</td>
</tr>
"""

html += f"""
</table>

<h2>Gráfico</h2>
<img src="grafico.png" width="700">

<h2>Download</h2>
<p><a href="ranking_{hoje}.csv">Baixar planilha CSV</a></p>

<div class="disclaimer">
⚠️ Este site não realiza recomendação de investimento.
Os dados apresentados são públicos e possuem finalidade exclusivamente educacional.
O investidor deve realizar sua própria análise antes de qualquer decisão.
</div>

</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Site gerado com sucesso em /docs")