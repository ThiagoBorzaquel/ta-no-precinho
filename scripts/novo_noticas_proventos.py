# =============================================================================
# NOVO BLOCO — adicionar no topo do main.py junto dos outros imports
# =============================================================================

import xml.etree.ElementTree as ET
import urllib.parse
import re
import requests   # provavelmente já importado


# =============================================================================
# FUNÇÕES AUXILIARES — colar antes de gerar_pagina_acao()
# =============================================================================

def buscar_proventos(ticker, limite=8):
    """
    Busca os últimos proventos (dividendos / JCP / bonificações) via brapi.dev.
    Documentação: https://brapi.dev/docs
    Token gratuito disponível em https://brapi.dev/
    """
    try:
        token = "SEU_TOKEN_BRAPI"   # ← substitua ou leia de env var
        url = (
            f"https://brapi.dev/api/quote/{ticker}"
            f"?modules=dividends&token={token}"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        cash = (
            data.get("results", [{}])[0]
                .get("dividendsData", {})
                .get("cashDividends", [])
        )
        # Ordena pelo mais recente
        cash = sorted(cash, key=lambda x: x.get("paymentDate", ""), reverse=True)
        return cash[:limite]
    except Exception:
        return []


def buscar_noticias(ticker, empresa, limite=5):
    """
    Busca notícias via Google News RSS.
    O conteúdo (título + resumo + fonte) é embutido na página;
    apenas o link aponta para a fonte original.
    """
    try:
        query = urllib.parse.quote(f"{ticker} {empresa} ação")
        url = (
            f"https://news.google.com/rss/search"
            f"?q={query}&hl=pt-BR&gl=BR&ceid=BR:pt"
        )
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TanoPrecinho/1.0)"}
        r = requests.get(url, timeout=10, headers=headers)
        r.raise_for_status()

        root = ET.fromstring(r.content)
        items = root.findall(".//item")[:limite]

        noticias = []
        for item in items:
            titulo  = item.findtext("title",  "").strip()
            link    = item.findtext("link",   "").strip()
            data    = item.findtext("pubDate","").strip()[:22]   # "Wed, 28 Apr 2026 10:00"
            fonte   = item.findtext("source", ticker).strip()
            desc    = item.findtext("description", "").strip()

            # Remove tags HTML do snippet
            desc_limpo = re.sub(r"<[^>]+>", "", desc)[:220].strip()
            if desc_limpo and not desc_limpo.endswith((".", "!", "?")):
                desc_limpo += "…"

            noticias.append({
                "titulo": titulo,
                "link":   link,
                "data":   data,
                "fonte":  fonte,
                "resumo": desc_limpo,
            })
        return noticias
    except Exception:
        return []


# =============================================================================
# CARDS — colar dentro de gerar_pagina_acao(), logo antes de </article>
# (substituir a tag </article> pelo bloco abaixo + </article>)
# =============================================================================

def gerar_card_proventos(ticker):
    proventos = buscar_proventos(ticker)

    if not proventos:
        return ""   # sem dados, não exibe o card

    linhas = ""
    for p in proventos:
        tipo     = p.get("type",         p.get("label",   "Provento"))
        valor    = p.get("value",        p.get("rate",    0))
        data_com = p.get("lastDatePrior", "—")
        data_pag = p.get("paymentDate",  "—")

        # Formata datas YYYY-MM-DD → DD/MM/YYYY
        def fmt(d):
            try:
                from datetime import datetime
                return datetime.strptime(d[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                return d

        linhas += f"""
          <tr>
            <td style="padding:8px 6px">{tipo}</td>
            <td style="padding:8px 6px;text-align:right;color:#22c55e;font-weight:600">
              R$ {float(valor):.4f}
            </td>
            <td style="padding:8px 6px;text-align:right;color:#94a3b8">{fmt(data_com)}</td>
            <td style="padding:8px 6px;text-align:right;color:#94a3b8">{fmt(data_pag)}</td>
          </tr>"""

    return f"""
<div class="card">
  <h2>💰 Últimos proventos de {ticker}</h2>
  <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="color:#64748b;border-bottom:1px solid #1e293b;font-size:11px;text-transform:uppercase;letter-spacing:.05em">
          <th style="text-align:left;padding:6px 6px">Tipo</th>
          <th style="text-align:right;padding:6px 6px">Valor / ação</th>
          <th style="text-align:right;padding:6px 6px">Data COM</th>
          <th style="text-align:right;padding:6px 6px">Pagamento</th>
        </tr>
      </thead>
      <tbody style="border-top:1px solid #1e293b">
        {linhas}
      </tbody>
    </table>
  </div>
  <p style="font-size:11px;color:#475569;margin-top:10px">
    Fonte: brapi.dev &nbsp;·&nbsp;
    Dividend Yield acumulado exibido nos indicadores acima.
  </p>
</div>"""


def gerar_card_noticias(ticker, empresa):
    noticias = buscar_noticias(ticker, empresa)

    if not noticias:
        return ""

    itens = ""
    for n in noticias:
        itens += f"""
      <div style="padding:14px 0;border-bottom:1px solid #1e293b">
        <div style="font-size:11px;color:#475569;margin-bottom:4px">
          {n['data']} &nbsp;·&nbsp;
          <span style="color:#64748b">{n['fonte']}</span>
        </div>
        <p style="margin:0 0 6px;font-size:14px;font-weight:600;line-height:1.4;color:#e2e8f0">
          {n['titulo']}
        </p>
        <p style="margin:0 0 8px;font-size:13px;color:#94a3b8;line-height:1.5">
          {n['resumo']}
        </p>
        <a href="{n['link']}" target="_blank" rel="noopener noreferrer"
           style="font-size:12px;color:#22c55e;text-decoration:none">
          Ler na fonte →
        </a>
      </div>"""

    return f"""
<div class="card">
  <h2>📰 Últimas notícias sobre {ticker}</h2>
  <p style="font-size:12px;color:#64748b;margin-top:-8px">
    Conteúdo agregado de fontes públicas. O TanoPrecinho não é responsável pelas publicações externas.
  </p>
  <div>{itens}</div>
</div>"""


# =============================================================================
# COMO USAR — dentro de gerar_pagina_acao(), no bloco conteudo = f"""..."""
# Adicione as duas chamadas logo antes de </article>:
#
#   {gerar_card_proventos(ticker)}
#   {gerar_card_noticias(ticker, empresa)}
#
# </article>
#
# Exemplo de onde inserir no conteudo existente:
# =============================================================================

EXEMPLO_USO = """
# No bloco conteudo = f\"\"\"...\"\"\" da função gerar_pagina_acao, substituir:

<div class="card">
<h2>Conclusão sobre {ticker}</h2>
...
</div>

</article>

# Por:

<div class="card">
<h2>Conclusão sobre {ticker}</h2>
...
</div>

{gerar_card_proventos(ticker)}

{gerar_card_noticias(ticker, empresa)}

</article>
"""
