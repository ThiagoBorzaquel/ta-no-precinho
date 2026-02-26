import os
import datetime
import pandas as pd
import matplotlib.pyplot as plt

from data.market_data import get_stock_data
from analysis.scoring import value_score

# =====================
# LISTA INICIAL SIMPLES
# =====================

tickers = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3",
    "WEGE3", "MGLU3", "SUZB3", "RENT3",
    "PRIO3", "GGBR4", "CSNA3",
    "JBSS3", "RADL3", "EQTL3"
]

# =====================
# COLETA
# =====================

df = get_stock_data(tickers)
df["Score"] = df.apply(value_score, axis=1)
df = df.sort_values("Score", ascending=False)

top10 = df.head(10)

# =====================
# CRIAR PASTA DOCS
# =====================

os.makedirs("docs", exist_ok=True)

hoje = datetime.date.today()
csv_path = f"docs/ranking_{hoje}.csv"
arquivo = f"docs/ranking_value_{hoje}.csv"
top20.to_csv(arquivo, index=False)

# =====================
# GERAR GRÁFICO
# =====================

plt.figure()
plt.bar(top10["Ticker"], top10["Score"])
plt.xticks(rotation=45)
plt.title("Top 10 - Tá no Precinho?")
plt.tight_layout()
plt.savefig("docs/grafico.png")
plt.close()

# =====================
# GERAR HTML
# =====================

html = f"""
<html>
<head>
    <title>Tá no Precinho?</title>
</head>
<body>

<h1>📉 Tá no Precinho?</h1>

<p>
Site com ações brasileiras negociadas com desconto
segundo métricas fundamentalistas.
</p>

<p><b>Data:</b> {hoje}</p>

<h2>Top 10</h2>

<table border="1" cellpadding="5">
<tr>
<th>Ticker</th>
<th>Setor</th>
<th>PL</th>
<th>PVP</th>
<th>ROE</th>
<th>DY</th>
<th>Score</th>
</tr>
"""

for _, row in top10.iterrows():
    html += f"""
<tr>
<td>{row['Ticker']}</td>
<td>{row['Setor']}</td>
<td>{round(row['PL'],2)}</td>
<td>{round(row['PVP'],2)}</td>
<td>{round(row['ROE']*100,2)}%</td>
<td>{round(row['DivYield']*100,2)}%</td>
<td>{row['Score']}</td>
</tr>
"""

html += f"""
</table>

<h2>Gráfico</h2>
<img src="grafico.png" width="600">

<h2>Download</h2>
<a href="ranking_{hoje}.csv">Baixar CSV</a>

<hr>
<p>
⚠️ Este site não faz recomendação de investimento.
Dados públicos com finalidade educacional.
</p>

</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Site gerado com sucesso em /docs")