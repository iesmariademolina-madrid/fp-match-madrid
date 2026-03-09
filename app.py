import streamlit as st
import pandas as pd
from pathlib import Path
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

st.set_page_config(
    page_title="Orientación FP IES MARÍA DE MOLINA",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "processed"

MEDIO_FILE = DATA_DIR / "BAREMO GRADO MEDIO.xlsx"
SUPERIOR_FILE = DATA_DIR / "BAREMO GRADO SUPERIOR.xlsx"

st.markdown(
    """
    <style>
    .main {
        padding-top: 1rem;
    }
    .hero-box {
        padding: 1.35rem 1.5rem;
        border-radius: 22px;
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #38bdf8 100%);
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 12px 30px rgba(29, 78, 216, 0.18);
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 0.35rem;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        font-size: 1rem;
        opacity: 0.96;
        line-height: 1.45;
    }
    .info-card {
        background: linear-gradient(180deg, #f8fbff 0%, #f1f5f9 100%);
        border: 1px solid #dbeafe;
        border-radius: 18px;
        padding: 1rem 1rem 0.9rem 1rem;
        margin: 0.5rem 0 1rem 0;
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 800;
        margin-top: 0.1rem;
        margin-bottom: 0.55rem;
        color: #0f172a;
    }
    .small-note {
        color: #334155;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .suggestion-box {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 16px;
        padding: 0.95rem 1rem;
        margin: 0.5rem 0 1rem 0;
    }
    .pill {
        display: inline-block;
        padding: 0.28rem 0.7rem;
        margin: 0.18rem 0.25rem 0.18rem 0;
        border-radius: 999px;
        background: #dbeafe;
        color: #1e3a8a;
        font-size: 0.88rem;
        font-weight: 600;
    }
    .total-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1rem;
        margin-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def normalize_scalar(text):
    return (
        pd.Series([text])
        .astype(str)
        .fillna("")
        .str.lower()
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
        .iloc[0]
        .strip()
    )


def clean_text_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


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


def nota_real(nota_media):
    return round(float(nota_media), 2)


def sugerencias_por_modalidad(modalidad):
    modalidad_norm = normalize_scalar(modalidad)

    if modalidad_norm == "ciencias y tecnologia":
        return [
            "Informática y Comunicaciones",
            "Electricidad y Electrónica",
            "Instalación y Mantenimiento",
            "Fabricación Mecánica",
            "Química",
            "Sanidad",
            "Edificación y Obra Civil",
            "Energía y Agua",
        ]

    if modalidad_norm == "humanidades y ciencias sociales":
        return [
            "Administración y Gestión",
            "Comercio y Marketing",
            "Servicios Socioculturales y a la Comunidad",
            "Hostelería y Turismo",
            "Sanidad",
        ]

    if modalidad_norm == "artes":
        return [
            "Imagen y Sonido",
            "Artes Gráficas",
            "Textil, Confección y Piel",
        ]

    return []


def familia_esta_relacionada(familia, modalidad_bach):
    if not modalidad_bach:
        return False

    familias_relacionadas = {
        normalize_scalar(x) for x in sugerencias_por_modalidad(modalidad_bach)
    }
    return normalize_scalar(familia) in familias_relacionadas


def calcular_puntuacion_constante(
    nivel_sim,
    nota_media,
    madrid,
    mencion=False,
    aprovechamiento=False
):
    puntos = nota_real(nota_media)
    detalle = [("Nota media", puntos)]

    if nivel_sim == "Grado Medio":
        extra_madrid = 10 if madrid else 0
        puntos += extra_madrid
        detalle.append(("ESO obtenida en Madrid", extra_madrid))

        if mencion:
            puntos += 3
            detalle.append(("Diploma de Mención Honorífica", 3))

        if aprovechamiento:
            puntos += 2
            detalle.append(("Diploma de Aprovechamiento", 2))

    else:
        extra_madrid = 10 if madrid else 0
        puntos += extra_madrid
        detalle.append(("Título obtenido en Madrid", extra_madrid))
        detalle.append(("Modalidad de Bachillerato relacionada", "+3 solo en los ciclos que correspondan"))

    return round(puntos, 2), detalle


def exact_col(df: pd.DataFrame, name: str):
    normalized = {normalize_scalar(c): c for c in df.columns}
    return normalized.get(normalize_scalar(name))


@st.cache_data
def load_data():
    if not MEDIO_FILE.exists():
        st.error(f"No se encuentra el archivo: {MEDIO_FILE}")
        st.stop()

    if not SUPERIOR_FILE.exists():
        st.error(f"No se encuentra el archivo: {SUPERIOR_FILE}")
        st.stop()

    gm = pd.read_excel(MEDIO_FILE, sheet_name=0)
    gs = pd.read_excel(SUPERIOR_FILE, sheet_name="Datos limpios")

    gm.columns = [str(c).strip() for c in gm.columns]
    gs.columns = [str(c).strip() for c in gs.columns]

    gm_map = {
        "familia": exact_col(gm, "Familia profesional"),
        "ciclo": exact_col(gm, "Ciclo"),
        "municipio": exact_col(gm, "Municipio"),
        "tipo_centro": exact_col(gm, "Tipo centro") or exact_col(gm, "Tipo de centro"),
        "codigo_centro": exact_col(gm, "Código centro") or exact_col(gm, "Código de centro") or exact_col(gm, "Codigo centro"),
        "centro": exact_col(gm, "Centro"),
        "via_a": exact_col(gm, "Nota A") or exact_col(gm, "A"),
    }

    gs_map = {
        "familia": exact_col(gs, "Familia profesional"),
        "ciclo": exact_col(gs, "Ciclo formativo"),
        "municipio": exact_col(gs, "Municipio"),
        "tipo_centro": exact_col(gs, "Tipo de centro") or exact_col(gs, "Tipo centro"),
        "codigo_centro": exact_col(gs, "Código de centro") or exact_col(gs, "Codigo de centro"),
        "centro": exact_col(gs, "Centro docente") or exact_col(gs, "Centro"),
        "modalidad": exact_col(gs, "Modalidad"),
        "turno": exact_col(gs, "Turno"),
        "bilingue": exact_col(gs, "Bilingüe") or exact_col(gs, "Bilingue"),
        "via_a1": exact_col(gs, "Vía A1") or exact_col(gs, "Via A1"),
        "via_a2": exact_col(gs, "Vía A2") or exact_col(gs, "Via A2"),
    }

    missing_gm = [k for k, v in gm_map.items() if k in ["familia", "ciclo", "municipio", "centro", "via_a"] and v is None]
    missing_gs = [k for k, v in gs_map.items() if k in ["familia", "ciclo", "municipio", "centro", "via_a1", "via_a2"] and v is None]

    if missing_gm:
        st.error(f"En el Excel de Grado Medio faltan columnas esperadas: {', '.join(missing_gm)}")
        st.stop()

    if missing_gs:
        st.error(f"En el Excel de Grado Superior faltan columnas esperadas: {', '.join(missing_gs)}")
        st.stop()

    gm_df = pd.DataFrame({
        "nivel": "Grado Medio",
        "familia": clean_text_series(gm[gm_map["familia"]]),
        "ciclo": clean_text_series(gm[gm_map["ciclo"]]),
        "municipio": clean_text_series(gm[gm_map["municipio"]]),
        "tipo_centro": clean_text_series(gm[gm_map["tipo_centro"]]) if gm_map["tipo_centro"] else "",
        "codigo_centro": clean_text_series(gm[gm_map["codigo_centro"]]) if gm_map["codigo_centro"] else "",
        "centro": clean_text_series(gm[gm_map["centro"]]),
        "modalidad": "",
        "turno": "",
        "bilingue": "",
        "via_a": clean_text_series(gm[gm_map["via_a"]]),
        "via_a1": "",
        "via_a2": "",
    })

    gs_df = pd.DataFrame({
        "nivel": "Grado Superior",
        "familia": clean_text_series(gs[gs_map["familia"]]),
        "ciclo": clean_text_series(gs[gs_map["ciclo"]]),
        "municipio": clean_text_series(gs[gs_map["municipio"]]),
        "tipo_centro": clean_text_series(gs[gs_map["tipo_centro"]]) if gs_map["tipo_centro"] else "",
        "codigo_centro": clean_text_series(gs[gs_map["codigo_centro"]]) if gs_map["codigo_centro"] else "",
        "centro": clean_text_series(gs[gs_map["centro"]]),
        "modalidad": clean_text_series(gs[gs_map["modalidad"]]) if gs_map["modalidad"] else "",
        "turno": clean_text_series(gs[gs_map["turno"]]) if gs_map["turno"] else "",
        "bilingue": clean_text_series(gs[gs_map["bilingue"]]) if gs_map["bilingue"] else "",
        "via_a": "",
        "via_a1": clean_text_series(gs[gs_map["via_a1"]]),
        "via_a2": clean_text_series(gs[gs_map["via_a2"]]),
    })

    df = pd.concat([gm_df, gs_df], ignore_index=True)

    for col in df.columns:
        df[col] = clean_text_series(df[col])

    df = df[(df["ciclo"] != "") & (df["centro"] != "")].copy()

    dedup_keys = [
        "nivel", "familia", "ciclo", "municipio", "tipo_centro",
        "centro", "modalidad", "turno", "bilingue", "via_a", "via_a1", "via_a2"
    ]
    df = df.drop_duplicates(subset=dedup_keys).reset_index(drop=True)

    return df


def aplicar_comparacion_puntuacion(
    df: pd.DataFrame,
    nivel_tabla: str,
    puntuacion_constante: float,
    modalidad_bach: str = None
):
    out = df.copy()

    out["via_a_num"] = out["via_a"].apply(to_float_safe)
    out["via_a1_num"] = out["via_a1"].apply(to_float_safe)
    out["via_a2_num"] = out["via_a2"].apply(to_float_safe)

    if nivel_tabla == "Grado Medio":
        out["es_relacionado"] = False
        out["bonus_modalidad"] = 0
        out["puntuacion_total"] = round(float(puntuacion_constante), 2)
        out["Estado"] = out["via_a_num"].apply(
            lambda x: "✅ Te alcanza"
            if pd.notna(x) and float(out["puntuacion_total"].iloc[0]) >= x
            else ("❌ No te alcanza" if pd.notna(x) else "")
        )
    else:
        out["es_relacionado"] = out["familia"].apply(
            lambda fam: familia_esta_relacionada(fam, modalidad_bach)
        )
        out["bonus_modalidad"] = out["es_relacionado"].map({True: 3, False: 0})
        out["puntuacion_total"] = out.apply(
            lambda row: round(float(puntuacion_constante) + float(row["bonus_modalidad"]), 2),
            axis=1
        )

        out["alcanza_a1"] = out.apply(
            lambda row: (
                "Sí" if pd.notna(row["via_a1_num"]) and row["puntuacion_total"] >= row["via_a1_num"]
                else ("No" if pd.notna(row["via_a1_num"]) else "")
            ),
            axis=1
        )
        out["alcanza_a2"] = out.apply(
            lambda row: (
                "Sí" if pd.notna(row["via_a2_num"]) and row["puntuacion_total"] >= row["via_a2_num"]
                else ("No" if pd.notna(row["via_a2_num"]) else "")
            ),
            axis=1
        )

        def resolver_estado(row):
            a1 = row["alcanza_a1"]
            a2 = row["alcanza_a2"]
            if a1 == "Sí" and a2 == "Sí":
                return "✅ Te alcanza"
            if a1 == "Sí" or a2 == "Sí":
                return "⚠️ Parcial"
            if pd.notna(row["via_a1_num"]) or pd.notna(row["via_a2_num"]):
                return "❌ No te alcanza"
            return ""

        out["Estado"] = out.apply(resolver_estado, axis=1)

    return out


def build_aggrid(df_display: pd.DataFrame):
    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_default_column(
        sortable=True,
        filter=True,
        resizable=True,
        wrapText=False,
        autoHeight=False,
    )

    first_col = df_display.columns[0]
    gb.configure_column(first_col, pinned="left")

    estado_style = JsCode(
        """
        function(params) {
            if (params.value === "✅ Te alcanza") {
                return {backgroundColor: "#dcfce7", color: "#166534", fontWeight: "600"};
            }
            if (params.value === "⚠️ Parcial") {
                return {backgroundColor: "#fef3c7", color: "#92400e", fontWeight: "600"};
            }
            if (params.value === "❌ No te alcanza") {
                return {backgroundColor: "#fee2e2", color: "#991b1b", fontWeight: "600"};
            }
            return {};
        }
        """
    )

    if "Resultado" in df_display.columns:
        gb.configure_column("Resultado", cellStyle=estado_style)

    gb.configure_grid_options(domLayout="normal")
    grid_options = gb.build()

    AgGrid(
        df_display,
        gridOptions=grid_options,
        height=480,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        update_mode=GridUpdateMode.NO_UPDATE,
        theme="streamlit",
        enable_enterprise_modules=False,
    )


df = load_data()

st.markdown(
    """
    <div class="hero-box">
        <div class="hero-title">Orientación FP IES MARÍA DE MOLINA</div>
        <div class="hero-subtitle">
            Explora ciclos de FP en Madrid, consulta las notas de corte oficiales y calcula si te alcanza.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="info-card">
        <div class="section-title">Qué puedes hacer aquí</div>
        <div class="small-note">
            En Grado Medio se compara con <b>A</b>. En Grado Superior se compara con <b>A1</b> y <b>A2</b>.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

top1, top2, top3, top4 = st.columns([1.1, 1.4, 1.5, 1.2])

with top1:
    nivel = st.selectbox("Nivel", ["Todos", "Grado Medio", "Grado Superior"])

if nivel == "Grado Medio":
    base_df = df[df["nivel"] == "Grado Medio"].copy()
elif nivel == "Grado Superior":
    base_df = df[df["nivel"] == "Grado Superior"].copy()
else:
    base_df = df.copy()

familias = ["Todas"] + sorted([x for x in base_df["familia"].unique() if x])

with top2:
    familia = st.selectbox("Familia profesional", familias)

if familia != "Todas":
    base_df = base_df[base_df["familia"] == familia].copy()

with top3:
    municipios = sorted([x for x in base_df["municipio"].unique() if x])
    municipios_sel = st.multiselect("Localidades", municipios)

if municipios_sel:
    base_df = base_df[base_df["municipio"].isin(municipios_sel)].copy()

with top4:
    tipos_centro = ["Todos"] + sorted([x for x in base_df["tipo_centro"].unique() if x])
    tipo_centro = st.selectbox("Tipo de centro", tipos_centro)

if tipo_centro != "Todos":
    base_df = base_df[base_df["tipo_centro"] == tipo_centro].copy()

adv1, adv2, adv3, adv4 = st.columns([1.5, 1.2, 1.2, 1.2])

with adv1:
    centros = ["Todos"] + sorted([x for x in base_df["centro"].unique() if x])
    centro = st.selectbox("Centro", centros)

if centro != "Todos":
    base_df = base_df[base_df["centro"] == centro].copy()

with adv2:
    if nivel in ["Todos", "Grado Superior"]:
        modalidades = ["Todas"] + sorted([x for x in base_df["modalidad"].unique() if x])
        modalidad = st.selectbox("Modalidad del ciclo", modalidades)
    else:
        modalidad = "Todas"
        st.selectbox("Modalidad del ciclo", ["No aplica"], disabled=True)

if modalidad != "Todas":
    base_df = base_df[base_df["modalidad"] == modalidad].copy()

with adv3:
    if nivel in ["Todos", "Grado Superior"]:
        turnos = ["Todos"] + sorted([x for x in base_df["turno"].unique() if x])
        turno = st.selectbox("Turno", turnos)
    else:
        turno = "Todos"
        st.selectbox("Turno", ["No aplica"], disabled=True)

if turno != "Todos":
    base_df = base_df[base_df["turno"] == turno].copy()

with adv4:
    if nivel in ["Todos", "Grado Superior"]:
        bilingues = ["Todos"] + sorted([x for x in base_df["bilingue"].unique() if x])
        bilingue = st.selectbox("Bilingüe", bilingues)
    else:
        bilingue = "Todos"
        st.selectbox("Bilingüe", ["No aplica"], disabled=True)

if bilingue != "Todos":
    base_df = base_df[base_df["bilingue"] == bilingue].copy()

st.markdown("---")
st.subheader("Simulador de puntuación")

s1, s2, s3 = st.columns([1.1, 1, 1])

with s1:
    if nivel in ["Grado Medio", "Grado Superior"]:
        nivel_sim = nivel
        st.text_input("Nivel del simulador", value=nivel_sim, disabled=True)
    else:
        nivel_sim = st.selectbox("Nivel del simulador", ["Grado Medio", "Grado Superior"])

with s2:
    nota_media = st.number_input("Nota media", min_value=0.0, max_value=10.0, value=7.0, step=0.01)

with s3:
    madrid = st.toggle("Título obtenido en Madrid", value=True)

mencion = False
aprovechamiento = False
modalidad_bach = None

if nivel_sim == "Grado Superior":
    modalidad_bach = st.selectbox(
        "Modalidad de Bachillerato del alumno",
        [
            "Ciencias y Tecnología",
            "Humanidades y Ciencias Sociales",
            "Artes",
            "Otra / No lo sé",
        ],
    )

    familias_sugeridas = sugerencias_por_modalidad(modalidad_bach)
    if familias_sugeridas:
        pills = "".join([f'<span class="pill">{fam}</span>' for fam in familias_sugeridas])
        st.markdown(
            f"""
            <div class="suggestion-box">
                <div class="section-title" style="font-size:1rem; margin-bottom:0.45rem;">
                    Familias que suman +3
                </div>
                <div class="small-note" style="margin-bottom:0.45rem;">
                    En los ciclos de estas familias, la tabla usará la puntuación con <b>+3</b>.
                </div>
                <div>{pills}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    c1, c2 = st.columns(2)
    with c1:
        mencion = st.toggle("Mención Honorífica", value=False)
    with c2:
        aprovechamiento = st.toggle("Aprovechamiento", value=False)

puntuacion_constante, detalle = calcular_puntuacion_constante(
    nivel_sim=nivel_sim,
    nota_media=nota_media,
    madrid=madrid,
    mencion=mencion,
    aprovechamiento=aprovechamiento,
)

st.dataframe(
    pd.DataFrame(detalle, columns=["Criterio", "Puntos"]),
    use_container_width=True,
    hide_index=True
)

extra1, extra2 = st.columns([1, 1])
with extra1:
    nota_max = st.number_input("Nota de corte máxima", min_value=0.0, max_value=25.0, value=25.0, step=0.1)
with extra2:
    solo_alcanza = st.toggle("Ocultar los ciclos que no alcanza", value=False)

hay_filtro_activo = (
    nivel != "Todos"
    or familia != "Todas"
    or len(municipios_sel) > 0
    or tipo_centro != "Todos"
    or centro != "Todos"
    or modalidad != "Todas"
    or turno != "Todos"
    or bilingue != "Todos"
)

if not hay_filtro_activo:
    st.info("Aplica algún filtro para ver resultados.")
else:
    filtered = base_df.copy()

    if nivel == "Todos":
        filtered = filtered[filtered["nivel"] == nivel_sim].copy()
        nivel_tabla = nivel_sim
    else:
        nivel_tabla = nivel

    filtered = aplicar_comparacion_puntuacion(
        filtered,
        nivel_tabla=nivel_tabla,
        puntuacion_constante=puntuacion_constante,
        modalidad_bach=modalidad_bach
    )

    if nivel_tabla == "Grado Medio":
        filtered["orden_corte"] = filtered["via_a"].apply(to_float_safe)
        filtered = filtered[
            filtered["orden_corte"].isna() | (filtered["orden_corte"] <= nota_max)
        ].copy()

        if solo_alcanza:
            filtered = filtered[filtered["Estado"] == "✅ Te alcanza"].copy()

        filtered = filtered.sort_values(
            by=["Estado", "orden_corte", "ciclo", "centro"],
            ascending=[False, True, True, True],
            na_position="last"
        )

        display_cols = [
            "ciclo",
            "familia",
            "municipio",
            "tipo_centro",
            "centro",
            "puntuacion_total",
            "via_a",
            "Estado",
        ]
    else:
        filtered["a1_num"] = filtered["via_a1"].apply(to_float_safe)
        filtered["a2_num"] = filtered["via_a2"].apply(to_float_safe)
        filtered["orden_corte"] = pd.concat([filtered["a1_num"], filtered["a2_num"]], axis=1).min(axis=1)

        filtered = filtered[
            filtered["orden_corte"].isna() | (filtered["orden_corte"] <= nota_max)
        ].copy()

        if solo_alcanza:
            filtered = filtered[filtered["Estado"].isin(["✅ Te alcanza", "⚠️ Parcial"])].copy()

        filtered = filtered.sort_values(
            by=["es_relacionado", "Estado", "orden_corte", "ciclo", "centro"],
            ascending=[False, False, True, True, True],
            na_position="last"
        )

        if familia != "Todas":
            display_cols = [
                "ciclo",
                "puntuacion_total",
                "modalidad",
                "turno",
                "bilingue",
                "municipio",
                "tipo_centro",
                "centro",
                "es_relacionado",
                "bonus_modalidad",
                "via_a1",
                "via_a2",
                "Estado",
            ]
        else:
            display_cols = [
                "ciclo",
                "puntuacion_total",
                "familia",
                "modalidad",
                "turno",
                "bilingue",
                "municipio",
                "tipo_centro",
                "centro",
                "es_relacionado",
                "bonus_modalidad",
                "via_a1",
                "via_a2",
                "Estado",
            ]

    st.markdown("---")
    st.subheader("Resultados")

    r1, r2 = st.columns(2)
    r1.metric("Coincidencias", len(filtered))
    r2.metric(
        "Opciones favorables",
        int((filtered["Estado"].isin(["✅ Te alcanza", "⚠️ Parcial"])).sum())
    )

    if len(filtered) == 0:
        st.info("No se han encontrado resultados con esa combinación de filtros.")
    else:
        rename_map = {
            "ciclo": "Ciclo",
            "familia": "Familia profesional",
            "municipio": "Municipio",
            "tipo_centro": "Tipo de centro",
            "centro": "Centro",
            "modalidad": "Modalidad",
            "turno": "Turno",
            "bilingue": "Bilingüe",
            "es_relacionado": "Relacionado",
            "bonus_modalidad": "Bonus",
            "puntuacion_total": "Puntuación",
            "via_a": "Corte A",
            "via_a1": "Corte A1",
            "via_a2": "Corte A2",
            "Estado": "Resultado",
        }

        display_df = filtered[[c for c in display_cols if c in filtered.columns]].copy()

        if "es_relacionado" in display_df.columns:
            display_df["es_relacionado"] = display_df["es_relacionado"].map({True: "Sí", False: "No"})

        display_df = display_df.rename(columns=rename_map)
        build_aggrid(display_df)

        st.markdown("### Tu puntuación")

        if nivel_tabla == "Grado Medio":
            st.markdown(
                f"""
                <div class="total-box">
                    <b>Total que se está usando para decidir si te alcanza:</b> {round(float(puntuacion_constante), 2)} puntos
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            total_sin_relacion = round(float(puntuacion_constante), 2)
            total_con_relacion = round(float(puntuacion_constante) + 3, 2)

            c1, c2 = st.columns(2)
            c1.metric("Total en ciclos no relacionados", f"{total_sin_relacion} puntos")
            c2.metric("Total en ciclos relacionados", f"{total_con_relacion} puntos")

        csv = display_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Descargar resultados en CSV",
            data=csv,
            file_name="orientacion_fp_ies_maria_de_molina_resultados.csv",
            mime="text/csv"
        )

with st.expander("Ver resumen del baremo"):
    st.markdown(
        """
### Grado Medio – Vía A
Se tiene en cuenta:
- la **nota media real**
- **10 puntos** si el título de la **ESO** se ha obtenido en **Madrid**
- **Mención Honorífica**
- **Aprovechamiento**

### Grado Superior – Vía A
Se tiene en cuenta:
- la **nota media real**
- **10 puntos** si el título se ha obtenido en **Madrid**
- **3 puntos extra solo si el ciclo corresponde a la modalidad de Bachillerato elegida**

### Importante
La decisión de **te alcanza / no te alcanza** se hace con la **puntuación total que aparece en la tabla**.
"""
    )
