import os
import datetime
import matplotlib.pyplot as plt

from data.market_data import get_stock_data
from analysis.scoring import value_score


# =====================================
# LISTA INICIAL (versão simples)
# =====================================

tickers = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3",
    "WEGE3", "MGLU3", "SUZB3", "RENT3",
    "PRIO3", "GGBR4", "CSNA3",
    "JBSS3", "RADL3", "EQTL3"
]


# =====================================
# COLETA E RANKING
# =====================================

df = get_stock_data(tickers)

df["Score"] = df.apply(value_score, axis=1)
df = df.sort_values("Score", ascending=False)

top10 = df.head(10)


# =====================================
# GARANTIR PASTA DOCS
# =====================================

os.makedirs("docs", exist_ok=True)

hoje = datetime.date.today()
arquivo_csv = f"docs/ranking_{hoje}.csv"

top10.to_csv(arquivo_csv, index=False)


# =====================================
# GERAR GRÁFICO
# =====================================

plt.figure()
plt.bar(top10["Ticker"], top10["Score"])
plt.xticks(rotation=45)
plt.title("Top 10 - Tá no Precinho?")
plt.tight_layout()
plt.savefig("docs/grafico.png")
plt.close()


# =====================================
# GERAR HTML
# =====================================

html = f"""
<html>
<head>
    <meta charset="utf-8">
    <title>Tá no Precinho?</title>
</head>
<body style="font-family: Arial; margin:40px;">

<h1>📉 Tá no Precinho?</h1>

<p>
Site que exibe ações brasileiras negociadas com desconto
segundo métricas fundamentalistas inspiradas em investidores
como Warren Buffett e Luiz Barsi.
</p>

<p><b>Data:</b> {hoje}</p>

<h2>Top 10 Ações com Maior Score</h2>

<table border="1" cellpadding="6" cellspacing="0">
<tr style="background-color:#f2f2f2;">
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
<td>{row.get('Ticker', '')}</td>
<td>{row.get('Setor', '')}</td>
<td>{round(row.get('PL', 0),2)}</td>
<td>{round(row.get('PVP', 0),2)}</td>
<td>{round(row.get('ROE', 0)*100,2)}%</td>
<td>{round(row.get('DivYield', 0)*100,2)}%</td>
<td>{row.get('Score', 0)}</td>
</tr>
"""

html += f"""
</table>

<h2>📊 Gráfico</h2>
<img src="grafico.png" width="700">

<h2>⬇️ Download</h2>
<a href="ranking_{hoje}.csv">Baixar CSV</a>

<hr>
<p style="font-size:12px; color:gray;">
⚠️ Este site não faz recomendação de investimento.
Os dados são públicos e exibidos apenas para fins educacionais.
Cada investidor deve realizar sua própria análise.
</p>

</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)


print("✅ Site gerado com sucesso em /docs")
