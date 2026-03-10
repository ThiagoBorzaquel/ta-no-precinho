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
# DESCONTO
# =========================

def calcular_desconto(row):

    preco = row["Preco"]
    preco_justo = row["PrecoJusto"]

    if preco_justo <= 0:
        return 0

    desconto = ((preco_justo - preco) / preco_justo) * 100

    return desconto


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