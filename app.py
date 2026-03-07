import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="FP Match Madrid",
    layout="wide"
)

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

    # Normalizar nombres de columnas por si hubiera diferencias de mayúsculas/minúsculas
    ciclos.columns = [c.strip().lower() for c in ciclos.columns]
    cortes.columns = [c.strip().lower() for c in cortes.columns]

    # Ajusta estas columnas si en tus CSV tienen otro nombre
    required_ciclos = ["nivel", "familia", "ciclo", "municipio", "centro", "modalidad", "turno"]
    required_cortes = ["nivel", "ciclo", "centro"]

    for col in required_ciclos:
        if col not in ciclos.columns:
            st.error(f"Falta la columna '{col}' en ciclos.csv")
            st.stop()

    for col in required_cortes:
        if col not in cortes.columns:
            st.error(f"Falta la columna '{col}' en cortes.csv")
            st.stop()

    # Merge básico por nivel + ciclo + centro
    df = pd.merge(
        ciclos,
        cortes,
        on=["nivel", "ciclo", "centro"],
        how="left"
    )

    # Rellenar vacíos para evitar errores en filtros/búsquedas
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].fillna("")

    return df


def search_cycles(df, query, nivel):
    result = df.copy()

    if nivel != "Todos":
        result = result[result["nivel"] == nivel]

    if query.strip():
        q = query.strip().lower()
        result = result[
            result["ciclo"].str.lower().str.contains(q, na=False)
            | result["familia"].str.lower().str.contains(q, na=False)
            | result["centro"].str.lower().str.contains(q, na=False)
            | result["municipio"].str.lower().str.contains(q, na=False)
        ]

    return result


st.title("FP Match Madrid")
st.caption("Consulta ciclos de FP en Madrid y sus notas de corte oficiales (curso 2025-2026)")

try:
    df = load_dataset()
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.stop()

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    query = st.text_input(
        "Buscar por palabra",
        placeholder="Ej.: informática, marketing, sanidad..."
    )

with col2:
    nivel = st.selectbox(
        "Nivel",
        ["Todos", "Grado Medio", "Grado Superior"]
    )

with col3:
    municipios = ["Todos"] + sorted([m for m in df["municipio"].dropna().unique() if str(m).strip()])
    municipio = st.selectbox("Municipio", municipios)

filtered = search_cycles(df, query, nivel)

if municipio != "Todos":
    filtered = filtered[filtered["municipio"] == municipio]

# Selección de columnas visibles
preferred_columns = [
    "nivel",
    "familia",
    "ciclo",
    "municipio",
    "centro",
    "modalidad",
    "turno",
    "via_a",
    "via_a1",
    "via_a2",
]

visible_columns = [c for c in preferred_columns if c in filtered.columns]

# Renombrado bonito
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
    display_df = filtered[visible_columns].rename(columns=rename_map)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

with st.expander("¿Cómo se consiguen los puntos?"):
    st.markdown(
        """
### Grado Medio
En las enseñanzas de Grado Medio se usa la **Vía A**, entre otras, según la forma de acceso.  
La puntuación depende del baremo oficial publicado para el curso.

### Grado Superior
En Grado Superior aparecen **Vía A1** y **Vía A2**, además de otras vías.  
Por eso en la tabla verás esas columnas separadas.

### Qué muestra esta app
La tabla reúne:
- la oferta de ciclos
- el centro y municipio
- la modalidad y turno
- las **notas de corte oficiales** del curso 2025-2026

Si un valor no aparece, normalmente significa que no figura en el cruce actual de datos o que no había corte publicado en esa vía.
"""
    )
