import yfinance as yf
import pandas as pd
import time


def get_ibov_tickers():
    """
    Busca automaticamente os códigos do IBOV na Wikipedia
    """
    url = "https://pt.wikipedia.org/wiki/Lista_de_companhias_citadas_no_Ibovespa"
    tables = pd.read_html(url)

    df = tables[0]
    tickers = df["Código"].tolist()

    return tickers


def get_stock_data(tickers):
    dados = []

    for ticker in tickers:
        try:
            acao = yf.Ticker(f"{ticker}.SA")
            info = acao.info

            dados.append({
                "Ticker": ticker,
                "Setor": info.get("sector") or "N/A",
                "PL": info.get("trailingPE") or 0,
                "PVP": info.get("priceToBook") or 0,
                "ROE": info.get("returnOnEquity") or 0,
                "DivYield": info.get("dividendYield") or 0,
                "DebtToEquity": info.get("debtToEquity") or 0,
                "MarketCap": info.get("marketCap") or 0
            })

            time.sleep(0.3)

        except Exception as e:
            print(f"Erro em {ticker}: {e}")

    df = pd.DataFrame(dados)
    df = df.dropna()

    return df