import yfinance as yf
import pandas as pd
import time
import os
import datetime
from tqdm import tqdm

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
    "CPLE3","BBDC4","B3SA3","ITUB4","ODPV3","PETR4","ITSA4","ABEV3","PCAR3","QUAL3",
    "CSAN3","COGN3","BBAS3","AZEV4","RAIZ4","PRIO3","AMBP3","USIM5","VALE3","RENT3",
    "VBBR3","CVCB3","GGBR4","VAMO3","RDOR3","RAIL3","CMIG4","CXSE3","AXIA3","PETR3",
    "BBDC3","NATU3","MOTV3","TIMS3","POMO4","BEEF3","MGLU3","ASAI3","VIVT3","CSNA3",
    "MBRF3","JHSF3","BPAC11","HAPV3","GOAU4","CBAV3","LREN3","GMAT3","RADL3","ENEV3",
    "UGPA3","LWSA3","CEAB3","BBSE3","TOTS3","SMFT3","EQTL3","WEGE3","ECOR3","VIVA3",
    "CMIN3","MOVI3","BRAV3","MRVE3","KLBN11","ANIM3","MULT3","GFSA3","GRND3","SUZB3",
    "CYRE3","PGMN3","DIRR3","ALOS3","BHIA3","SBSP3","EMBJ3","MDIA3","LJQQ3","KEPL3",
    "SIMH3","RCSL4","SANB11","RAPT4","AURE3","GGPS3","HBSA3","CPFE3","CSMG3","PLPL3",
    "FLRY3","ITUB3","IGTI11","AZEV3","BMGB4","INTB3","DXCO3","HYPE3","RECV3","ENGI11",
    "ONCO3","HBRE3","VVEO3","SMTO3","CURY3","BRAP4","PSSA3","YDUQ3","SLCE3","EGIE3",
    "CASH3","ISAE4","BRKM5","AXIA6","AUAU3","AXIA7","JSLG3","AZZA3","KLBN4","TOKY3",
    "POSI3","EZTC3","PMAM3","BRSR6","TAEE11","LIGT3","SBFG3","VULC3","SAPR11","ALPA4",
    "SAPR4","AZTE3","PINE4","TEND3","AMER3","IRBR3","MDNE3","SOJA3","SEQL3","PNVL3",
    "DESK3","MYPK3","OIBR3","ARML3","TUPY3","DASA3","HBOR3","TTEN3","ALUP11","RANI3",
    "ORVR3","ALLD3","NEOE3","CSED3","IFCM3","FESA4","CAML3","SEER3","LOGG3","JALL3",
    "POMO3","LAVV3","MLAS3","MILS3","TASA4","ABCB4","USIM3","WIZC3","TFCO4","FIQE3",
    "UNIP6","MTRE3","ESPA3","TGMA3","VTRU3","EVEN3","RNEW4","BMOB3","MELK3","SYNE3",
    "OBTC3","AMAR3","KLBN3","PRNR3","LEVE3","OPCT3","SHUL4","VIVR3","TRIS3","PTBL3",
    "CYRE4","MEAL3","RENT4","VLID3","AGRO3","SAPR3","FICT3","ROMI3","BRST3","BLAU3",
    "BRBI11","PFRM3","VITT3","TCSA3","ENJU3","ALPK3","MATD3","GOAU3","LPSB3","ITSA3",
    "FRAS3","RNEW3","TAEE4","DMVF3","SANB4","LUPA3","JFEN3","RCSL3","CMIG3","ETER3",
    "DEXP3","BRAP3","SANB3","TAEE3","TRAD3","AALR3","PDGR3","FHER3","BEES3","SHOW3",
    "HAGA4","GGBR3","BIOM3","TECN3","TPIS3","ALPA3","BSLI4","BSLI3","AERI3","CSUD3",
    "IGTI3","SCAR3","BMEB4","CAMB3","TASA3","AMOB3","LAND3","AGXY3","EALT4","UCAS3",
    "WEST3","EUCA4","CTAX3","INEP3","AVLL3","PDTC3","HAGA3","CGRA4","CTKA4","BRKM3",
    "WDCN3","ENGI4","BEES4","BPAC5","INEP4","MNPR3","EPAR3","UNIP3","ALUP3","AZEV11",
    "NGRD3","PINE3","DOTZ3","ALUP4","WHRL3","BRSR3","ISAE3","BIED3","WHRL4","PTNT4",
    "BAZA3","ENGI3","TKNO4","BMEB3","LOGN3","VSTE3","COCE5","CRPG5","DOHL4","MTSA4",
    "EQPA3","OFSA3","DEXP4","CEBR6","EMAE4","MNDL3","RAPT3","CLSC4","SNSY5","BPAC3",
    "CTKA3","REDE3","NEXP3","NUTR3","RVEE3","CEBR3","ADMF3","MGEL4","OIBR4","HOOT4",
    "OSXB3","WLMM4","ENMT3","EALT3","RPMG3","ATED3","BMIN4","MWET4","TELB3","TELB4",
    "CEEB3","GSHP3","CEBR5","LUXM4","PATI3","BALM4","CEDO4","BGIP4","CGRA3","PPLA11",
    "UNIP5","FESA3","AFLT3","CTSA4","ARND3","CGAS5","BGIP3","EKTR4","GEPA4","PLAS3",
    "TKNO3","BNBR3","EQMA3B","RPAD6","RSID3","BOBR4","BMKS3","RSUL4","BDLL3","SOND6",
    "PEAB4","PEAB3","CRPG3","EUCA3","BRSR5","CBEE3","AXIA5","ENMT4","CTSA3","BAUH4",
    "CEEB5","SOND5","GEPA3","SNSY3","PTNT3","CLSC3","COCE3","HBTS5","WLMM3","EQPA5",
    "PSVM11","RPAD5","PINE11","GPAR3","NORD3","CGAS3","BRKM6","MRSA5B","BDLL4","CRPG6",
    "ESTR4","CALI3","MERC4","IGTI4","CEED3","BIOM11"
]

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

    pl_justo = 15

    preco_justo = preco * (pl_justo / pl)

    return round(preco_justo, 2)

# =========================
# COLETA FUNDAMENTALISTA
# =========================

from concurrent.futures import ThreadPoolExecutor, as_completed
import random



def get_stock_data(tickers):

    def buscar_ticker(ticker):

        for tentativa in range(3):

            try:
                acao = yf.Ticker(f"{ticker}.SA")
                info = acao.info

                nome = info.get("shortName", ticker)

                market_cap = info.get("marketCap")
                preco = info.get("currentPrice")

                dy = info.get("dividendYield") or 0

                # normalizar dividend yield
                if dy > 1:
                    dy = dy / 100

                if not market_cap or not preco:
                    return None
                
                roe = info.get("returnOnEquity") or 0

                if roe > 1:
                    roe = roe / 100

                setor_original = info.get("sector", "Não informado")

                return {
                        "Ticker": ticker,
                        "Empresa": nome,
                        "setor_original": setor_original,
                        "Setor": traducao_setores.get(setor_original, setor_original),
                        "PL": info.get("trailingPE") or 0,
                        "PVP": info.get("priceToBook") or 0,
                        "ROE": roe,
                        "DivYield": dy,
                        "MarketCap": market_cap,
                        "Preco": preco,
                        "Categoria": classificar_cap(market_cap)
                    }

            except Exception:
                time.sleep(random.uniform(0.3, 0.8))

        return None


    dados = []

    with ThreadPoolExecutor(max_workers=6) as executor:

        futures = [executor.submit(buscar_ticker, t) for t in tickers]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Buscando dados"):
            try:
                resultado = future.result(timeout=10)
                if resultado:
                    dados.append(resultado)
            except:
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


if df.empty:
    print("Nenhuma empresa passou no filtro.")
    exit()

# Score
df["Score"] = df.apply(value_score, axis=1)


# =========================
# ESTATÍSTICAS
# =========================

total_acoes = len(df)

pagadoras_div = len(df[df["DivYield"] > 0])

score_alto = len(df[df["Score"] >= 70])

# Preço justo
df["PrecoJusto"] = df.apply(calcular_preco_justo, axis=1)

# Desconto %
df["Desconto_%"] = df.apply(
    lambda row: (
        ((row["PrecoJusto"] - row["Preco"]) / row["PrecoJusto"]) * 100
        if row["PrecoJusto"] > 0
        else 0
    ),
    axis=1
)

df["Desconto_%"] = df["Desconto_%"].clip(-100, 100)

# Ordenar por maior desconto
df["Ranking"] = (df["Score"] * 0.7) + (df["Desconto_%"] * 0.3)

df = df.sort_values("Ranking", ascending=False)



top10 = df.nlargest(10, "Desconto_%")

top_blue = df[df["Categoria"] == "Blue Chips"].sort_values("Desconto_%", ascending=False).head(5)
top_mid = df[df["Categoria"] == "Mid Caps"].sort_values("Desconto_%", ascending=False).head(5)
top_small = df[df["Categoria"] == "Small Caps"].sort_values("Desconto_%", ascending=False).head(5)


print("Empresas após filtros:", len(df))

total_acoes = len(df)
pagadoras_div = len(df[df["DivYield"] > 0])
score_alto = len(df[df["Score"] >= 70])

print(f"{len(df)} empresas válidas encontradas.")

# =========================
# RISCO
# =========================

def calcular_risco(row):

    risco = 0

    if row["PL"] > 20:
        risco += 1

    if row["PVP"] > 2:
        risco += 1

    if row["DivYield"] < 0.03:
        risco += 1

    if row["ROE"] < 0.12:
        risco += 1

    if risco <= 1:
        return "Baixo"

    if risco <= 3:
        return "Médio"

    return "Alto"

df["Risco"] = df.apply(calcular_risco, axis=1)
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

.stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px,1fr));
    gap: 15px;
    margin-bottom: 25px;
}}

.stat-box {{
    background: var(--card);
    padding: 16px;
    border-radius: 12px;
    text-align: center;
}}

.stat-num {{
    font-size: 22px;
    font-weight: bold;
}}

.stat-label {{
    font-size: 12px;
    color: var(--muted);
}}

</style>

<script>

let ordemAsc = false;

function aplicarFiltros() {{
    let setor = document.getElementById("filtroSetor").value;
    let categoria = document.getElementById("filtroCategoria").value;
    let scoreMin = parseFloat(document.getElementById("filtroScore").value) || 0;
    let quantidade = parseInt(document.getElementById("filtroQuantidade").value);

    let linhas = Array.from(document.querySelectorAll("tbody tr"));

    let filtradas = linhas.filter(linha => {{
        let setorLinha = linha.dataset.setor;
        let categoriaLinha = linha.dataset.categoria;
        let scoreLinha = parseFloat(linha.dataset.score);

        if (setor !== "Todos" && setorLinha !== setor) return false;
        if (categoria !== "Todos" && categoriaLinha !== categoria) return false;
        if (scoreLinha < scoreMin) return false;

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
<div class="stat-num">{total_acoes}</div>
<div class="stat-label">📊 Ações analisadas</div>
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
<th onclick="ordenarTabela(10)">Ranking Score</th>
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

<td>
<strong>{row['Ticker']}</strong><br>
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
<td>{row['Score']}</td>
<td style="color:{'#22c55e' if desconto > 0 else '#ef4444'}">{desconto}%</td>
<td>R$ {round(row["PrecoJusto"],2)}</td>
<td>{round(row["Ranking"],2)}</td>

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