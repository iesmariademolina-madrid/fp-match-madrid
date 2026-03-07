import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="FP Match Madrid", layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"


@st.cache_data
def load_dataset():
    ciclos_path = DATA_DIR / "ciclos.csv"
    cortes_path = DATA_DIR / "cortes.csv"

    if not ciclos_path.exists():
        st.error(f"No se encuentra el archivo: {ciclos_path}")
        st.stop()

    if not cortes_path.exists():
        st.error(f"No se encuentra el archivo: {cortes_path}")
        st.stop()

    ciclos = pd.read_csv(ciclos_path)
    cortes = pd.read_csv(cortes_path)

    ciclos.columns = [c.strip().lower() for c in ciclos.columns]
    cortes.columns = [c.strip().lower() for c in cortes.columns]

    required_ciclos = ["nivel", "familia", "ciclo", "municipio", "centro"]
    required_cortes = ["nivel", "ciclo", "centro"]

    for col in required_ciclos:
        if col not in ciclos.columns:
            st.error(f"Falta la columna '{col}' en ciclos.csv")
            st.stop()

    for col in required_cortes:
        if col not in cortes.columns:
            st.error(f"Falta la columna '{col}' en cortes.csv")
            st.stop()

    # Asegurar columnas opcionales
    for col in ["modalidad", "turno"]:
        if col not in ciclos.columns:
            ciclos[col] = ""

    for col in ["via_a", "via_a1", "via_a2"]:
        if col not in cortes.columns:
            cortes[col] = ""

    # Normalización básica de texto para mejorar el merge
    text_cols_ciclos = ["nivel", "ciclo", "centro", "familia", "municipio", "modalidad", "turno"]
    text_cols_cortes = ["nivel", "ciclo", "centro"]

    for col in text_cols_ciclos:
        ciclos[col] = ciclos[col].fillna("").astype(str).str.strip()

    for col in text_cols_cortes + ["via_a", "via_a1", "via_a2"]:
        cortes[col] = cortes[col].fillna("").astype(str).str.strip()

    df = pd.merge(
        ciclos,
        cortes[["nivel", "ciclo", "centro", "via_a", "via_a1", "via_a2"]],
        on=["nivel", "ciclo", "centro"],
        how="left"
    )

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def normalize_text(series):
    return (
        series.astype(str)
        .str.lower()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
    )


def search_cycles(df, query, nivel, familia, municipio):
    result = df.copy()

    if nivel != "Todos":
        result = result[result["nivel"] == nivel]

    if familia != "Todas":
        result = result[result["familia"] == familia]

    if municipio != "Todos":
        result = result[result["municipio"] == municipio]

    if query.strip():
        q = (
            pd.Series([query.strip()])
            .astype(str)
            .str.lower()
            .str.normalize("NFKD")
            .str.encode("ascii", errors="ignore")
            .str.decode("utf-8")
            .iloc[0]
        )

        ciclo_norm = normalize_text(result["ciclo"])
        familia_norm = normalize_text(result["familia"])
        centro_norm = normalize_text(result["centro"])
        municipio_norm = normalize_text(result["municipio"])

        mask = (
            ciclo_norm.str.contains(q, na=False)
            | familia_norm.str.contains(q, na=False)
            | centro_norm.str.contains(q, na=False)
            | municipio_norm.str.contains(q, na=False)
        )

        result = result[mask]

    return result


st.title("FP Match Madrid")
st.caption("Consulta ciclos de FP en Madrid y sus notas de corte oficiales (curso 2025-2026)")

try:
    df = load_dataset()
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.stop()

familias = ["Todas"] + sorted([f for f in df["familia"].dropna().unique() if str(f).strip()])
municipios = ["Todos"] + sorted([m for m in df["municipio"].dropna().unique() if str(m).strip()])

col1, col2, col3, col4 = st.columns([2.2, 1, 1.3, 1.3])

with col1:
    query = st.text_input(
        "Buscar por palabra",
        placeholder="Ej.: sanidad, informática, marketing, deporte..."
    )

with col2:
    nivel = st.selectbox(
        "Nivel",
        ["Todos", "Grado Medio", "Grado Superior"]
    )

with col3:
    familia = st.selectbox("Familia profesional", familias)

with col4:
    municipio = st.selectbox("Municipio", municipios)

filtered = search_cycles(df, query, nivel, familia, municipio)

# Elegir columnas visibles según nivel
base_columns = [
    "nivel",
    "familia",
    "ciclo",
    "municipio",
    "centro",
    "modalidad",
    "turno",
]

if nivel == "Grado Medio":
    preferred_columns = base_columns + ["via_a"]
elif nivel == "Grado Superior":
    preferred_columns = base_columns + ["via_a1", "via_a2"]
else:
    preferred_columns = base_columns + ["via_a", "via_a1", "via_a2"]

visible_columns = [c for c in preferred_columns if c in filtered.columns]

rename_map = {
    "nivel": "Nivel",
    "familia": "Familia profesional",
    "ciclo": "Ciclo",
    "municipio": "Municipio",
    "centro": "Centro",
    "modalidad": "Modalidad",
    "turno": "Turno",
    "via_a": "Corte Vía A",
    "via_a1": "Corte Vía A1",
    "via_a2": "Corte Vía A2",
}

st.subheader("Resultados")
st.write(f"Coincidencias encontradas: {len(filtered)}")

if len(filtered) == 0:
    st.info("No se han encontrado resultados con esa búsqueda.")
else:
    display_df = filtered[visible_columns].copy()

    # Ocultar columnas completamente vacías en la vista actual
    non_empty_cols = []
    for col in display_df.columns:
        if display_df[col].astype(str).str.strip().ne("").any():
            non_empty_cols.append(col)

    display_df = display_df[non_empty_cols].rename(columns=rename_map)

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv = display_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Descargar resultados en CSV",
        data=csv,
        file_name="fp_match_madrid_resultados.csv",
        mime="text/csv"
    )

with st.expander("¿Cómo se consiguen los puntos?"):
    st.markdown(
        """
### Grado Medio
En Grado Medio aparece la **Vía A**, además de otras vías en los listados oficiales.  
En esta app se muestra la **nota de corte de la Vía A** cuando está disponible.

### Grado Superior
En Grado Superior los listados distinguen entre **Vía A1** y **Vía A2**.  
Por eso se muestran como columnas separadas.

### Qué muestra esta app
La tabla reúne:
- el ciclo
- la familia profesional
- el centro y municipio
- la modalidad y el turno
- las **notas de corte oficiales del curso 2025-2026**

### Importante
Si algún valor no aparece, puede deberse a que:
- no figura corte publicado para esa vía
- el cruce entre oferta y baremo no tiene coincidencia exacta
- el dato no estaba disponible en el documento original
"""
    )
