import yfinance as yf
import pandas as pd
import random
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_stock_data(tickers, traducao_setores, classificar_cap):

    def buscar_ticker(ticker):

        for tentativa in range(3):

            try:

                acao = yf.Ticker(f"{ticker}.SA")

                fast = acao.fast_info
                info = acao.info

                preco = fast.get("lastPrice")
                market_cap = fast.get("marketCap")

                if not preco or not market_cap:
                    return None

                dy = info.get("dividendYield") or 0
                roe = info.get("returnOnEquity") or 0

                if dy > 1:
                    dy = dy / 100

                if roe > 1:
                    roe = roe / 100

                setor_original = info.get("sector", "Não informado")

                return {
                    "Ticker": ticker,
                    "Empresa": info.get("shortName", ticker),
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

            except:
                time.sleep(random.uniform(0.3,0.8))

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