def gerar_metric(nome, valor, cor="#e2e8f0"):
    return f"""
    <div style="
    background:#020617;
    padding:14px;
    border-radius:14px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    ">
        <span style="color:#cbd5e1">{nome}</span>
        <strong style="color:#e2e8f0">{valor}</strong>
    </div>
    """