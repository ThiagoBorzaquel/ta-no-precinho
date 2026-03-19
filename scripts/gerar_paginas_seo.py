def slugify(texto):
    return (
        texto.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace(",", "")
        .replace("/", "")
    )

def gerar_paginas_seo(df, gerar_pagina):

    for _, row in df.iterrows():

        ticker = row["Ticker"]
        empresa = row["Empresa"]

        nome_slug = slugify(empresa)
        ticker_slug = ticker.lower()

        base_nome = f"{nome_slug}-{ticker_slug}"

        paginas = {
            "vale-a-pena": f"{empresa} vale a pena?",
            "dividendos": f"{empresa} paga bons dividendos?",
            "preco-justo": f"{empresa} está barata?"
        }

        for tipo, titulo in paginas.items():

            nome_arquivo = f"{base_nome}-{tipo}"

            conteudo = f"""
<h1>{titulo}</h1>
<p>A ação {empresa} ({ticker}) está sendo analisada...</p>
"""
            