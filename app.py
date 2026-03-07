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

    for col in ciclos.columns:
        ciclos[col] = ciclos[col].fillna("").astype(str).str.strip()

    for col in cortes.columns:
        cortes[col] = cortes[col].fillna("").astype(str).str.strip()

    df = pd.merge(
        ciclos,
        cortes[["nivel", "ciclo", "centro", "via_a", "via_b", "via_c", "via_a1", "via_a2"]],
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


def calcular_puntuacion(nivel_sim, via_sim, nota_media, madrid, anio, relacionada=False, mencion=False, aprovechamiento=False):
    puntos = puntos_por_nota(nota_media)
    detalle = [("Nota media", puntos)]

    if nivel_sim == "Grado Medio":
        if via_sim == "Vía A":
            p = 12 if madrid else 2
            puntos += p
            detalle.append(("ESO en Madrid / fuera", p))
            if mencion:
                puntos += 3
                detalle.append(("Diploma de Mención Honorífica", 3))
            if aprovechamiento:
                puntos += 2
                detalle.append(("Diploma de Aprovechamiento", 2))

        elif via_sim == "Vía B":
            p = 12 if madrid else 2
            puntos += p
            detalle.append(("FP Básica en Madrid / fuera", p))
            if relacionada:
                puntos += 5
                detalle.append(("Familia profesional relacionada", 5))

        elif via_sim == "Vía C":
            p = 12 if madrid else 2
            puntos += p
            detalle.append(("Título/prueba en Madrid / fuera", p))
            p_anio = puntos_por_anio(anio)
            puntos += p_anio
            detalle.append(("Año de obtención/superación", p_anio))

    elif nivel_sim == "Grado Superior":
        if via_sim == "Vía A":
            if relacionada:
                puntos += 5
                detalle.append(("Modalidad de Bachiller relacionada", 5))
            p = 12 if madrid else 2
            puntos += p
            detalle.append(("Bachillerato en Madrid / fuera", p))
            p_anio = puntos_por_anio(anio)
            puntos += p_anio
            detalle.append(("Año de obtención", p_anio))

        elif via_sim == "Vía B":
            p = 12 if madrid else 2
            puntos += p
            detalle.append(("Grado Medio en Madrid / fuera", p))
            p_anio = puntos_por_anio(anio)
            puntos += p_anio
            detalle.append(("Año de obtención", p_anio))
            if relacionada:
                puntos += 10
                detalle.append(("Misma familia profesional", 10))

        elif via_sim == "Vía C":
            p = 12 if madrid else 2
            puntos += p
            detalle.append(("Título/prueba en Madrid / fuera", p))
            p_anio = puntos_por_anio(anio)
            puntos += p_anio
            detalle.append(("Año de obtención/superación", p_anio))

    return round(puntos, 2), detalle


def to_float_safe(value):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


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
- La **nota media** aporta entre **6 y 12 puntos** según tramos.
- Luego se suman criterios por **vía**: centro en Madrid o fuera, año de obtención y, según el caso, modalidad relacionada, misma familia profesional, diplomas, etc.
- En la parte inferior puedes marcar exactamente qué condiciones cumples y calcular tu puntuación estimada.
"""
)

familias = ["Todas"] + sorted([f for f in df["familia"].dropna().unique() if str(f).strip()])
municipios = ["Todos"] + sorted([m for m in df["municipio"].dropna().unique() if str(m).strip()])

col1, col2, col3, col4, col5 = st.columns([2.3, 1, 1.3, 1.2, 1.1])

with col1:
    query = st.text_input(
        "Buscar por palabra",
        placeholder="Ej.: sanidad, informática, marketing, deporte..."
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

s1, s2, s3, s4 = st.columns([1.1, 1.1, 1, 1])

with s1:
    nivel_sim = st.selectbox("Nivel del simulador", ["Grado Medio", "Grado Superior"])

with s2:
    if nivel_sim == "Grado Medio":
        via_sim = st.selectbox("Vía", ["Vía A", "Vía B", "Vía C"])
    else:
        via_sim = st.selectbox("Vía", ["Vía A", "Vía B", "Vía C"])

with s3:
    nota_media = st.number_input("Nota media", min_value=0.0, max_value=10.0, value=7.0, step=0.01)

with s4:
    madrid = st.toggle("Título o estudios en Madrid", value=True)

extra1, extra2, extra3 = st.columns([1, 1, 1])

with extra1:
    anio = st.number_input("Año de obtención / superación", min_value=1990, max_value=2030, value=2025, step=1)

with extra2:
    relacionada = st.toggle("Relación con la familia / modalidad", value=False)

with extra3:
    mencion = False
    aprovechamiento = False
    if nivel_sim == "Grado Medio" and via_sim == "Vía A":
        mencion = st.toggle("Mención Honorífica", value=False)
        aprovechamiento = st.toggle("Aprovechamiento", value=False)

puntuacion, detalle = calcular_puntuacion(
    nivel_sim=nivel_sim,
    via_sim=via_sim,
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

solo_alcanza = st.toggle("Mostrar solo ciclos cuyo corte alcanzo o supero", value=False)

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

    if nivel == "Grado Medio":
        corte_col = "via_a" if via_sim == "Vía A" else "via_b" if via_sim == "Vía B" else "via_c"
    elif nivel == "Grado Superior":
        # En los baremos de corte de GS lo publicado separa A1 y A2, mientras el anexo general habla de Vía A.
        # Para el simulador, Vía A se compara con la mejor de A1/A2 mostradas.
        if via_sim == "Vía A":
            corte_col = "mejor_via_a"
        elif via_sim == "Vía B":
            corte_col = "via_b"
        else:
            corte_col = "via_c"
    else:
        corte_col = None

    if "via_a1" in filtered.columns and "via_a2" in filtered.columns:
        filtered["via_a1_num"] = filtered["via_a1"].apply(to_float_safe)
        filtered["via_a2_num"] = filtered["via_a2"].apply(to_float_safe)
        filtered["mejor_via_a"] = filtered[["via_a1_num", "via_a2_num"]].min(axis=1, skipna=True)

    if "via_a" in filtered.columns:
        filtered["via_a_num"] = filtered["via_a"].apply(to_float_safe)
    if "via_b" in filtered.columns:
        filtered["via_b_num"] = filtered["via_b"].apply(to_float_safe)
    if "via_c" in filtered.columns:
        filtered["via_c_num"] = filtered["via_c"].apply(to_float_safe)

    if corte_col:
        if corte_col == "mejor_via_a":
            filtered["corte_referencia"] = filtered["mejor_via_a"]
        elif f"{corte_col}_num" in filtered.columns:
            filtered["corte_referencia"] = filtered[f"{corte_col}_num"]
        else:
            filtered["corte_referencia"] = pd.NA

        filtered["Te alcanza"] = filtered["corte_referencia"].apply(
            lambda x: "Sí" if pd.notna(x) and puntuacion >= x else ("No" if pd.notna(x) else "")
        )

        if solo_alcanza:
            filtered = filtered[filtered["Te alcanza"] == "Sí"]

    base_columns = ["ciclo", "municipio", "centro", "modalidad", "turno"]

    if nivel == "Grado Medio":
        preferred_columns = base_columns + ["via_a", "via_b", "via_c", "Te alcanza"]
    elif nivel == "Grado Superior":
        preferred_columns = base_columns + ["via_a1", "via_a2", "via_b", "via_c", "Te alcanza"]
    else:
        preferred_columns = base_columns + ["via_a", "via_a1", "via_a2", "via_b", "via_c", "Te alcanza"]

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
        "Te alcanza": "¿Te alcanza?",
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
**Grado Medio**
- **Vía A**: nota media + Madrid/fuera + Mención Honorífica/Aprovechamiento.
- **Vía B**: nota media + Madrid/fuera + familia profesional relacionada.
- **Vía C**: nota media + Madrid/fuera + año de obtención/superación.

**Grado Superior**
- **Vía A**: nota media + modalidad de Bachiller relacionada + Madrid/fuera + año.
- **Vía B**: nota media + Madrid/fuera + año + misma familia profesional.
- **Vía C**: nota media o prueba + Madrid/fuera + año.
"""
    )
