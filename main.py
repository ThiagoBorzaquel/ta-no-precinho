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
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Tá no Precinho?</title>

<style>
body {{
    font-family: Arial, sans-serif;
    background-color: #0f172a;
    color: #e2e8f0;
    margin: 0;
    padding: 40px;
}}

h1 {{
    color: #38bdf8;
    font-size: 40px;
}}

h2 {{
    margin-top: 40px;
    color: #f8fafc;
}}

.card {{
    background-color: #1e293b;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 30px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}}

th {{
    background-color: #1e293b;
    padding: 12px;
    text-align: left;
}}

td {{
    padding: 10px;
    border-bottom: 1px solid #334155;
}}

tr:hover {{
    background-color: #1e293b;
}}

.score-high {{
    color: #22c55e;
    font-weight: bold;
}}

.score-mid {{
    color: #facc15;
    font-weight: bold;
}}

.score-low {{
    color: #ef4444;
    font-weight: bold;
}}

.footer {{
    margin-top: 60px;
    font-size: 14px;
    color: #94a3b8;
}}

.button {{
    display: inline-block;
    background-color: #38bdf8;
    color: #0f172a;
    padding: 10px 18px;
    border-radius: 8px;
    text-decoration: none;
    font-weight: bold;
    margin-top: 15px;
}}

.button:hover {{
    background-color: #0ea5e9;
}}
</style>
</head>

<body>

<h1>📉 Tá no Precinho?</h1>

<div class="card">
<p>
Radar de ações brasileiras negociadas com desconto segundo métricas
fundamentalistas inspiradas em grandes investidores de valor.
</p>

<p><strong>Data da atualização:</strong> {hoje}</p>
</div>

<h2>Top 10 Ações Mais Descontadas</h2>

<div class="card">

<table>
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

    score_class = "score-low"
    if row["Score"] >= 50:
        score_class = "score-high"
    elif row["Score"] >= 30:
        score_class = "score-mid"

    html += f"""
<tr>
<td><strong>{row['Ticker']}</strong></td>
<td>{row['Setor']}</td>
<td>{round(row['PL'],2)}</td>
<td>{round(row['PVP'],2)}</td>
<td>{round(row['ROE']*100,2)}%</td>
<td>{round(row['DivYield']*100,2)}%</td>
<td class="{score_class}">{row['Score']}</td>
</tr>
"""

html += f"""
</table>

<a class="button" href="ranking_{hoje}.csv">Baixar CSV Completo</a>

</div>

<h2>Gráfico</h2>
<div class="card">
<img src="grafico.png" width="100%">
</div>

<div class="footer">
⚠️ Este site não faz recomendação de investimento.
Dados públicos utilizados para fins educacionais.
Decisões de investimento são de responsabilidade do investidor.
</div>

</body>
</html>
"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)


print("✅ Site gerado com sucesso em /docs")
