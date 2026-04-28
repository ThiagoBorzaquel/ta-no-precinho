def gerar_sitemap(df, base_url):

    urls = []

    urls.append(f"<url><loc>{base_url}/</loc></url>")

    for _, row in df.iterrows():

        ticker = row["Ticker"]
        nome = row["Empresa"].lower().replace(" ", "-")

        urls.append(f"<url><loc>{base_url}/acoes/{ticker}.html</loc></url>")

        for tipo in ["vale-a-pena", "dividendos", "preco-justo"]:
            urls.append(
                f"<url><loc>{base_url}/{nome}-{ticker.lower()}-{tipo}.html</loc></url>"
            )

    sitemap = f"<urlset>{''.join(urls)}</urlset>"

    with open("docs/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap)