import streamlit as st
import pandas as pd
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.load_data import load_dataset
from src.search import search_cyclesfrom pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from src.load_data import load_dataset
from src.search import apply_filters, format_for_display

st.set_page_config(
    page_title="FP Match Madrid",
    page_icon="🎓",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; padding-bottom: 2rem;}
      .app-title {font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem;}
      .subtle {color: #5b6470;}
      .metric-card {
          background: white; border: 1px solid #e7ebf0; border-radius: 14px;
          padding: 0.9rem 1rem; box-shadow: 0 1px 2px rgba(0,0,0,.03);
      }
      .small-note {font-size: 0.92rem; color: #5b6470;}
      div[data-testid="stDataFrame"] div[role="table"] {font-size: 0.95rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

df = load_dataset()

st.markdown('<div class="app-title">FP Match Madrid</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtle">Busca ciclos de FP en Madrid y consulta la nota de corte oficial del curso 2025-2026.</div>',
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns([2.2, 1, 1])
with col1:
    query = st.text_input(
        "Palabra clave",
        placeholder="Ej.: informática, marketing, sanidad, deportes, imagen...",
        help="Busca por nombre del ciclo, familia profesional, centro o municipio.",
    )
with col2:
    nivel = st.selectbox("Nivel", ["Todos", "Grado Medio", "Grado Superior"])
with col3:
    ordenar = st.selectbox(
        "Ordenar por",
        ["Ciclo (A-Z)", "Municipio (A-Z)", "Corte vía A ↑", "Corte vía A ↓"],
    )

with st.sidebar:
    st.header("Filtros")
    municipios = ["Todos"] + sorted(x for x in df["municipio"].dropna().unique() if x)
    familias = ["Todas"] + sorted(x for x in df["familia"].dropna().unique() if x)
    tipos = ["Todos"] + sorted(x for x in df["tipo_centro"].dropna().unique() if x)
    modalidades = ["Todas"] + sorted(x for x in df["modalidad"].dropna().unique() if x)
    turnos = ["Todos"] + sorted(x for x in df["turno"].dropna().unique() if x)

    municipio = st.selectbox("Municipio", municipios)
    familia = st.selectbox("Familia profesional", familias)
    tipo_centro = st.selectbox("Tipo de centro", tipos)
    modalidad = st.selectbox("Modalidad", modalidades)
    turno = st.selectbox("Turno", turnos)
    solo_con_nota = st.checkbox("Ocultar filas sin nota de corte", value=False)

filtered = apply_filters(
    df=df,
    query=query,
    nivel=nivel,
    municipio=municipio,
    familia=familia,
    tipo_centro=tipo_centro,
    modalidad=modalidad,
    turno=turno,
    solo_con_nota=solo_con_nota,
)

if ordenar == "Ciclo (A-Z)":
    filtered = filtered.sort_values(["ciclo", "municipio", "centro"], na_position="last")
elif ordenar == "Municipio (A-Z)":
    filtered = filtered.sort_values(["municipio", "ciclo", "centro"], na_position="last")
elif ordenar == "Corte vía A ↑":
    filtered = filtered.sort_values(["nota_referencia", "ciclo"], na_position="last")
else:
    filtered = filtered.sort_values(["nota_referencia", "ciclo"], ascending=[False, True], na_position="last")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="metric-card"><strong>{len(filtered):,}</strong><br><span class="small-note">Resultados</span></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><strong>{filtered["ciclo"].nunique():,}</strong><br><span class="small-note">Ciclos distintos</span></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card"><strong>{filtered["municipio"].nunique():,}</strong><br><span class="small-note">Municipios</span></div>', unsafe_allow_html=True)

st.markdown("### Resultados")
st.dataframe(
    format_for_display(filtered),
    use_container_width=True,
    hide_index=True,
)

csv = format_for_display(filtered).to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Descargar resultados en CSV",
    data=csv,
    file_name="fp_match_madrid_resultados.csv",
    mime="text/csv",
)

with st.expander("Cómo se consiguen los puntos"):
    st.markdown(
        """
        #### Grado Medio · Vía A
        La puntuación combina, sobre todo, la **nota media del expediente académico** y otros méritos.

        **Nota media**
        - Igual o superior a 9 → **12 puntos**
        - Igual o superior a 8 y menor que 9 → **11 puntos**
        - Igual o superior a 7 y menor que 8 → **10 puntos**
        - Igual o superior a 6 y menor que 7 → **8 puntos**
        - Igual o superior a 5 y menor que 6 → **6 puntos**

        **Otros criterios**
        - Diploma de Mención Honorífica → **3 puntos**
        - Diploma de Aprovechamiento → **2 puntos**
        - Título obtenido en centros de la Comunidad de Madrid → **12 puntos**
        - Título obtenido fuera de la Comunidad de Madrid → **2 puntos**

        #### Grado Superior · Vía A
        En los listados oficiales de corte aparecen **Vía A1** y **Vía A2**.
        - **A1**: bachillerato relacionado con el ciclo
        - **A2**: bachillerato no relacionado

        **Nota media del expediente**
        - Igual o superior a 9 → **12 puntos**
        - Igual o superior a 8 y menor que 9 → **11 puntos**
        - Igual o superior a 7 y menor que 8 → **10 puntos**
        - Igual o superior a 6 y menor que 7 → **8 puntos**
        - Igual o superior a 5 y menor que 6 → **6 puntos**

        **Otros criterios**
        - Modalidad de bachiller relacionada con el ciclo → **5 puntos**
        - Título obtenido en centros de la Comunidad de Madrid → **12 puntos**
        - Título obtenido fuera de la Comunidad de Madrid → **2 puntos**
        - Título obtenido entre 2008 y la fecha de solicitud → **6 puntos**
        - Título obtenido en 2007 → **4 puntos**
        - Título obtenido en 2006 → **3 puntos**
        - Título obtenido en 2005 → **2 puntos**
        - Título obtenido antes de 2005 → **1 punto**

        La tabla principal muestra la **nota de corte oficial** del curso 2025-2026 extraída de los listados de la Comunidad de Madrid.
        """
    )

st.caption("Proyecto listo para subir a GitHub y desplegar en Streamlit.")
