import yfinance as yf
import pandas as pd
import time


# =========================
# LISTA OFICIAL IBOV (FIXA)
# =========================

def get_ibov_tickers():
    return [
        "PETR4","VALE3","ITUB4","BBDC4","BBAS3",
        "WEGE3","MGLU3","SUZB3","RENT3","PRIO3",
        "GGBR4","CSNA3","JBSS3","RADL3","EQTL3",
        "RAIL3","LREN3","ELET3","EMBR3","HAPV3",
        "VIVT3","TIMS3","BRFS3","AZUL4","CMIG4",
        "CPFE3","ENBR3","BRKM5","KLBN11","UGPA3",
        "MULT3","CYRE3","MRVE3","HYPE3","RDOR3"
    ]


# =========================
# COLETA FUNDAMENTALISTA
# =========================

def get_stock_data(tickers):

    dados = []

    for ticker in tickers:
        try:
            acao = yf.Ticker(f"{ticker}.SA")
            info = acao.info

            dados.append({
                "Ticker": ticker,
                "Setor": info.get("sector"),
                "PL": info.get("trailingPE") or 0,
                "PVP": info.get("priceToBook") or 0,
                "ROE": info.get("returnOnEquity") or 0,
                "DivYield": info.get("dividendYield") or 0,
                "MarketCap": info.get("marketCap") or 0
            })

            time.sleep(0.4)

        except Exception as e:
            print(f"Erro em {ticker}: {e}")

    df = pd.DataFrame(dados)
    return df