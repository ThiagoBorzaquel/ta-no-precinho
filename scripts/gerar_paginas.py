def _aplicar_template(nome, titulo, conteudo, descricao, keywords, url):
    with open("docs/layout_base.html", "r", encoding="utf-8") as f:
        template = f.read()
    html = template.replace("{{titulo}}", titulo)
    html = html.replace("{{conteudo}}", conteudo)
    html = html.replace("{{descricao}}", descricao)
    html = html.replace("{{keywords}}", keywords)
    html = html.replace("{{url}}", url)
    return html

def gerar_pagina_raiz(nome, titulo, conteudo, descricao="", keywords=""):
    url = f"https://tanoprecinho.site/{nome}.html"
    html = _aplicar_template(nome, titulo, conteudo, descricao, keywords, url)
    with open(f"docs/{nome}.html", "w", encoding="utf-8") as f:
        f.write(html)

def gerar_pagina(nome, titulo, conteudo, descricao="", keywords=""):
    url = f"https://tanoprecinho.site/seo/{nome}.html"
    html = _aplicar_template(nome, titulo, conteudo, descricao, keywords, url)
    with open(f"docs/seo/{nome}.html", "w", encoding="utf-8") as f:
        f.write(html)