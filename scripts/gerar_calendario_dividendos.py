def gerar_calendario_dividendos_completo(df):

    import pandas as pd
    import yfinance as yf

    print("📅 Gerando calendário de dividendos...")

    # =========================
    # COLETAR DIVIDENDOS
    # =========================

    registros = []

    for ticker in df["Ticker"].unique():
        try:
            t = yf.Ticker(f"{ticker}.SA")
            divs = t.dividends

            if divs.empty:
                continue

            divs = divs.tail(12)

            for data, valor in divs.items():
                registros.append({
                    "Ticker": ticker,
                    "DataPagamento": data,
                    "ValorProvento": float(valor)
                })

        except Exception:
            continue

    df_div = pd.DataFrame(registros)

    if df_div.empty:
        print("⚠️ Nenhum dividendo encontrado.")
        return

    # =========================
    # TRATAMENTO
    # =========================

    df_div["DataPagamento"] = pd.to_datetime(df_div["DataPagamento"])
    df_div["MesPagamento"] = df_div["DataPagamento"].dt.month

    # merge com base principal
    df = df.merge(df_div, on="Ticker", how="left")
    df = df[df["ValorProvento"].notna()].copy()

    if df.empty:
        print("⚠️ Nenhum dado válido para calendário.")
        return

    df = df.sort_values("DataPagamento")

    # Garante colunas opcionais existam
    for col in ["Setor", "Categoria", "DivYield", "Empresa"]:
        if col not in df.columns:
            df[col] = ""

    df["DivYield"] = pd.to_numeric(df["DivYield"], errors="coerce").fillna(0)

    # =========================
    # DADOS PARA STATS
    # =========================

    total_tickers   = df["Ticker"].nunique()
    total_proventos = df["ValorProvento"].sum()
    melhor_dy_row   = df.loc[df["DivYield"].idxmax()] if df["DivYield"].max() > 0 else None
    melhor_dy_str   = (
        f"{melhor_dy_row['Ticker']} ({melhor_dy_row['DivYield']:.1f}%)"
        if melhor_dy_row is not None else "—"
    )

    # =========================
    # CONSTANTES
    # =========================

    MESES_PT = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março",    4: "Abril",
        5: "Maio",    6: "Junho",     7: "Julho",     8: "Agosto",
        9: "Setembro",10: "Outubro",  11: "Novembro", 12: "Dezembro"
    }

    MESES_ABREV = {
        1: "Jan", 2: "Fev", 3: "Mar",  4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul",  8: "Ago",
        9: "Set",10: "Out",11: "Nov", 12: "Dez"
    }

    meses_com_dados = sorted(df["MesPagamento"].dropna().unique().astype(int).tolist())
    setores_unicos  = sorted(df["Setor"].dropna().replace("", pd.NA).dropna().unique().tolist())

    # =========================
    # HTML CARD DE LINHA
    # =========================

    def card(row):
        dy_val   = float(row.get("DivYield", 0) or 0)
        dy_badge = (
            f'<span class="badge-dy">{dy_val:.1f}% DY</span>'
            if dy_val > 0 else ""
        )
        empresa  = str(row.get("Empresa", "") or "")
        setor    = str(row.get("Setor", "") or "")
        cat      = str(row.get("Categoria", "") or "")
        valor    = round(float(row["ValorProvento"]), 4)
        data_fmt = row["DataPagamento"].strftime("%d/%m/%Y")
        mes_num  = int(row["MesPagamento"])

        return f"""
        <div class="card-div"
             data-mes="{mes_num}"
             data-setor="{setor}"
             data-categoria="{cat}"
             data-dy="{dy_val}"
             data-valor="{valor}"
             data-data="{row['DataPagamento'].strftime('%Y%m%d')}">

            <div class="card-left">
                <div class="logo-wrap">
                    <img src="../logos/{row['Ticker']}.png"
                         onerror="this.src='../logos/default.svg'"
                         alt="{row['Ticker']}"
                         class="logo-img">
                </div>
                <div class="card-info">
                    <span class="ticker-label">{row['Ticker']}</span>
                    <span class="empresa-label">{empresa}</span>
                    {f'<span class="setor-tag">{setor}</span>' if setor else ''}
                </div>
            </div>

            <div class="card-right">
                {dy_badge}
                <span class="valor-provento">R$ {valor:.2f}</span>
                <span class="data-pag">{data_fmt}</span>
            </div>
        </div>
        """

    # =========================
    # PILLS DE MÊS
    # =========================

    pills_meses = '<button class="pill-mes active" data-mes="all">Todos</button>\n'
    for m in meses_com_dados:
        pills_meses += f'<button class="pill-mes" data-mes="{m}">{MESES_ABREV[m]}</button>\n'

    # =========================
    # SELECTS DE SETOR / CATEGORIA
    # =========================

    options_setor = '<option value="all">Todos setores</option>\n'
    options_setor += "\n".join(
        [f'<option value="{s}">{s}</option>' for s in setores_unicos]
    )

    options_cat = """
        <option value="all">Todas categorias</option>
        <option value="Blue Chips">Blue Chips</option>
        <option value="Mid Caps">Mid Caps</option>
        <option value="Small Caps">Small Caps</option>
    """

    # =========================
    # GRUPOS POR MÊS
    # =========================

    grupos_html = ""
    for mes in meses_com_dados:
        df_mes    = df[df["MesPagamento"] == mes]
        total_mes = df_mes["ValorProvento"].sum()
        qtd_ativ  = df_mes["Ticker"].nunique()
        cards_html = "".join([card(row) for _, row in df_mes.iterrows()])

        grupos_html += f"""
        <section class="grupo-mes" data-mes="{mes}">
            <div class="mes-header">
                <div class="mes-titulo">
                    <span class="mes-nome">{MESES_PT[mes]}</span>
                    <span class="mes-meta">{qtd_ativ} ativo{'s' if qtd_ativ != 1 else ''}</span>
                </div>
                <span class="mes-total">R$ {total_mes:.2f}</span>
            </div>
            <div class="mes-cards">
                {cards_html}
            </div>
        </section>
        """

    # =========================
    # HTML FINAL COMPLETO
    # =========================

    conteudo = f"""
<style>
/* ================================================
   CALENDÁRIO DE DIVIDENDOS — Design System
   ================================================ */

@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600&display=swap');

.cal-wrap {{
    --green:      #00d97e;
    --green-dim:  #00d97e22;
    --green-mid:  #00d97e55;
    --bg:         #090e1a;
    --bg2:        #0f1729;
    --bg3:        #151f35;
    --border:     #1e2d4a;
    --text:       #e2e8f0;
    --muted:      #64748b;
    --accent:     #38bdf8;
    --warn:       #fbbf24;

    font-family: 'DM Sans', sans-serif;
    color: var(--text);
    background: var(--bg);
    min-height: 100vh;
    padding: 0 0 80px;
}}

/* --- HERO --- */
.cal-hero {{
    background: linear-gradient(135deg, #0a1628 0%, #0d1f3c 60%, #0a2616 100%);
    border-bottom: 1px solid var(--border);
    padding: 48px 32px 40px;
    position: relative;
    overflow: hidden;
}}

.cal-hero::before {{
    content: '';
    position: absolute;
    inset: 0;
    background:
        radial-gradient(ellipse 60% 80% at 80% 50%, #00d97e0d, transparent),
        radial-gradient(ellipse 40% 60% at 20% 80%, #38bdf808, transparent);
    pointer-events: none;
}}

.cal-hero-inner {{
    max-width: 960px;
    margin: 0 auto;
    position: relative;
}}

.cal-eyebrow {{
    font-family: 'Syne', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .2em;
    text-transform: uppercase;
    color: var(--green);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}}

.cal-eyebrow::before {{
    content: '';
    display: inline-block;
    width: 20px;
    height: 2px;
    background: var(--green);
    border-radius: 2px;
}}

.cal-title {{
    font-family: 'Syne', sans-serif;
    font-size: clamp(28px, 5vw, 44px);
    font-weight: 800;
    line-height: 1.1;
    margin: 0 0 8px;
    color: #fff;
}}

.cal-subtitle {{
    font-size: 15px;
    color: var(--muted);
    margin: 0 0 36px;
}}

/* --- STATS --- */
.stats-row {{
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
}}

.stat-card {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 20px;
    min-width: 140px;
    transition: border-color .2s;
}}

.stat-card:hover {{ border-color: var(--green-mid); }}

.stat-label {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 4px;
}}

.stat-value {{
    font-family: 'Syne', sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: var(--green);
}}

.stat-value.white {{ color: #fff; }}
.stat-value.accent {{ color: var(--accent); }}

/* --- FILTROS --- */
.cal-filtros {{
    max-width: 960px;
    margin: 0 auto;
    padding: 28px 32px 0;
}}

/* Pills de mês */
.filtro-label {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 10px;
}}

.pills-wrap {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 20px;
}}

.pill-mes {{
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--muted);
    border-radius: 100px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 600;
    font-family: 'Syne', sans-serif;
    cursor: pointer;
    transition: all .15s ease;
    white-space: nowrap;
}}

.pill-mes:hover {{
    border-color: var(--green-mid);
    color: var(--text);
}}

.pill-mes.active {{
    background: var(--green);
    border-color: var(--green);
    color: #000;
}}

/* Selects row */
.selects-row {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 8px;
}}

.filtro-select {{
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 8px;
    padding: 8px 36px 8px 14px;
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    outline: none;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%2364748b' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    transition: border-color .15s;
    flex: 1;
    min-width: 150px;
    max-width: 240px;
}}

.filtro-select:focus {{
    border-color: var(--green-mid);
}}

.resultado-count {{
    margin-left: auto;
    font-size: 13px;
    color: var(--muted);
    white-space: nowrap;
}}

#badge-count {{
    font-weight: 700;
    color: var(--green);
}}

/* --- CONTEÚDO --- */
.cal-content {{
    max-width: 960px;
    margin: 0 auto;
    padding: 24px 32px 0;
}}

/* --- GRUPO MÊS --- */
.grupo-mes {{
    margin-bottom: 36px;
    animation: fadeUp .4s ease both;
}}

@keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(16px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}

.mes-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
}}

.mes-titulo {{
    display: flex;
    align-items: baseline;
    gap: 10px;
}}

.mes-nome {{
    font-family: 'Syne', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: #fff;
}}

.mes-meta {{
    font-size: 12px;
    color: var(--muted);
}}

.mes-total {{
    font-family: 'Syne', sans-serif;
    font-size: 15px;
    font-weight: 700;
    color: var(--green);
}}

/* --- CARDS --- */
.mes-cards {{
    display: flex;
    flex-direction: column;
    gap: 8px;
}}

.card-div {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    cursor: default;
    transition: border-color .2s, transform .15s, background .15s;
    animation: fadeUp .35s ease both;
}}

.card-div:hover {{
    border-color: var(--green-mid);
    background: var(--bg3);
    transform: translateX(3px);
}}

.card-left {{
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
}}

.logo-wrap {{
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: var(--bg3);
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    overflow: hidden;
}}

.logo-img {{
    width: 28px;
    height: 28px;
    object-fit: contain;
}}

.card-info {{
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
}}

.ticker-label {{
    font-family: 'Syne', sans-serif;
    font-size: 15px;
    font-weight: 700;
    color: #fff;
    letter-spacing: .04em;
}}

.empresa-label {{
    font-size: 12px;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
}}

.setor-tag {{
    font-size: 10px;
    font-weight: 600;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--accent);
    opacity: .75;
}}

.card-right {{
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 3px;
    flex-shrink: 0;
}}

.badge-dy {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    background: var(--green-dim);
    color: var(--green);
    border: 1px solid var(--green-mid);
    border-radius: 100px;
    padding: 2px 8px;
}}

.valor-provento {{
    font-family: 'Syne', sans-serif;
    font-size: 17px;
    font-weight: 700;
    color: var(--green);
}}

.data-pag {{
    font-size: 12px;
    color: var(--muted);
}}

/* --- EMPTY STATE --- */
.empty-state {{
    text-align: center;
    padding: 60px 20px;
    color: var(--muted);
    display: none;
}}

.empty-state.show {{ display: block; }}

.empty-icon {{
    font-size: 40px;
    margin-bottom: 12px;
}}

.empty-msg {{
    font-family: 'Syne', sans-serif;
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 6px;
}}

/* --- RESPONSIVE --- */
@media (max-width: 600px) {{
    .cal-hero, .cal-filtros, .cal-content {{
        padding-left: 16px;
        padding-right: 16px;
    }}

    .stats-row {{
        gap: 10px;
    }}

    .stat-card {{
        flex: 1;
        min-width: 120px;
        padding: 12px 14px;
    }}

    .stat-value {{
        font-size: 18px;
    }}

    .empresa-label {{
        max-width: 120px;
    }}

    .filtro-select {{
        max-width: 100%;
        min-width: 100%;
    }}

    .selects-row {{
        flex-direction: column;
        align-items: stretch;
    }}

    .resultado-count {{
        margin-left: 0;
    }}

    .card-div {{
        padding: 12px 14px;
    }}
}}
</style>

<div class="cal-wrap">

  <!-- HERO -->
  <header class="cal-hero">
    <div class="cal-hero-inner">
      <div class="cal-eyebrow">Tanoprecinho • B3</div>
      <h1 class="cal-title">Calendário de<br>Dividendos 2026</h1>
      <p class="cal-subtitle">Proventos pagos ao longo do ano, direto da B3.</p>

      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-label">Ativos</div>
          <div class="stat-value white">{total_tickers}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Total Proventos</div>
          <div class="stat-value">R$ {total_proventos:.2f}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Maior Yield</div>
          <div class="stat-value accent">{melhor_dy_str}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Meses com pag.</div>
          <div class="stat-value white">{len(meses_com_dados)}</div>
        </div>
      </div>
    </div>
  </header>

  <!-- FILTROS -->
  <div class="cal-filtros">

    <div class="filtro-label">Filtrar por mês</div>
    <div class="pills-wrap" id="pills-mes">
      {pills_meses}
    </div>

    <div class="selects-row">
      <select class="filtro-select" id="sel-setor" onchange="aplicar()">
        {options_setor}
      </select>
      <select class="filtro-select" id="sel-categoria" onchange="aplicar()">
        {options_cat}
      </select>
      <select class="filtro-select" id="sel-ordenar" onchange="reordenar()">
        <option value="data">Ordenar por data</option>
        <option value="valor">Maior provento</option>
        <option value="dy">Maior DY</option>
      </select>
      <span class="resultado-count">
        Exibindo <span id="badge-count">0</span> pagamentos
      </span>
    </div>

  </div>

  <!-- CONTEÚDO -->
  <div class="cal-content" id="cal-content">
    {grupos_html}
    <div class="empty-state" id="empty-state">
      <div class="empty-icon">🔍</div>
      <div class="empty-msg">Nenhum resultado encontrado</div>
      <p>Tente ajustar os filtros para ver mais ações.</p>
    </div>
  </div>

</div>

<script>
(function() {{

  // ── Estado dos filtros ─────────────────────────────────────────
  let mesSel = 'all';

  // ── Pills de mês ──────────────────────────────────────────────
  document.querySelectorAll('.pill-mes').forEach(btn => {{
    btn.addEventListener('click', function() {{
      document.querySelectorAll('.pill-mes').forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      mesSel = this.dataset.mes;
      aplicar();
    }});
  }});

  // ── Aplicar filtros ───────────────────────────────────────────
  window.aplicar = function() {{
    const setor    = document.getElementById('sel-setor').value;
    const cat      = document.getElementById('sel-categoria').value;
    let   visTotal = 0;

    // Esconde/mostra cards
    document.querySelectorAll('.card-div').forEach(el => {{
      const okMes   = (mesSel === 'all' || el.dataset.mes    === mesSel);
      const okSetor = (setor  === 'all' || el.dataset.setor  === setor);
      const okCat   = (cat    === 'all' || el.dataset.categoria === cat);
      const vis     = okMes && okSetor && okCat;
      el.style.display = vis ? 'flex' : 'none';
      if (vis) visTotal++;
    }});

    // Esconde/mostra seções de mês inteiras quando vazias
    document.querySelectorAll('.grupo-mes').forEach(sec => {{
      const temVisivel = Array.from(sec.querySelectorAll('.card-div'))
        .some(c => c.style.display !== 'none');
      sec.style.display = temVisivel ? '' : 'none';
    }});

    // Contador de resultados
    document.getElementById('badge-count').textContent = visTotal;

    // Empty state
    const empty = document.getElementById('empty-state');
    empty.classList.toggle('show', visTotal === 0);
  }};

  // ── Reordenar dentro de cada grupo ───────────────────────────
  window.reordenar = function() {{
    const tipo = document.getElementById('sel-ordenar').value;

    document.querySelectorAll('.mes-cards').forEach(wrap => {{
      const cards = Array.from(wrap.querySelectorAll('.card-div'));

      cards.sort((a, b) => {{
        if (tipo === 'valor') return parseFloat(b.dataset.valor) - parseFloat(a.dataset.valor);
        if (tipo === 'dy')    return parseFloat(b.dataset.dy)    - parseFloat(a.dataset.dy);
        // 'data': usa order original (data-data é YYYYMMDD)
        return parseInt(a.dataset.data) - parseInt(b.dataset.data);
      }});

      cards.forEach(c => wrap.appendChild(c));
    }});
  }};

  // ── Init: contar registros visíveis no carregamento ───────────
  aplicar();

}})();
</script>
"""

    # =========================
    # GERAR PÁGINA
    # =========================

    gerar_pagina(
        "calendario-dividendos",
        "Calendário de Dividendos 2026",
        conteudo,
        descricao="Calendário completo com ações que pagarão dividendos ao longo do ano.",
        keywords="calendário dividendos, ações dividendos, renda passiva"
    )

    print("✅ Calendário de dividendos gerado com sucesso.")
