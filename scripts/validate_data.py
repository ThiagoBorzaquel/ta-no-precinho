import pandas as pd


def validar_dados(df):

    if df.empty:
        return df

    colunas_numericas = [
        "PL",
        "PVP",
        "ROE",
        "DivYield",
        "MarketCap",
        "Preco"
    ]

    # garantir tipos numéricos
    for col in colunas_numericas:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # remover NaN críticos
    df = df.dropna(subset=["PL", "PVP", "ROE", "DivYield", "MarketCap", "Preco"])

    # remover valores absurdos
    df = df[
        (df["PL"] > 0) &
        (df["PL"] < 100) &

        (df["PVP"] > 0) &
        (df["PVP"] < 20) &

        (df["ROE"] > -1) &
        (df["ROE"] < 2) &

        (df["DivYield"] >= 0) &
        (df["DivYield"] < 1) &

        (df["MarketCap"] > 100_000_000) &
        (df["Preco"] > 0)
    ]

    return df