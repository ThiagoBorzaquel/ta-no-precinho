def value_score(row):
    score = 0

    if row["PL"] > 0 and row["PL"] < 10:
        score += 25

    if row["PVP"] > 0 and row["PVP"] < 1.5:
        score += 20

    if row["ROE"] > 0.15:
        score += 20

    if row["DivYield"] > 0.05:
        score += 15

    if row["DebtToEquity"] < 150:
        score += 10

    if row["MarketCap"] > 10_000_000_000:
        score += 10

    return score