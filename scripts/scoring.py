# múltiplos razoáveis por setor
SETOR_PL = {

    "Serviços Financeiros": 8,
    "Energia": 10,
    "Utilidades Públicas": 12,
    "Materiais Básicos": 10,
    "Consumo Cíclico": 12,
    "Consumo Defensivo": 14,
    "Saúde": 15,
    "Indústria": 12,
    "Tecnologia": 20,
    "Comunicação": 15,
    "Imobiliário": 12
}

SETOR_PVP = {

    "Serviços Financeiros": 1.5,
    "Energia": 1.2,
    "Utilidades Públicas": 1.3,
    "Materiais Básicos": 1.5,
    "Consumo Cíclico": 2,
    "Consumo Defensivo": 2,
    "Saúde": 2.5,
    "Indústria": 2,
    "Tecnologia": 4,
    "Comunicação": 2,
    "Imobiliário": 1
}


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
    pvp = row["PVP"]
    roe = row["ROE"]
    setor = row["Setor"]

    if preco <= 0:
        return 0

    pl_setor = SETOR_PL.get(setor, 12)
    pvp_setor = SETOR_PVP.get(setor, 1.5)

    # preço justo por PL
    if pl > 0:
        preco_pl = preco * (pl_setor / pl)
    else:
        preco_pl = preco

    # preço justo por PVP
    if pvp > 0:
        preco_pvp = preco * (pvp_setor / pvp)
    else:
        preco_pvp = preco

    # bônus por ROE alto
    fator_roe = 1 + (roe * 0.5)

    preco_justo = ((preco_pl + preco_pvp) / 2) * fator_roe

    # limitar distorções
    if preco_justo > preco * 3:
        preco_justo = preco * 3

    if preco_justo < preco * 0.5:
        preco_justo = preco * 0.5

    return round(preco_justo, 2)


# =========================
# DESCONTO
# =========================

def calcular_desconto(row):

    preco = row["Preco"]
    preco_justo = row["PrecoJusto"]

    if preco <= 0 or preco_justo <= 0:
        return 0

    desconto = ((preco_justo / preco) - 1) * 100

    return max(min(desconto, 100), -80)


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


# =========================
# Farol risco
# =========================

def farol_risco(risco):
    if risco == "Baixo":
        return "🟢"
    elif risco == "Médio":
        return "🟡"
    else:
        return "🔴"
    return "⚪"

# =========================
# Qualidade
# =========================

def score_qualidade(row):

    score = 0

    if row["ROE"] > 0.20:
        score += 30
    elif row["ROE"] > 0.15:
        score += 20

    if row["DivYield"] > 0.06:
        score += 20
    elif row["DivYield"] > 0.03:
        score += 10

    if row["PVP"] < 1:
        score += 20
    elif row["PVP"] < 1.5:
        score += 10

    if row["MarketCap"] > 10_000_000_000:
        score += 10

    return score

# =========================
# Valuation
# =========================

def score_valuation(row):

    desconto = row["Desconto_%"]

    if desconto > 50:
        return 40
    elif desconto > 30:
        return 30
    elif desconto > 15:
        return 20
    elif desconto > 5:
        return 10
    else:
        return 0
    
# =========================
# Calcular Ranking
# =========================
def calcular_ranking(row):

    qualidade = score_qualidade(row)
    valuation = score_valuation(row)

    ranking = qualidade * 0.6 + valuation * 0.4

    return ranking

# =========================
# Carregar histórico 
# =========================
import pandas as pd
import os
from datetime import datetime, timedelta

def carregar_historico(periodo_dias):

    pasta = "data/history"

    arquivos = sorted(os.listdir(pasta))

    hoje = datetime.today()
    limite = hoje - timedelta(days=periodo_dias)

    dados = []

    for arquivo in arquivos:

        if not arquivo.endswith(".csv"):
            continue

        data_str = arquivo.replace("valuation_", "").replace(".csv", "")
        data = datetime.strptime(data_str, "%Y-%m-%d")

        if data >= limite:

            df = pd.read_csv(os.path.join(pasta, arquivo))
            df["Data"] = data
            dados.append(df)

    if not dados:
        return pd.DataFrame()

    return pd.concat(dados)

