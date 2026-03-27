def gerar_paginas_ranking(df):

    top_div = df.sort_values("DivYield", ascending=False).head(20)

    lista_div = "".join([
    f"""
    <div style="background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);padding:14px;border-radius:12px;display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px">
    <img src="../logos/{row['Ticker']}.png"
         alt="Logo {row['Empresa']}"
         loading="lazy"
         onerror="this.onerror=null;this.src='../logos/default.svg';"
         style="width:28px;height:28px">
    <div>
    <a href="../acoes/{row['Ticker']}.html" style="color:#e2e8f0;text-decoration:none;font-weight:600;">{row['Empresa']}</a>
    <div style="font-size:12px;color:#cbd5e1">{row['Ticker']}</div>
    </div>
    </div>
    <div style="color:#22c55e;font-weight:700;">{round(row['DivYield']*100,2)}%</div>
    </div>
    """
    for _, row in top_div.iterrows()
    ])

    gerar_pagina(
        "melhores-acoes-dividendos",
        "Melhores ações de dividendos",
        f"<div>{lista_div}</div>",
        descricao="Ranking atualizado das melhores ações de dividendos da bolsa.",
        keywords="melhores dividendos, ações dividendos"
    )

    top_baratas = df.sort_values("Desconto_%", ascending=False).head(20)

    lista_baratas = "".join([
    f"""
    <div style="background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.05);padding:14px;border-radius:12px;display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
    <div style="display:flex;align-items:center;gap:10px">
    <img src="../logos/{row['Ticker']}.png"
         alt="Logo {row['Empresa']}"
         loading="lazy"
         onerror="this.onerror=null;this.src='../logos/default.svg';"
         style="width:28px;height:28px">
    <div>
    <a href="../acoes/{row['Ticker']}.html" style="color:#e2e8f0;text-decoration:none;font-weight:600;">{row['Empresa']}</a>
    <div style="font-size:12px;color:#cbd5e1">{row['Ticker']}</div>
    </div>
    </div>
    <div style="color:#22c55e;font-weight:700;">{round(row['Desconto_%'],2)}%</div>
    </div>
    """
    for _, row in top_baratas.iterrows()
    ])

    gerar_pagina(
        "acoes-baratas-2026",
        "Ações mais baratas da bolsa",
        f"<div>{lista_baratas}</div>",
        descricao="Veja as ações mais baratas hoje na bolsa.",
        keywords="ações baratas, ações descontadas"
    )

    gerar_pagina(
    "investidores",
    "Maiores investidores da bolsa",
    """
<div style="max-width:900px;margin:auto">

<h1>📚 Maiores investidores da bolsa</h1>

<p style="color:#cbd5e1">
Conheça os maiores investidores da história e aprenda as estratégias que fizeram eles acumularem patrimônio.
</p>

<div class="card">

<h2 style="margin-bottom:12px;">💰 Aprenda com os melhores</h2>

<div style="display:flex;flex-direction:column;gap:10px;">

<a href="barsi-dividendos.html" style="
display:flex;
justify-content:space-between;
align-items:center;
padding:12px 14px;
background:rgba(30,41,59,0.6);
border:1px solid rgba(255,255,255,0.05);
border-radius:10px;
text-decoration:none;
color:#e2e8f0;
transition:0.2s;
">

<span>💸 Luiz Barsi</span>
<span style="font-size:12px;color:#94a3b8;">Dividendos</span>

</a>

<a href="warren-buffett.html" style="
display:flex;
justify-content:space-between;
align-items:center;
padding:12px 14px;
background:rgba(30,41,59,0.6);
border:1px solid rgba(255,255,255,0.05);
border-radius:10px;
text-decoration:none;
color:#e2e8f0;
transition:0.2s;
">

<span>💰 Warren Buffett</span>
<span style="font-size:12px;color:#94a3b8;">Value Investing</span>

</a>

<a href="benjamin-graham.html" style="
display:flex;
justify-content:space-between;
align-items:center;
padding:12px 14px;
background:rgba(30,41,59,0.6);
border:1px solid rgba(255,255,255,0.05);
border-radius:10px;
text-decoration:none;
color:#e2e8f0;
transition:0.2s;
">

<span>📘 Benjamin Graham</span>
<span style="font-size:12px;color:#94a3b8;">Fundamentos</span>

</a>

<a href="peter-lynch.html" style="
display:flex;
justify-content:space-between;
align-items:center;
padding:12px 14px;
background:rgba(30,41,59,0.6);
border:1px solid rgba(255,255,255,0.05);
border-radius:10px;
text-decoration:none;
color:#e2e8f0;
transition:0.2s;
">

<span>📈 Peter Lynch</span>
<span style="font-size:12px;color:#94a3b8;">Crescimento</span>

</a>

</div>

</div>

<div class="card">
<h3>📊 Quer ver ações baratas agora?</h3>
<a href="../index.html" style="display:inline-block;margin-top:10px;padding:12px 18px;background:#22c55e;color:white;border-radius:8px;text-decoration:none;font-weight:600;">
Ver ranking atualizado →
</a>
</div>

<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Explore rankings prontos com as melhores ações da bolsa hoje.</p>
<nav aria-label="Paginas de livros" class="menu">
<a href="seo/melhores-acoes-para-investir.html">🏆 Melhores ações</a>
<a href="seo/acoes-maior-dividend-yield.html">💰 Dividendos</a>
<a href="seo/acoes-maior-roe.html">📈 Alta rentabilidade</a>
<a href="seo/acoes-mais-seguras.html">🛡️ Mais seguras</a>
<a href="seo/acoes-dividendos-mensais.html">💵 Renda mensal</a>
<a href="seo/acoes-baratas-2026.html">🔥 Ações baratas</a>
<a href="seo/melhores-acoes-dividendos.html">💸 Dividendos 2026</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>

</div>
""",
    descricao="Conheça os maiores investidores da bolsa e aprenda suas estratégias.",
    keywords="maiores investidores, luiz barsi, warren buffett, value investing"
)
    
gerar_pagina(
    "barsi-dividendos",
    "Como Luiz Barsi ficou bilionário com dividendos",
    """
<div style="max-width:900px;margin:auto">

<div class="card">

<h2>🇧🇷 Luiz Barsi — o investidor dos dividendos</h2>

<p>
💸 Luiz Barsi é considerado o maior investidor pessoa física do Brasil.
Sua estratégia é simples e extremamente poderosa: viver de dividendos.
</p>

<p>
Ao longo de décadas, Barsi construiu patrimônio investindo em empresas sólidas,
com foco em geração de caixa e pagamento consistente de dividendos.
</p>

<p>
Sua filosofia não envolve especulação ou tentar prever o mercado.
Ele compra boas empresas e mantém posição por muitos anos.
</p>

<p>
A ideia central é clara:
<strong>construir renda passiva crescente ao longo do tempo.</strong>
</p>

</div>

<div class="card">

<h2>📈 A estratégia de Barsi</h2>

<ul>
<li>Foco em dividendos consistentes</li>
<li>Compra de empresas sólidas</li>
<li>Visão de longo prazo</li>
<li>Reinvestimento dos dividendos</li>
</ul>

<p>
Barsi nunca tentou prever o mercado. Ele apenas acumulou boas empresas ao longo do tempo.
</p>

</div>

<div class="card">

<h2>🧠 O segredo</h2>

<p>
O maior diferencial de Barsi não foi inteligência fora da curva.
Foi disciplina.
</p>

<p>
Enquanto a maioria tenta ganhar dinheiro rápido, ele focou em renda passiva consistente.
</p>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Quer aprender direto com ele?</h2>

<p>
Se você quer entender exatamente como Barsi pensa e investe, esse é o melhor ponto de partida:
</p>

<a href="https://amzn.to/47rV2Vj" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro recomendado
</a>

<p style="font-size:12px;color:#94a3b8;margin-top:10px">
*Link de afiliado — você apoia o projeto sem pagar nada a mais
</p>

</div>

<div class="card">

<h3>📊 Veja ações com dividendos agora</h3>

<a href="../index.html" style="display:inline-block;margin-top:10px;padding:12px 18px;background:#3b82f6;color:white;border-radius:8px;text-decoration:none;font-weight:600;">
Ver ranking →
</a>

</div>

<<div class="card">
<h2>O Basico de todo investidor</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Antes de escolher ações, os melhores investidores dominam o essencial:
mentalidade, disciplina e visão de longo prazo.</p>
<nav aria-label="O Basico de todo investidor" class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>

</div>
""",
    descricao="Aprenda como Luiz Barsi ficou bilionário investindo em dividendos.",
    keywords="luiz barsi, dividendos, renda passiva, investir em ações"
)

gerar_pagina(
    "warren-buffett",
    "Como Warren Buffett ficou bilionário investindo",
    """
<div style="max-width:900px;margin:auto">

<div class="card">

<h2>💰 Warren Buffett — o maior investidor do mundo</h2>

<p>
Warren Buffett é conhecido como o maior investidor da história.
Ele construiu sua fortuna aplicando os princípios do value investing.
</p>

<p>
Buffett busca empresas sólidas, com vantagem competitiva e boa gestão,
comprando apenas quando estão abaixo do valor justo.
</p>

<p>
Ele evita riscos desnecessários e acredita que o tempo é o maior aliado do investidor.
</p>

<p>
Sua frase mais famosa resume bem sua estratégia:
<strong>"Se você não pretende manter uma ação por 10 anos, não compre por 10 minutos."</strong>
</p>

</div>

<div class="card">

<h2>🧠 Filosofia de investimento</h2>

<ul>
<li>Comprar empresas com vantagem competitiva</li>
<li>Pensar no longo prazo</li>
<li>Evitar especulação</li>
<li>Investir no que entende</li>
</ul>

</div>

<div class="card">

<h2>📚 Quer aprender direto com ele?</h2>

<p>
Se você quer entender exatamente como Buffet pensa e investe, esse é o melhor ponto de partida:
</p>

<a href="https://amzn.to/4uT0Lh0" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro do Warren Buffett
</a>

</div>

<div class="card">
<a href="../index.html">← Ver ranking de ações</a>
</div>

<<div class="card">
<h2>O Basico de todo investidor</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Antes de escolher ações, os melhores investidores dominam o essencial:
mentalidade, disciplina e visão de longo prazo.</p>
<nav aria-label="O Basico de todo investidor" class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>

</div>
""",
    descricao="Conheça a estratégia de Warren Buffett.",
    keywords="warren buffett, value investing, melhores investidores"
)

gerar_pagina(
    "benjamin-graham",
    "Benjamin Graham — pai do value investing",
    """
<div style="max-width:900px;margin:auto">

<div class="card">

<h2>📘 Benjamin Graham — pai do value investing</h2>

<p>
Benjamin Graham foi o criador da análise fundamentalista moderna
e mentor de Warren Buffett.
</p>

<p>
Ele desenvolveu o conceito de comprar ações abaixo do valor justo,
utilizando uma margem de segurança para reduzir riscos.
</p>

<p>
Graham via o mercado como emocional e irracional no curto prazo,
mas eficiente no longo prazo.
</p>

<p>
Seu ensinamento principal:
<strong>o preço é o que você paga, o valor é o que você recebe.</strong>
</p>

</div>

<div class="card">

<h2>🧠 Princípios fundamentais</h2>

<ul>
<li>Comprar com margem de segurança</li>
<li>Focar no valor, não no preço</li>
<li>Ignorar emoções do mercado</li>
<li>Investir com disciplina</li>
</ul>

</div>

<div class="card">

<h2>📊 O conceito de margem de segurança</h2>

<p>
Graham defendia que o investidor deve comprar ativos com desconto em relação ao valor justo.
Isso reduz risco e aumenta o potencial de retorno.
</p>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Quer aprender direto com ele?</h2>

<p>
Se você quer entender exatamente como Graham pensa e investe, esse é o melhor ponto de partida:
</p>


<a href="https://amzn.to/4bMAYOV" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro do Benjamin Graham
</a>

</div>

<div class="card">
<a href="../index.html">📊 Ver ações baratas agora →</a>
</div>

<<div class="card">
<h2>O Basico de todo investidor</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Antes de escolher ações, os melhores investidores dominam o essencial:
mentalidade, disciplina e visão de longo prazo.</p>
<nav aria-label="O Basico de todo investidor" class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>

</div>
""",
    descricao="Conheça Benjamin Graham e o conceito de value investing.",
    keywords="benjamin graham, value investing, investir em valor"
)

gerar_pagina(
    "peter-lynch",
    "Peter Lynch — investir no que você conhece",
    """
<div style="max-width:900px;margin:auto">

<div class="card">

<h2>📈 Peter Lynch — investir no que você conhece</h2>

<p>
Peter Lynch ficou famoso por mostrar que qualquer pessoa pode investir bem,
desde que observe o mundo ao seu redor.
</p>

<p>
Sua estratégia é baseada em identificar empresas que fazem parte do seu dia a dia
antes que o mercado perceba seu potencial.
</p>

<p>
Ele acredita que investidores comuns têm vantagem,
pois conseguem enxergar tendências no consumo antes dos grandes fundos.
</p>

<p>
A ideia principal é simples:
<strong>invista em negócios que você entende.</strong>
</p>

</div>

<div class="card">

<h2>🧠 Filosofia</h2>

<ul>
<li>Invista no que você conhece</li>
<li>Observe o dia a dia</li>
<li>Busque empresas em crescimento</li>
<li>Pense no longo prazo</li>
</ul>

</div>

<div class="card">

<h2>🔍 Exemplo prático</h2>

<p>
Se você percebe que uma marca está crescendo e sendo cada vez mais usada,
isso pode ser um sinal de oportunidade.
</p>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Quer aprender direto com ele?</h2>

<p>
Se você quer entender exatamente como Lynch pensa e investe, esse é o melhor ponto de partida:
</p>

<a href="https://amzn.to/47rVy5H" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro do Peter Lynch
</a>

</div>

<div class="card">
<a href="../index.html">📊 Ver ranking de ações →</a>
</div>

<div class="card">
<h2>O Basico de todo investidor</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Antes de escolher ações, os melhores investidores dominam o essencial:
mentalidade, disciplina e visão de longo prazo.</p>
<nav aria-label="O Basico de todo investidor" class="menu">
    <a href="pai-rico-pai-pobre.html">💰 Pai Rico, Pai Pobre</a>
    <a href="homem-mais-rico-babilonia.html">🏺 O Homem Mais Rico da Babilônia</a>
    <a href="mente-milionaria.html">🧠 Os Segredos da Mente Milionária</a>
</nav>
</div>

</div>
""",
    descricao="Conheça a estratégia de Peter Lynch.",
    keywords="peter lynch, investir no que conhece, ações crescimento"
)

gerar_pagina(
    "pai-rico-pai-pobre",
    "Pai Rico, Pai Pobre — lições financeiras",
    """
<div style="max-width:900px;margin:auto">

<h1>💰 Pai Rico, Pai Pobre</h1>

<p style="color:#cbd5e1">
A escola prepara as crianças para o mundo real? Essa é a primeira pergunta com a qual o leitor se depara neste livro. O recado é ousado e direto: boa formação e notas altas não bastam para assegurar o sucesso de alguém. O mundo mudou; a maioria dos jovens tem cartão de crédito, antes mesmo de concluir os estudos, e nunca teve aula sobre dinheiro, investimentos, juros etc. Ou seja, eles vão para a escola, mas continuam financeiramente improficientes, despreparados para enfrentar um mundo que valoriza mais as despesas do que a poupança.

Para o autor, o conselho mais perigoso que se pode dar a um jovem nos dias de hoje é: “Vá para a escola, tire notas altas e depois procure um trabalho seguro.” O fato é que agora as regras são outras, e não existe mais emprego garantido para ninguém. Pai Rico, Pai Pobre demonstra que a questão não é ser empregado ou empregador, mas ter o controle do próprio destino ou delegá-lo a alguém. É essa a tese de Robert Kiyosaki neste livro substancial e visionário. Para ele, a formação proporcionada pelo sistema educacional não prepara os jovens para o mundo que encontrarão depois de formados.
</p>

<div class="card">

<h2>🧠 Principais ensinamentos</h2>

<ul>
<li>Ativos colocam dinheiro no bolso</li>
<li>Passivos tiram dinheiro do bolso</li>
<li>Trabalhe para aprender, não só para ganhar</li>
<li>Construa renda passiva</li>
</ul>

</div>

<div class="card">

<h2>💡 Mentalidade</h2>

<p>
O livro mostra a diferença entre pensar como pobre e pensar como rico.
</p>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Comece por aqui</h2>

<a href="https://amzn.to/3Pte87v" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro
</a>

</div>

<div class="card">
<a href="../index.html">📊 Ver ações para investir →</a>
</div>

<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Explore rankings prontos com as melhores ações da bolsa hoje.</p>
<nav aria-label="Paginas de livros" class="menu">
<a href="seo/melhores-acoes-para-investir.html">🏆 Melhores ações</a>
<a href="seo/acoes-maior-dividend-yield.html">💰 Dividendos</a>
<a href="seo/acoes-maior-roe.html">📈 Alta rentabilidade</a>
<a href="seo/acoes-mais-seguras.html">🛡️ Mais seguras</a>
<a href="seo/acoes-dividendos-mensais.html">💵 Renda mensal</a>
<a href="seo/acoes-baratas-2026.html">🔥 Ações baratas</a>
<a href="seo/melhores-acoes-dividendos.html">💸 Dividendos 2026</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>


</div>
""",
    descricao="Resumo do livro Pai Rico, Pai Pobre.",
    keywords="pai rico pai pobre resumo, educação financeira"
)

gerar_pagina(
    "homem-mais-rico-babilonia",
    "O Homem Mais Rico da Babilônia — princípios financeiros",
    """
<div style="max-width:900px;margin:auto">

<h1>🏺 O Homem Mais Rico da Babilônia</h1>

<p style="color:#cbd5e1">
Baseando-se nos segredos de sucesso dos antigos babilônicos ― os habitantes da cidade mais rica e próspera de seu tempo ―, George S. Clason mostra soluções ao mesmo tempo sábias e muito atuais para evitar a falta de dinheiro, como não desperdiçar recursos durante tempos de opulência, buscar conhecimento e informação em vez de apenas lucro, assegurar uma renda para o futuro, manter a pontualidade no pagamento de dívidas e, sobretudo, cultivar as próprias aptidões, tornando-se cada vez mais habilidoso e consciente.
</p>

<div class="card">

<h2>💰 Regras clássicas</h2>

<ul>
<li>Pague a si mesmo primeiro</li>
<li>Controle seus gastos</li>
<li>Faça seu dinheiro trabalhar</li>
<li>Proteja seu patrimônio</li>
</ul>

</div>

<div class="card">

<h2>📊 Por que funciona?</h2>

<p>
Porque os princípios são simples, mas consistentes ao longo do tempo.
</p>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Leitura essencial</h2>

<a href="https://amzn.to/4dKRSjp" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro
</a>

</div>

<div class="card">
<a href="../index.html">📊 Ver oportunidades na bolsa →</a>
</div>

<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Explore rankings prontos com as melhores ações da bolsa hoje.</p>
<nav aria-label="Rpaginas de livros" class="menu">
<a href="seo/melhores-acoes-para-investir.html">🏆 Melhores ações</a>
<a href="seo/acoes-maior-dividend-yield.html">💰 Dividendos</a>
<a href="seo/acoes-maior-roe.html">📈 Alta rentabilidade</a>
<a href="seo/acoes-mais-seguras.html">🛡️ Mais seguras</a>
<a href="seo/acoes-dividendos-mensais.html">💵 Renda mensal</a>
<a href="seo/acoes-baratas-2026.html">🔥 Ações baratas</a>
<a href="seo/melhores-acoes-dividendos.html">💸 Dividendos 2026</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>

</div>
""",
    descricao="Aprenda os princípios do Homem Mais Rico da Babilônia.",
    keywords="homem mais rico da babilonia resumo"
)

gerar_pagina(
    "mente-milionaria",
    "Os Segredos da Mente Milionária",
    """
<div style="max-width:900px;margin:auto">

<h1>🧠 Os Segredos da Mente Milionária</h1>

<p style="color:#cbd5e1">
"T. Harv Eker desmistifica o motivo pelo qual algumas pessoas estão destinadas à riqueza e outras a uma vida de dureza. Se você quer conhecer as causas fundamentais do sucesso, leia este livro." – Robert G. Allen, autor de O milionário em um minuto


Se as suas finanças andam na corda bamba, talvez esteja na hora de você refletir sobre o que T. Harv Eker chama de "o seu modelo de dinheiro" – um conjunto de crenças que cada um de nós alimenta desde a infância e que molda o nosso destino financeiro, quase sempre nos levando para uma situação difícil.

Nesse livro, Eker mostra como substituir uma mentalidade destrutiva – que você talvez nem perceba que tem – pelos "arquivos de riqueza", 17 modos de pensar e agir que distinguem os ricos das demais pessoas. Alguns desses princípios fundamentais são:

• Ou você controla o seu dinheiro ou ele controlará você.

• O hábito de administrar as finanças é mais importante do que a quantidade de dinheiro que você tem.

• A sua motivação para enriquecer é crucial: se ela possui uma raiz negativa, como o medo, a raiva ou a necessidade de provar algo a si mesmo, o dinheiro nunca lhe trará felicidade.

• O segredo do sucesso não é tentar evitar os problemas nem se livrar deles, mas crescer pessoalmente para se tornar maior do que qualquer adversidade.

• Os gastos excessivos têm pouco a ver com o que você está comprando e tudo a ver com a falta de satisfação na sua vida.

O autor também ensina um método eficiente de administrar o dinheiro. Você aprenderá a estabelecer sua remuneração pelos resultados que apresenta e não pelas horas que trabalha. Além disso, saberá como aumentar o seu patrimônio líquido – a verdadeira medida da riqueza.

A ideia é fazer o seu dinheiro trabalhar para você tanto quanto você trabalha para ele. Para isso, é necessário poupar e investir em vez de gastar. "Enriquecer não diz respeito somente a ficar rico em termos financeiros", diz Eker. "É mais do que isso: trata-se da pessoa que você se torna para alcançar esse objetivo."
</p>

<div class="card">

<h2>🧠 Ideia central</h2>

<p>
Seu resultado financeiro é reflexo do seu modelo mental.
</p>

</div>

<div class="card">

<h2>💡 Lições principais</h2>

<ul>
<li>Ricos pensam diferente</li>
<li>Assuma responsabilidade financeira</li>
<li>Foque em crescer</li>
<li>Construa ativos</li>
</ul>

</div>

<div class="card" style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);">

<h2>📚 Comece a mudar sua mentalidade</h2>

<a href="https://amzn.to/4rW4VSI" target="_blank" style="display:inline-block;margin-top:12px;padding:14px 20px;background:#22c55e;color:white;border-radius:10px;text-decoration:none;font-weight:700;">
👉 Ver livro
</a>

</div>

<div class="card">
<a href="../index.html">📊 Ver ranking de ações →</a>
</div>

<div class="card">
<h2>🚀 Descubra oportunidades</h2>
<p style="color:#cbd5e1;font-size:14px;margin-bottom:15px">Explore rankings prontos com as melhores ações da bolsa hoje.</p>
<nav aria-label="paginas de livros" class="menu">
<a href="seo/melhores-acoes-para-investir.html">🏆 Melhores ações</a>
<a href="seo/acoes-maior-dividend-yield.html">💰 Dividendos</a>
<a href="seo/acoes-maior-roe.html">📈 Alta rentabilidade</a>
<a href="seo/acoes-mais-seguras.html">🛡️ Mais seguras</a>
<a href="seo/acoes-dividendos-mensais.html">💵 Renda mensal</a>
<a href="seo/acoes-baratas-2026.html">🔥 Ações baratas</a>
<a href="seo/melhores-acoes-dividendos.html">💸 Dividendos 2026</a>
<a href="seo/investidores.html">📚 Maiores investidores da bolsa</a>
</nav>
</div>

</div>
""",
    descricao="Aprenda a mentalidade dos ricos.",
    keywords="mente milionaria, educação financeira mentalidade"
)
