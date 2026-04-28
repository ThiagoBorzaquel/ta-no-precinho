import json
import os


def gerar_dados_graficos(df, output_path="docs/graficos.json"):
    """
    Gera os dados dos gráficos em JSON para consumo no frontend.
    """

    def montar_top(df_base):
        return [
            {
                "ticker": row["Ticker"],
                "empresa": row["Empresa"],
                "valor": round(row["Desconto_%"], 2)
            }
            for _, row in df_base.iterrows()
        ]

    # =========================
    # TOPS
    # =========================

    top10 = df.sort_values("Desconto_%", ascending=False).head(10)

    top_blue = df[df["Categoria"] == "Blue Chips"] \
        .sort_values("Desconto_%", ascending=False).head(10)

    top_mid = df[df["Categoria"] == "Mid Caps"] \
        .sort_values("Desconto_%", ascending=False).head(10)

    top_small = df[df["Categoria"] == "Small Caps"] \
        .sort_values("Desconto_%", ascending=False).head(10)

    data = {
        "top": montar_top(top10),
        "blue": montar_top(top_blue),
        "mid": montar_top(top_mid),
        "small": montar_top(top_small),
    }

    # =========================
    # SALVAR JSON
    # =========================

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("📊 Dados de gráficos gerados em:", output_path)