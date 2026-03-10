import os
import requests

BASE_URL = "https://raw.githubusercontent.com/thefintz/icones-b3/main/icones"

CACHE_DIR = "data/logos"
SITE_DIR = "docs/logos"

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(SITE_DIR, exist_ok=True)


def baixar_logo(ticker):

    
    url = f"{BASE_URL}/{ticker}.png"

    cache_path = f"{CACHE_DIR}/{ticker}.png"
    site_path = f"{SITE_DIR}/{ticker}.png"

    # se já existe no cache não baixa novamente
    if os.path.exists(cache_path):

        if not os.path.exists(site_path):
            with open(cache_path, "rb") as src:
                with open(site_path, "wb") as dst:
                    dst.write(src.read())

        return site_path

    try:

        response = requests.get(url, timeout=10)

        if response.status_code == 200:

            with open(cache_path, "wb") as f:
                f.write(response.content)

            with open(site_path, "wb") as f:
                f.write(response.content)

            return site_path

    except:
        pass

    return None


def preparar_logos(df):

    for ticker in df["Ticker"]:
        baixar_logo(ticker)