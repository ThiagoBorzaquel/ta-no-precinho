# =========================
# GERAR SITEMAP
# =========================

def gerar_sitemap(df):
    base_url = "https://tanoprecinho.site"
    urls = []

    def add(loc, freq="daily", pri="0.7"):
        urls.append(f"  <url><loc>{loc}</loc><changefreq>{freq}</changefreq><priority>{pri}</priority></url>")

    # HOME
    add(f"{base_url}/", "daily", "1.0")

    # PÁGINAS EDUCATIVAS E LEGAIS — fora do loop, 1x no sitemap
    for p, freq, pri in [
        ("missao.html",          "monthly", "0.7"),
        ("fundamentalista.html", "monthly", "0.7"),
        ("pl.html",              "monthly", "0.7"),
        ("roe.html",             "monthly", "0.7"),
        ("dividend-yield.html",  "monthly", "0.7"),
        ("investidor.html",      "monthly", "0.5"),
        ("privacidade.html",     "monthly", "0.3"),
        ("termos.html",          "monthly", "0.3"),
        ("cookies.html",         "monthly", "0.3"),
        ("sobre.html",           "monthly", "0.4"),
        ("contato.html",         "monthly", "0.4"),
    ]:
        add(f"{base_url}/{p}", freq, pri)

    # PÁGINAS DE RANKING FIXAS — fora do loop, 1x no sitemap
    for p in [
        "seo/melhores-acoes-para-investir.html",
        "seo/acoes-maior-dividend-yield.html",
        "seo/acoes-maior-roe.html",
        "seo/acoes-mais-seguras.html",
        "seo/acoes-dividendos-mensais.html",
        "seo/melhores-acoes-dividendos.html",
        "seo/acoes-baratas-2026.html",
    ]:
        add(f"{base_url}/{p}", "daily", "0.9")

    # PÁGINAS POR AÇÃO — 1 entrada por ticker
    seen = set()
    for _, row in df.iterrows():
        ticker = row["Ticker"]
        if ticker in seen:
            continue
        seen.add(ticker)
        slug = gerar_slug(row["Empresa"], ticker)
        add(f"{base_url}/acoes/{ticker}.html",              "daily",  "0.8")
        add(f"{base_url}/seo/vale-a-pena-{slug}.html",     "weekly", "0.7")
        add(f"{base_url}/seo/{slug}-ta-barato.html",       "weekly", "0.7")
        add(f"{base_url}/seo/{slug}-paga-dividendos.html", "weekly", "0.7")

    header = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    footer = '\n</urlset>\n'
    sitemap = header + "\n".join(urls) + footer

    with open("docs/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap)

    print(f"Sitemap gerado com {len(urls)} URLs unicas.")


