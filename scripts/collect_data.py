import yfinance as yf
import pandas as pd
import random
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator
import time
import random

# =========================
# BUSCAR TICKERS DA B3
# =========================

import requests

# =========================
# BUSCAR TICKERS DA B3
# =========================

def get_b3_tickers():

    try:

        print("Buscando lista de ativos da B3...")

        url = "https://brapi.dev/api/quote/list"
        response = requests.get(url, timeout=10)

        data = response.json()

        tickers = [item["stock"] for item in data["stocks"]]

        # manter apenas ações
        tickers = [t for t in tickers if t.endswith(("3","4","5","6","11"))]

        print(f"{len(tickers)} ativos encontrados.")

        return tickers

    except:

        print("Falha ao buscar API. Usando lista fallback.")

        return []


from deep_translator import GoogleTranslator

# cache simples pra evitar repetir tradução

from deep_translator import GoogleTranslator

def get_stock_data(tickers, traducao_setores, classificar_cap):

    tickers = filtrar_acoes_validas(tickers)

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

                resumo = info.get("longBusinessSummary", "")
                site = info.get("website", "")

                # fallback
                if not resumo:
                    resumo = f"A empresa {info.get('shortName', ticker)} atua no setor de {traducao_setores.get(setor_original, setor_original)}."

                # 🔥 DEBUG (IMPORTANTE)
                print(f"[{ticker}] resumo original:", resumo[:80])

                # tradução
                try:
                    if resumo:
                        resumo_traduzido = GoogleTranslator(source='auto', target='pt').translate(resumo)
                        time.sleep(random.uniform(0.2, 0.5))
                    else:
                        resumo_traduzido = resumo

                except Exception as e:
                    print(f"ERRO tradução {ticker}:", e)
                    resumo_traduzido = resumo

                print(f"[{ticker}] traduzido:", resumo_traduzido[:80])

                return {
                    "Ticker": ticker,
                    "Empresa": info.get("shortName", ticker),
                    "Resumo": resumo_traduzido,
                    "Site": site,
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

            except Exception:
                time.sleep(random.uniform(0.3, 0.8))

        return None

    dados = []

    with ThreadPoolExecutor(max_workers=4) as executor:

        futures = [executor.submit(buscar_ticker, t) for t in tickers]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Buscando dados"):

            try:
                resultado = future.result(timeout=10)

                if resultado:
                    dados.append(resultado)

            except:
                continue

    return pd.DataFrame(dados)
    

    



    
# =========================
# FILTRO DE AÇÕES VÁLIDAS
# =========================

def filtrar_acoes_validas(tickers):

    tickers_validos = []

    for t in tickers:

        if len(t) != 5:
            continue

        if not t[-1].isdigit():
            continue

        if t.endswith(("3","4","5","6")):
            tickers_validos.append(t)

    return list(set(tickers_validos))


# =========================
# COLETA FUNDAMENTALISTA
# =========================

def get_stock_data(tickers, traducao_setores, classificar_cap):

    tickers = filtrar_acoes_validas(tickers)

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

                # normalização
                if dy > 1:
                    dy = dy / 100

                if roe > 1:
                    roe = roe / 100

                setor_original = info.get("sector", "Não informado")
                
                resumo = info.get("longBusinessSummary", "")
                site = info.get("website", "")

                # fallback
                if not resumo:
                    resumo = f"A empresa {info.get('shortName', ticker)} atua no setor de {traducao_setores.get(setor_original, setor_original)}."

                # traduzir para português
                try:
                    if resumo:
                        resumo = GoogleTranslator(source='auto', target='pt').translate(resumo)
                        time.sleep(random.uniform(0.2, 0.5))
                except:
                    pass

                # fallback se não tiver resumo
                if not resumo:
                    resumo = f"A empresa {info.get('shortName', ticker)} atua no setor de {traducao_setores.get(info.get('sector', ''), info.get('sector', 'Não informado'))}."

                return {
                    "Ticker": ticker,
                    "Empresa": info.get("shortName", ticker),
                    "Resumo": resumo,
                    "Site": site,
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
            

            except Exception:

                time.sleep(random.uniform(0.3, 0.8))

        return None


    dados = []

    with ThreadPoolExecutor(max_workers=4) as executor:

        futures = [executor.submit(buscar_ticker, t) for t in tickers]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Buscando dados"):

            try:

                resultado = future.result(timeout=10)

                if resultado:
                    dados.append(resultado)

            except:
                continue

    return pd.DataFrame(dados)