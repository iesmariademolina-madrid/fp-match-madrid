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

    for col in ["via_a", "via_a1", "via_a2"]:
        if col not in cortes.columns:
            cortes[col] = ""

    for col in ciclos.columns:
        ciclos[col] = ciclos[col].fillna("").astype(str).str.strip()

    for col in cortes.columns:
        cortes[col] = cortes[col].fillna("").astype(str).str.strip()

    df = pd.merge(
        ciclos,
        cortes[["nivel", "ciclo", "centro", "via_a", "via_a1", "via_a2"]],
        on=["nivel", "ciclo", "centro"],
        how="left"
    )

    for col in df.columns:
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


def puntos_por_nota(nota_media):
    if nota_media >= 9:
        return 12
    if nota_media >= 8:
        return 11
    if nota_media >= 7:
        return 10
    if nota_media >= 6:
        return 8
    if nota_media >= 5:
        return 6
    return 0


def puntos_por_anio(anio):
    if anio >= 2008:
        return 6
    if anio == 2007:
        return 4
    if anio == 2006:
        return 3
    if anio == 2005:
        return 2
    if anio == 2004:
        return 1
    if anio == 2003:
        return 0.5
    return 0


def calcular_puntuacion_via_a(nivel_sim, nota_media, madrid, anio=None,
                              relacionada=False, mencion=False, aprovechamiento=False):
    puntos = puntos_por_nota(nota_media)
    detalle = [("Nota media", puntos)]

    if nivel_sim == "Grado Medio":
        p = 12 if madrid else 2
        puntos += p
        detalle.append(("ESO en Madrid / fuera", p))

        if mencion:
            puntos += 3
            detalle.append(("Diploma de Mención Honorífica", 3))

        if aprovechamiento:
            puntos += 2
            detalle.append(("Diploma de Aprovechamiento", 2))

    else:
        if relacionada:
            puntos += 5
            detalle.append(("Modalidad de Bachiller relacionada", 5))

        p = 12 if madrid else 2
        puntos += p
        detalle.append(("Bachillerato en Madrid / fuera", p))

        p_anio = puntos_por_anio(anio)
        puntos += p_anio
        detalle.append(("Año de obtención", p_anio))

    return round(puntos, 2), detalle


def to_float_safe(value):
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    text = text.replace(",", ".")
    try:
        return float(text)
    except Exception:
        return None


def preparar_columnas_numericas(df):
    out = df.copy()
    if "via_a" in out.columns:
        out["via_a_num"] = out["via_a"].apply(to_float_safe)
    if "via_a1" in out.columns:
        out["via_a1_num"] = out["via_a1"].apply(to_float_safe)
    if "via_a2" in out.columns:
        out["via_a2_num"] = out["via_a2"].apply(to_float_safe)
    return out


def aplicar_comparacion_puntuacion(df, nivel_tabla, puntuacion):
    out = preparar_columnas_numericas(df)

    if nivel_tabla == "Grado Medio":
        out["corte_referencia"] = out["via_a_num"]
        out["¿Te alcanza?"] = out["corte_referencia"].apply(
            lambda x: "Sí" if pd.notna(x) and puntuacion >= x else ("No" if pd.notna(x) else "")
        )

    elif nivel_tabla == "Grado Superior":
        # Compara por separado A1 y A2 para que sea correcto y transparente
        out["¿Te alcanza A1?"] = out["via_a1_num"].apply(
            lambda x: "Sí" if pd.notna(x) and puntuacion >= x else ("No" if pd.notna(x) else "")
        )
        out["¿Te alcanza A2?"] = out["via_a2_num"].apply(
            lambda x: "Sí" if pd.notna(x) and puntuacion >= x else ("No" if pd.notna(x) else "")
        )
        out["alcanza_alguna"] = out.apply(
            lambda r: (
                r.get("¿Te alcanza A1?", "") == "Sí"
                or r.get("¿Te alcanza A2?", "") == "Sí"
            ),
            axis=1,
        )

    return out


st.title("FP Match Madrid")
st.caption("Consulta ciclos de FP en Madrid y sus notas de corte oficiales (curso 2025-2026)")

try:
    df = load_dataset()
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.stop()

st.info(
    """
**Baremo resumido**
- La **nota media** aporta una parte de la puntuación.
- En **Grado Medio** se simula solo la **Vía A**.
- En **Grado Superior** se simula solo la **Vía A**, y se compara con los cortes publicados de **A1** y **A2**.
- Después puedes ver qué ciclos quedan a tu alcance según esa puntuación.
"""
)

familias = ["Todas"] + sorted([f for f in df["familia"].dropna().unique() if str(f).strip()])
municipios = ["Todos"] + sorted([m for m in df["municipio"].dropna().unique() if str(m).strip()])

col1, col2, col3, col4, col5 = st.columns([2.3, 1, 1.3, 1.2, 1.1])

with col1:
    query = st.text_input(
        "Buscar por palabra",
        placeholder="Ej.: sanidad, informática, marketing..."
    )

with col2:
    nivel = st.selectbox("Nivel", ["Todos", "Grado Medio", "Grado Superior"])

with col3:
    familia = st.selectbox("Familia profesional", familias)

with col4:
    municipio = st.selectbox("Municipio", municipios)

with col5:
    turno_filtro = st.selectbox("Turno", ["Ambas", "Diurno", "Vespertino"])

st.markdown("---")
st.subheader("Simulador de puntuación")

s1, s2, s3, s4 = st.columns([1.2, 1, 1, 1])

with s1:
    nivel_sim = st.selectbox("Nivel del simulador", ["Grado Medio", "Grado Superior"])

with s2:
    nota_media = st.number_input("Nota media", min_value=0.0, max_value=10.0, value=7.0, step=0.01)

with s3:
    madrid = st.toggle("Estudios realizados en Madrid", value=True)

with s4:
    if nivel_sim == "Grado Superior":
        anio = st.number_input("Año de obtención", min_value=1990, max_value=2030, value=2025, step=1)
    else:
        anio = None

extra1, extra2 = st.columns([1, 1])

with extra1:
    relacionada = False
    if nivel_sim == "Grado Superior":
        relacionada = st.toggle("Modalidad de Bachiller relacionada", value=False)

with extra2:
    mencion = False
    aprovechamiento = False
    if nivel_sim == "Grado Medio":
        mencion = st.toggle("Mención Honorífica", value=False)
        aprovechamiento = st.toggle("Aprovechamiento", value=False)

puntuacion, detalle = calcular_puntuacion_via_a(
    nivel_sim=nivel_sim,
    nota_media=nota_media,
    madrid=madrid,
    anio=anio,
    relacionada=relacionada,
    mencion=mencion,
    aprovechamiento=aprovechamiento,
)

st.success(f"Puntuación estimada: **{puntuacion} puntos**")

detalle_df = pd.DataFrame(detalle, columns=["Criterio", "Puntos"])
st.dataframe(detalle_df, use_container_width=True, hide_index=True)

solo_alcanza = st.toggle("Mostrar solo los ciclos que podría hacer", value=False)

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

    # Para asegurar la comparación correcta, si el nivel del buscador está en "Todos",
    # se filtra por el nivel elegido en el simulador.
    nivel_tabla = nivel
    if nivel_tabla == "Todos":
        nivel_tabla = nivel_sim
        filtered = filtered[filtered["nivel"] == nivel_sim]

    filtered = aplicar_comparacion_puntuacion(filtered, nivel_tabla, puntuacion)

    if nivel_tabla == "Grado Medio":
        if solo_alcanza:
            filtered = filtered[filtered["¿Te alcanza?"] == "Sí"]

        preferred_columns = [
            "ciclo",
            "municipio",
            "centro",
            "modalidad",
            "turno",
            "via_a",
            "¿Te alcanza?",
        ]

    else:
        if solo_alcanza:
            filtered = filtered[
                (filtered["¿Te alcanza A1?"] == "Sí") | (filtered["¿Te alcanza A2?"] == "Sí")
            ]

        preferred_columns = [
            "ciclo",
            "municipio",
            "centro",
            "modalidad",
            "turno",
            "via_a1",
            "via_a2",
            "¿Te alcanza A1?",
            "¿Te alcanza A2?",
        ]

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
        "¿Te alcanza?": "¿Te alcanza?",
        "¿Te alcanza A1?": "¿Te alcanza A1?",
        "¿Te alcanza A2?": "¿Te alcanza A2?",
    }

    st.markdown("---")
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

with st.expander("Ver resumen del baremo"):
    st.markdown(
        """
**Grado Medio – Vía A**
- Nota media
- Estudios en Madrid o fuera
- Mención Honorífica
- Aprovechamiento

**Grado Superior – Vía A**
- Nota media
- Modalidad de Bachiller relacionada
- Estudios en Madrid o fuera
- Año de obtención

La tabla compara esa puntuación con los cortes oficiales mostrados para cada nivel.
"""
    )
