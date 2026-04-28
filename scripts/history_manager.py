import os
import datetime


def salvar_historico(df):

    os.makedirs("data/history", exist_ok=True)

    hoje = datetime.date.today().isoformat()

    caminho = f"data/history/valuation_{hoje}.csv"

    df.to_csv(caminho, index=False)

    print(f"Histórico salvo: {caminho}")