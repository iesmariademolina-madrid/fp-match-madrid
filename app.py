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

    if ciclos_path.stat().st_size == 0:
        st.error("ciclos.csv está vacío.")
        st.stop()

    if cortes_path.stat().st_size == 0:
        st.error("cortes.csv está vacío.")
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

    for col in ["modalidad", "turno"]:
        if col not in ciclos.columns:
            ciclos[col] = ""

    for col in ["via_a", "via_b", "via_c", "via_a1", "via_a2"]:
        if col not in cortes.columns:
            cortes[col] = ""

    text_cols_ciclos = ["nivel", "familia", "ciclo", "municipio", "centro", "modalidad", "turno"]
    text_cols_cortes = ["nivel", "ciclo", "centro", "via_a", "via_b", "via_c", "via_a1", "via_a2"]

    for col in text_cols_ciclos:
        ciclos[col] = ciclos[col].fillna("").astype(str).str.strip()

    for col in text_cols_cortes:
        cortes[col] = cortes[col].fillna("").astype(str).str.strip()

    df = pd.merge(
        ciclos,
        cortes[["nivel", "ciclo", "centro", "via_a", "via_b", "via_c", "via_a1", "via_a2"]],
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


def normalize_scalar(text):
    return (
        pd.Series([text])
        .astype(str)
        .str.lower()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
        .iloc[0]
    )


def infer_turno_group(turno_value):
    t = normalize_scalar(turno_value)

    if any(x in t for x in ["vespertino", "tarde", "vesp"]):
        return "Vespertino"
    if any(x in t for x in ["diurno", "manana", "mañana", "matutino"]):
        return "Diurno"
    return "Ambas / No indicado"


def search_cycles(df, query, nivel, familia, municipio, turno_filtro):
    result = df.copy()

    if nivel != "Todos":
        result = result[result["nivel"] == nivel]

    if familia != "Todas":
        result = result[result["familia"] == familia]

    if municipio != "Todos":
        result = result[result["municipio"] == municipio]

    result["turno_grupo"] = result["turno"].apply(infer_turno_group)

    if turno_filtro != "Ambas":
        result = result[result["turno_grupo"] == turno_filtro]

    if query.strip():
        q = normalize_scalar(query.strip())

        synonym_map = {
            "deporte": [
                "deporte",
                "deportes",
                "actividad fisica",
                "actividades fisicas",
                "actividades fisicas y deportivas",
                "acondicionamiento fisico",
                "sociodeportiva",
                "guia en el medio natural",
                "tiempo libre",
            ],
            "informatica": [
                "informatica",
                "microinformatica",
                "dam",
                "daw",
                "asir",
                "smr",
            ],
            "sanidad": [
                "sanidad",
                "cuidados auxiliares de enfermeria",
                "higiene bucodental",
                "laboratorio",
                "diagnostico",
                "farmacia",
                "protesis dental",
            ],
            "marketing": [
                "marketing",
                "comercio",
                "ventas",
                "publicidad",
                "gestion comercial",
            ],
        }

        terms = synonym_map.get(q, [q])

        ciclo_norm = normalize_text(result["ciclo"])
        familia_norm = normalize_text(result["familia"])
        centro_norm = normalize_text(result["centro"])
        municipio_norm = normalize_text(result["municipio"])

        mask = pd.Series(False, index=result.index)

        for term in terms:
            mask = mask | ciclo_norm.str.contains(term, na=False)
            mask = mask | familia_norm.str.contains(term, na=False)
            mask = mask | centro_norm.str.contains(term, na=False)
            mask = mask | municipio_norm.str.contains(term, na=False)

        result = result[mask]

    return result


def calcular_puntuacion_simulada(nivel_sim, via_sim, nota_media, relacionada):
    """
    Simulador sencillo y transparente.
    Está pensado como estimación visual para el alumno.
    """
    base = float(nota_media)

    if nivel_sim == "Grado Medio":
        # Versión sencilla: la nota media es la base principal
        return round(base, 2)

    # Grado Superior
    if via_sim == "Vía A1":
        bonus = 0.0 if relacionada else -0.5
        return round(base + bonus, 2)

    if via_sim == "Vía A2":
        bonus = -0.5 if relacionada else 0.0
        return round(base + bonus, 2)

    return round(base, 2)


st.title("FP Match Madrid")
st.caption("Consulta ciclos de FP en Madrid y sus notas de corte oficiales (curso 2025-2026)")

try:
    df = load_dataset()
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.stop()

familias = ["Todas"] + sorted([f for f in df["familia"].dropna().unique() if str(f).strip()])
municipios = ["Todos"] + sorted([m for m in df["municipio"].dropna().unique() if str(m).strip()])

# --- Cartel informativo ---
st.info(
    """
**Cómo funciona el baremo**
- En **Grado Medio** se muestran cortes de **Vía A**, **B** y **C**.
- En **Grado Superior** se muestran cortes de **Vía A1**, **A2**, **B** y **C**.
- La puntuación del alumno depende de su vía de acceso y de su nota media.
- El simulador de abajo sirve para estimar su puntuación y compararla con los cortes publicados.
"""
)

col1, col2, col3, col4, col5 = st.columns([2.3, 1, 1.3, 1.2, 1.1])

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

with col5:
    turno_filtro = st.selectbox("Turno", ["Ambas", "Diurno", "Vespertino"])

hay_filtro_activo = (
    query.strip() != ""
    or nivel != "Todos"
    or familia != "Todas"
    or municipio != "Todos"
    or turno_filtro != "Ambas"
)

if not hay_filtro_activo:
    st.info("Escribe una palabra o aplica algún filtro para ver resultados.")
else:
    filtered = search_cycles(df, query, nivel, familia, municipio, turno_filtro)

    base_columns = [
        "ciclo",
        "municipio",
        "centro",
        "modalidad",
        "turno",
    ]

    if nivel == "Grado Medio":
        preferred_columns = base_columns + ["via_a", "via_b", "via_c"]
    elif nivel == "Grado Superior":
        preferred_columns = base_columns + ["via_a1", "via_a2", "via_b", "via_c"]
    else:
        preferred_columns = base_columns + ["via_a", "via_a1", "via_a2", "via_b", "via_c"]

    visible_columns = [c for c in preferred_columns if c in filtered.columns]

    rename_map = {
        "ciclo": "Ciclo",
        "municipio": "Municipio",
        "centro": "Centro",
        "modalidad": "Modalidad",
        "turno": "Turno",
        "via_a": "Corte Vía A",
        "via_a1": "Corte Vía A1",
        "via_a2": "Corte Vía A2",
        "via_b": "Corte Vía B",
        "via_c": "Corte Vía C",
    }

    st.subheader("Resultados")
    st.write(f"Coincidencias encontradas: {len(filtered)}")

    if len(filtered) == 0:
        st.info("No se han encontrado resultados con esa búsqueda o combinación de filtros.")
    else:
        display_df = filtered[visible_columns].copy()

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

st.markdown("---")
st.subheader("Simulador de puntuación")

sim_col1, sim_col2, sim_col3 = st.columns([1.2, 1.2, 1])

with sim_col1:
    nivel_sim = st.selectbox("Nivel del simulador", ["Grado Medio", "Grado Superior"])

with sim_col2:
    if nivel_sim == "Grado Medio":
        via_sim = st.selectbox("Vía", ["Vía A"])
    else:
        via_sim = st.selectbox("Vía", ["Vía A1", "Vía A2"])

with sim_col3:
    nota_media = st.number_input("Nota media", min_value=0.0, max_value=10.0, value=5.0, step=0.01)

relacionada = False
if nivel_sim == "Grado Superior":
    relacionada = st.toggle("Modalidad / itinerario relacionado", value=True)

puntuacion = calcular_puntuacion_simulada(nivel_sim, via_sim, nota_media, relacionada)

st.success(f"Puntuación estimada: **{puntuacion}**")

with st.expander("Ver detalle del baremo y advertencias"):
    st.markdown(
        """
### Qué debes tener en cuenta
- Este simulador sirve para **orientar**.
- La puntuación final depende del **baremo oficial** y de la **vía de acceso concreta**.
- La **nota de corte** no es fija: cambia según el ciclo, el centro y el curso.
- Compárala siempre con las columnas de corte de la tabla.

### Lectura rápida
- **Grado Medio**: normalmente te fijarás sobre todo en la **Vía A**.
- **Grado Superior**: revisa **A1** o **A2** según tu caso.
"""
    )
