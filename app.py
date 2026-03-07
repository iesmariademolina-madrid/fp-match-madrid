import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="FP Match Madrid",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"

# ---------- ESTILOS ----------
st.markdown(
    """
    <style>
    .main {
        padding-top: 1rem;
    }
    .hero-box {
        padding: 1.2rem 1.4rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 100%);
        color: white;
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
    }
    .hero-subtitle {
        font-size: 1rem;
        opacity: 0.95;
    }
    .info-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1rem 1rem 0.85rem 1rem;
        margin: 0.5rem 0 1rem 0;
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        margin-top: 0.2rem;
        margin-bottom: 0.6rem;
    }
    .small-note {
        color: #475569;
        font-size: 0.92rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- CARGA ----------
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

    # Merge base
    df = pd.merge(
        ciclos,
        cortes[["nivel", "ciclo", "centro", "via_a", "via_a1", "via_a2"]],
        on=["nivel", "ciclo", "centro"],
        how="left"
    )

    for col in df.columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df


# ---------- UTILS ----------
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


def calcular_puntuacion_via_a(
    nivel_sim,
    nota_media,
    madrid,
    relacionada=False,
    mencion=False,
    aprovechamiento=False
):
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

    return round(puntos, 2), detalle


def detectar_modalidad_relacionada(ciclo_texto, modalidad_bach):
    ciclo = normalize_scalar(ciclo_texto)
    modalidad = normalize_scalar(modalidad_bach)

    tech_keywords = [
        "informatica", "microinformatica", "asir", "dam", "daw",
        "electric", "electron", "mecani", "automoc", "fabricacion",
        "instalacion", "energia", "quimica", "laboratorio",
        "imagen para el diagnostico", "audiologia", "anatomia",
        "mantenimiento", "robot", "telecom", "edificacion"
    ]
    social_keywords = [
        "administracion", "finanzas", "marketing", "comercio",
        "ventas", "publicidad", "turismo", "agencia de viajes",
        "gestion", "integracion social", "educacion infantil",
        "servicios", "atencion", "mediacion", "documentacion sanitaria"
    ]
    arts_keywords = [
        "imagen", "sonido", "animacion", "audiovisual", "fotografia",
        "iluminacion", "produccion audiovisual", "arte", "grafica"
    ]

    if modalidad == "ciencias y tecnologia":
        return any(k in ciclo for k in tech_keywords)
    if modalidad == "humanidades y ciencias sociales":
        return any(k in ciclo for k in social_keywords)
    if modalidad == "artes":
        return any(k in ciclo for k in arts_keywords)

    return False


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
                "deporte", "deportes", "actividad fisica", "actividades fisicas",
                "actividades fisicas y deportivas", "acondicionamiento fisico",
                "sociodeportiva", "guia en el medio natural", "tiempo libre",
            ],
            "informatica": [
                "informatica", "microinformatica", "dam", "daw", "asir", "smr",
            ],
            "sanidad": [
                "sanidad", "cuidados auxiliares de enfermeria", "higiene bucodental",
                "laboratorio", "diagnostico", "farmacia", "protesis dental",
            ],
            "marketing": [
                "marketing", "comercio", "ventas", "publicidad", "gestion comercial",
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


# ---------- APP ----------
try:
    df = load_dataset()
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.stop()

st.markdown(
    """
    <div class="hero-box">
        <div class="hero-title">FP Match Madrid</div>
        <div class="hero-subtitle">
            Busca ciclos de FP en Madrid, consulta sus notas de corte 2025-2026
            y calcula tu puntuación estimada en la vía A.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="info-card">
        <div class="section-title">Cómo funciona el baremo</div>
        <div class="small-note">
            En esta app trabajamos solo con la <b>vía A</b>, que es la más útil para el alumnado del centro.
            En <b>Grado Medio</b> se compara con la columna <b>Vía A</b>.
            En <b>Grado Superior</b> se compara con las columnas oficiales <b>Vía A1</b> y <b>Vía A2</b>.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

familias = ["Todas"] + sorted([f for f in df["familia"].dropna().unique() if str(f).strip()])
municipios = ["Todos"] + sorted([m for m in df["municipio"].dropna().unique() if str(m).strip()])

# FILTROS
f1, f2, f3, f4, f5 = st.columns([2.4, 1.1, 1.3, 1.2, 1.1])

with f1:
    query = st.text_input(
        "Buscar por palabra",
        placeholder="Ej.: sanidad, informática, marketing..."
    )

with f2:
    nivel = st.selectbox("Nivel", ["Todos", "Grado Medio", "Grado Superior"])

with f3:
    familia = st.selectbox("Familia profesional", familias)

with f4:
    municipio = st.selectbox("Municipio", municipios)

with f5:
    turno_filtro = st.selectbox("Turno", ["Ambas", "Diurno", "Vespertino"])

st.markdown("---")
st.subheader("Simulador de puntuación")

s1, s2, s3 = st.columns([1.1, 1, 1])

with s1:
    nivel_sim = st.selectbox("Nivel del simulador", ["Grado Medio", "Grado Superior"])

with s2:
    nota_media = st.number_input("Nota media", min_value=0.0, max_value=10.0, value=7.0, step=0.01)

with s3:
    madrid = st.toggle("Estudios realizados en Madrid", value=True)

relacionada = False
mencion = False
aprovechamiento = False

if nivel_sim == "Grado Superior":
    sim1, sim2 = st.columns([1.2, 2.2])

    with sim1:
        modalidad_bach = st.selectbox(
            "Modalidad de Bachillerato",
            [
                "Ciencias y Tecnología",
                "Humanidades y Ciencias Sociales",
                "Artes",
                "Otra / No lo sé",
            ],
        )

    with sim2:
        ciclo_objetivo = st.text_input(
            "Ciclo que te interesa",
            placeholder="Ej.: DAW, Higiene Bucodental, Administración y Finanzas..."
        )

    if ciclo_objetivo.strip():
        relacionada = detectar_modalidad_relacionada(ciclo_objetivo, modalidad_bach)
        if relacionada:
            st.success("Tu modalidad de Bachillerato parece relacionada con ese ciclo.")
        else:
            st.warning("No parece una modalidad relacionada, o no se ha podido detectar con claridad.")
    else:
        st.info("Escribe un ciclo concreto y estimaré si la modalidad de Bachillerato está relacionada.")

else:
    sim1, sim2 = st.columns([1, 1])
    with sim1:
        mencion = st.toggle("Mención Honorífica", value=False)
    with sim2:
        aprovechamiento = st.toggle("Aprovechamiento", value=False)

puntuacion, detalle = calcular_puntuacion_via_a(
    nivel_sim=nivel_sim,
    nota_media=nota_media,
    madrid=madrid,
    relacionada=relacionada,
    mencion=mencion,
    aprovechamiento=aprovechamiento,
)

m1, m2, m3 = st.columns(3)
m1.metric("Puntuación estimada", f"{puntuacion} puntos")
m2.metric("Nivel del simulador", nivel_sim)
m3.metric("Resultados en vía usada", "A" if nivel_sim == "Grado Medio" else "A1 / A2")

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

    nivel_tabla = nivel
    if nivel_tabla == "Todos":
        nivel_tabla = nivel_sim
        filtered = filtered[filtered["nivel"] == nivel_sim]

    filtered = aplicar_comparacion_puntuacion(filtered, nivel_tabla, puntuacion)

    dup_keys = ["nivel", "ciclo", "municipio", "centro", "modalidad", "turno"]
    for key in dup_keys:
        if key not in filtered.columns:
            filtered[key] = ""

    filtered["posible_duplicado"] = filtered.duplicated(subset=dup_keys, keep=False)
    filtered["Revisar dato"] = filtered["posible_duplicado"].apply(lambda x: "Sí" if x else "")

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
            "Revisar dato",
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
            "Revisar dato",
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
        "Revisar dato": "Posible duplicado",
    }

    st.markdown("---")
    st.subheader("Resultados")

    r1, r2 = st.columns([1, 1])
    r1.metric("Coincidencias", len(filtered))
    if nivel_tabla == "Grado Medio":
        alcanzables = (filtered.get("¿Te alcanza?", pd.Series(dtype=str)) == "Sí").sum()
    else:
        a1 = (filtered.get("¿Te alcanza A1?", pd.Series(dtype=str)) == "Sí").sum()
        a2 = (filtered.get("¿Te alcanza A2?", pd.Series(dtype=str)) == "Sí").sum()
        alcanzables = max(a1, a2)
    r2.metric("Opciones alcanzables", int(alcanzables))

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

with st.expander("Ver resumen del baremo"):
    st.markdown(
        """
### Grado Medio – Vía A
Se tiene en cuenta:
- la **nota media**
- si los estudios se han realizado en **Madrid o fuera**
- **Mención Honorífica**
- **Aprovechamiento**

### Grado Superior – Vía A
Se tiene en cuenta:
- la **nota media**
- si la **modalidad de Bachillerato está relacionada**
- si el Bachillerato se ha cursado en **Madrid o fuera**

### Importante
El simulador es orientativo.  
La comparación final se hace contra los **cortes oficiales** que aparecen en la tabla.
"""
    )
