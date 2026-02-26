import yfinance as yf
import pandas as pd
import time

def get_stock_data(tickers):
    dados = []

    for ticker in tickers:
        try:
            acao = yf.Ticker(f"{ticker}.SA")
            info = acao.info

            dados.append({
                "Ticker": ticker,
                "Empresa": info.get("shortName"),
                "Setor": info.get("sector"),
                "PVP": info.get("priceToBook") or 0,
                "PL": info.get("trailingPE") or 0,
                "ROE": info.get("returnOnEquity") or 0,
                "DivYield": info.get("dividendYield") or 0,
                "DebtToEquity": info.get("debtToEquity") or 0,
                "MarketCap": info.get("marketCap") or 0
            })

            time.sleep(0.5)

        except Exception as e:
            print(f"Erro em {ticker}: {e}")

    return pd.DataFrame(dados)