import yfinance as yf
import pandas as pd
import random
import time
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator
import time
import random
import requests
import json
import os
import datetime

# =========================
# BUSCAR TICKERS DA B3
# =========================



CACHE_DIR = "cache"

def salvar_cache_tickers(tickers):

    os.makedirs(CACHE_DIR, exist_ok=True)

    hoje = datetime.date.today().strftime("%Y-%m-%d")

    arquivo = os.path.join(CACHE_DIR, f"tickers_{hoje}.json")

    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(tickers, f, ensure_ascii=False, indent=2)


def carregar_cache_mais_recente():

    if not os.path.exists(CACHE_DIR):
        return []

    arquivos = [
        f for f in os.listdir(CACHE_DIR)
        if f.startswith("tickers_") and f.endswith(".json")
    ]

    if not arquivos:
        return []

    arquivos.sort(reverse=True)

    ultimo = arquivos[0]

    caminho = os.path.join(CACHE_DIR, ultimo)

    try:

        with open(caminho, "r", encoding="utf-8") as f:
            tickers = json.load(f)

        print(f"Usando fallback do cache: {ultimo}")
        print(f"{len(tickers)} tickers carregados do cache.")

        return tickers

    except Exception as e:

        print("Erro ao carregar cache:", e)

        return []


def get_b3_tickers():

    try:

        print("Buscando lista de ativos da B3...")

        url = "https://brapi.dev/api/available"

        response = requests.get(url, timeout=15)

        response.raise_for_status()

        data = response.json()

        if isinstance(data, list):
            tickers = data
        else:
            tickers = data.get("stocks", [])

        # filtrar ações válidas
        tickers = [
            t for t in tickers
            if isinstance(t, str)
            and len(t) == 5
            and t.endswith(("3", "4", "5", "6"))
        ]

        tickers = sorted(list(set(tickers)))

        print(f"{len(tickers)} ativos encontrados.")

        # salva cache diário
        salvar_cache_tickers(tickers)

        return tickers

    except Exception as e:

        print("Falha ao buscar API da B3:", e)

        # FALLBACK → cache do dia anterior
        tickers_cache = carregar_cache_mais_recente()

        if tickers_cache:
            return tickers_cache

        # fallback extremo
        print("Usando fallback mínimo.")

        return [
            "PETR4",
            "VALE3",
            "ITUB4",
            "BBAS3",
            "BBDC4",
            "WEGE3",
            "ABEV3"
        ]   

    



    
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
