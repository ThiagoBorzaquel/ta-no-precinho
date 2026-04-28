# =========================
# LIMPAR NOMES
# =========================

def limpar_nome_empresa(nome):
    if not isinstance(nome, str):
        return nome

    remover = [
        " ON", " PN", " N1", " N2", " NM",
        "ON ", "PN ", "N1 ", "N2 ", "NM ",
        "ON", "PN", "N1", "N2", "NM"
    ]

    nome_limpo = nome

    for termo in remover:
        nome_limpo = nome_limpo.replace(termo, "")

    nome_limpo = " ".join(nome_limpo.split())

    return nome_limpo.strip()