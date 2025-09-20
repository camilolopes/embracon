import streamlit as st
import pandas as pd
from typing import List, Tuple

st.set_page_config(page_title="Sorteio Consórcio (Embracon)", page_icon="🎯", layout="wide")

# -------------------------------
# Helpers
# -------------------------------

def parse_bilhetes(raw: str) -> List[str]:
    """Parse user input into a list of 5-digit ticket strings (left-pad with zeros)."""
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    norm = []
    for p in parts:
        digits = ''.join(ch for ch in p if ch.isdigit())
        if not digits:
            continue
        if len(digits) > 5:
            digits = digits[-5:]  # keep last 5 digits
        norm.append(digits.zfill(5))
    return norm


def gerar_centenas_por_bilhete(b: str) -> List[str]:
    """For groups <= 1000: 3 centenas per prize (digits 3-4-5, 2-3-4, 1-2-3)."""
    assert len(b) == 5
    return [b[2:5], b[1:4], b[0:3]]


def gerar_milhares_por_bilhete(b: str) -> List[str]:
    """For groups 1001..10000: 2 milhares per prize (digits 2-3-4-5, 1-2-3-4)."""
    assert len(b) == 5
    return [b[1:5], b[0:4]]


def calcular_probabilidade(grupo_tamanho: int, n_bilhetes: int) -> Tuple[float, str]:
    """Return (probability per draw for a specific number, human label)."""
    if grupo_tamanho <= 1000:
        # space size: 1000 (000..999), windows per ticket = 3
        p_per_window = 1/1000
        windows = 3
        label = "centena"
    else:
        # space size: 10000 (0000..9999), windows per ticket = 2
        p_per_window = 1/10000
        windows = 2
        label = "milhar"
    p_ticket = windows * p_per_window
    p_draw = 1 - (1 - p_ticket) ** max(1, n_bilhetes)
    return p_draw, label


def to_int(s: str) -> int:
    try:
        return int(s)
    except Exception:
        return 0

# -------------------------------
# UI
# -------------------------------

st.title("🎯 Simulador de Contemplação — Regra Consórcio (Embracon)")
st.caption("Informe os bilhetes sorteados e o tamanho do grupo. O app aplica automaticamente a regra correta: 3 centenas por prêmio (≤1000 participantes) ou 2 milhares por prêmio (1001 a 10000).")

with st.sidebar:
    st.header("⚙️ Parâmetros")
    grupo_tamanho = st.number_input("Tamanho do grupo", min_value=2, max_value=10000, value=1000, step=1, help="Até 1000: usa centenas. 1001..10000: usa milhares.")
    limite_cota = st.number_input("Limitar exibição até o número", min_value=0, max_value=10000, value=600, step=1)
    minhas_cotas_raw = st.text_input("Minhas cotas (separe por vírgula)", placeholder="Ex.: 070, 471, 590")
    st.markdown("---")
    st.write("**Dica:** Bilhetes devem ter 5 dígitos (o app completa zeros à esquerda). Ex.: 01927 → 01927; 1927 → 01927")

st.subheader("1) Bilhetes sorteados (5 prêmios)")
raw_bilhetes = st.text_area("Cole os 5 bilhetes sorteados (separe por vírgula ou quebra de linha)",
                            value="", height=120,
                            placeholder="Ex.: 48602, 01927, 82187, 34246, 68744")

bilhetes = parse_bilhetes(raw_bilhetes)
col_valid, col_preview = st.columns([1, 2])
with col_valid:
    st.metric(label="Bilhetes válidos", value=len(bilhetes))
with col_preview:
    if bilhetes:
        st.write("**Prévia:**", ", ".join(bilhetes))
    else:
        st.info("Insira os bilhetes para começar.")

if bilhetes:
    # Geração de números conforme regra
    if grupo_tamanho <= 1000:
        construidos = [x for b in bilhetes for x in gerar_centenas_por_bilhete(b)]
        regra_label = "Centenas (3 por prêmio)"
        width = 3
    else:
        construidos = [x for b in bilhetes for x in gerar_milhares_por_bilhete(b)]
        regra_label = "Milhares (2 por prêmio)"
        width = 4

    st.subheader("2) Números gerados pela regra")
    st.write(f"**Regra aplicada:** {regra_label}")

    # Dataframe consolidado
    df = pd.DataFrame({"bilhete": [b for b in bilhetes for _ in range(3 if grupo_tamanho <= 1000 else 2)],
                       "numero": construidos})

    # Ordenação e duplicatas
    df_unique = (df
                 .assign(numero_int=df["numero"].astype(int))
                 .sort_values(["numero_int", "bilhete"])\
                 .drop_duplicates(subset=["numero"]))

    # Filtro por limite
    lim = int(limite_cota)
    df_filtrado = df_unique[df_unique["numero_int"] <= lim].copy()
    df_filtrado = df_filtrado.sort_values("numero_int", ascending=False).reset_index(drop=True)

    c1, c2 = st.columns(2)
    with c1:
        st.write("**Todos os números gerados (sem filtro):**")
        st.dataframe(df_unique[["numero", "bilhete"]].reset_index(drop=True), use_container_width=True)
    with c2:
        st.write(f"**Mais próximos (≤ {lim}):**")
        if df_filtrado.empty:
            st.warning("Nenhum número gerado está dentro do limite informado.")
        else:
            st.dataframe(df_filtrado[["numero", "bilhete"]], use_container_width=True)

    # Probabilidade por concurso para um número específico
    p_draw, unidade = calcular_probabilidade(grupo_tamanho, n_bilhetes=len(bilhetes))
    st.subheader("3) Probabilidade por concurso")
    st.write(f"Probabilidade de **uma {unidade} específica** aparecer em pelo menos um dos prêmios deste concurso:")
    st.metric(label="Probabilidade por concurso", value=f"{p_draw*100:.3f}%", delta=f"odds ≈ 1 em {1/p_draw:.2f}")

    # Checagem de minhas cotas
    if minhas_cotas_raw:
        minhas = [s.strip() for s in minhas_cotas_raw.split(',') if s.strip()]
        pad = (3 if grupo_tamanho <= 1000 else 4)
        minhas_norm = [str(int(c)).zfill(pad) for c in minhas if c.isdigit() or (c.replace('0','').isdigit())]
        st.subheader("4) Minhas cotas — conferência")
        if not minhas_norm:
            st.warning("Nenhuma cota válida informada.")
        else:
            hit_set = set(df_unique["numero"].tolist())
            rows = []
            for c in minhas_norm:
                rows.append({
                    "cota": c,
                    "contemplada_este_concurso?": "Sim" if c in hit_set else "Não"
                })
            df_minas = pd.DataFrame(rows)
            st.dataframe(df_minas, use_container_width=True)

    # Downloads
    st.subheader("5) Exportar resultados")
    csv = df_unique[["numero", "bilhete"]].to_csv(index=False).encode("utf-8")
    st.download_button("Baixar todos os números gerados (CSV)", data=csv, file_name="numeros_gerados.csv", mime="text/csv")

    csv2 = df_filtrado[["numero", "bilhete"]].to_csv(index=False).encode("utf-8")
    st.download_button(f"Baixar filtrados ≤ {lim} (CSV)", data=csv2, file_name="numeros_filtrados.csv", mime="text/csv")

else:
    st.info("👆 Insira os bilhetes no campo acima para ver os resultados.")
