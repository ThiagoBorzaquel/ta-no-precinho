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