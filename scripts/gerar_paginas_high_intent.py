def gerar_paginas_high_intent(df):

    def montar_lista(df_base, tipo="geral"):
        html_lista = ""

        for i, (_, row) in enumerate(df_base.iterrows(), start=1):
            medalhas = ["🥇", "🥈", "🥉"]
            icone = medalhas[i-1] if i <= 3 else ""

            tag = ""
            if row["DivYield"] > 0.08:
                tag = "💰 RENDA"
            elif row["ROE"] > 0.20:
                tag = "🏆 ALTA RENT"
            elif row["Desconto_%"] > 50:
                tag = "🔥 OPORTUNIDADE"

            html_lista += f"""
            <a href="../acoes/{row['Ticker']}.html" style="text-decoration:none;color:inherit" aria-label="Ver análise de {row['Empresa']} ({row['Ticker']})">
            <div style="background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);padding:14px;border-radius:12px;display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
            <div style="display:flex;align-items:center;gap:10px">
            <img src="../logos/{row['Ticker']}.png"
                 alt="Logo {row['Empresa']}"
                 onerror="this.onerror=null;this.src='../logos/default.svg';"
                 style="width:28px;height:28px">
            <div>
            <div style="font-weight:600">#{i} {icone} {row['Empresa']}</div>
            <div style="font-size:12px;color:#cbd5e1">{row['Ticker']} • {row['Setor']}</div>
            </div>
            </div>
            <div style="text-align:right">
            <div style="color:#22c55e;font-weight:700">{round(row['Score'],0)}</div>
            <div style="font-size:11px;color:#cbd5e1">{tag}</div>
            </div>
            </div>
            </a>
            """

        return html_lista

    top_score = df.sort_values("Score", ascending=False).head(20)
    gerar_pagina(
        "melhores-acoes-para-investir",
        "Melhores ações para investir em 2026",
        f"""<div class="card"><h2>🏆 Melhores ações para investir</h2>
        <p style="color:#22c55e;font-size:13px">Atualizado hoje • Ranking baseado em Score</p>
        {montar_lista(top_score)}</div>""",
        descricao="Veja as melhores ações para investir hoje na bolsa brasileira.",
        keywords="melhores ações 2026, melhores ações para investir hoje"
    )

    top_dy = df.sort_values("DivYield", ascending=False).head(20)
    gerar_pagina(
        "acoes-maior-dividend-yield",
        "Ações com maior dividend yield hoje",
        f"""<div class="card"><h2>💰 Maiores pagadoras de dividendos</h2>
        <p style="color:#22c55e;font-size:13px">Atualizado hoje • Ranking por Dividend Yield</p>
        {montar_lista(top_dy)}</div>""",
        descricao="Ranking das ações com maior dividend yield da bolsa.",
        keywords="ações dividend yield alto, melhores dividendos hoje"
    )

    top_roe = df.sort_values("ROE", ascending=False).head(20)
    gerar_pagina(
        "acoes-maior-roe",
        "Ações com maior ROE da bolsa",
        f"""<div class="card"><h2>📈 Empresas mais rentáveis</h2>
        <p style="color:#22c55e;font-size:13px">Atualizado hoje • Ranking por ROE</p>
        {montar_lista(top_roe)}</div>""",
        descricao="Veja as empresas mais rentáveis da bolsa com maior ROE.",
        keywords="ações com maior roe, empresas mais lucrativas"
    )

    seguras = df[df["Risco_num"] < 0.3].sort_values("Score", ascending=False).head(20)
    gerar_pagina(
        "acoes-mais-seguras",
        "Ações mais seguras da bolsa",
        f"""<div class="card"><h2>🛡️ Ações mais seguras</h2>
        <p style="color:#22c55e;font-size:13px">Baixo risco • Score alto</p>
        {montar_lista(seguras)}</div>""",
        descricao="Ranking de ações mais seguras da bolsa brasileira.",
        keywords="ações seguras, ações baixo risco"
    )

    renda = df[df["DivYield"] > 0.06].sort_values("DivYield", ascending=False).head(20)
    gerar_pagina(
        "acoes-dividendos-mensais",
        "Ações para renda mensal com dividendos",
        f"""<div class="card"><h2>💵 Renda mensal com dividendos</h2>
        <p style="color:#cbd5e1;font-size:13px">Empresas com alto pagamento de dividendos</p>
        {montar_lista(renda)}</div>""",
        descricao="Ações que podem gerar renda mensal com dividendos.",
        keywords="ações dividendos mensais, renda passiva ações"
    )
    