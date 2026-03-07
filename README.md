# FP Match Madrid

Aplicación en **Streamlit** para buscar ciclos de **Formación Profesional en Madrid** y consultar la **nota de corte oficial del curso 2025-2026**.

## Qué hace

- Busca por palabra clave: `informática`, `marketing`, `sanidad`, `imagen`, etc.
- Filtra por:
  - nivel
  - municipio
  - familia profesional
  - tipo de centro
  - modalidad
  - turno
- Muestra una **tabla global** con:
  - ciclo
  - familia profesional
  - centro
  - municipio
  - modalidad
  - turno
  - **nota de corte vía A**
  - **nota de corte vía A1/A2** en grado superior
- Incluye un bloque explicativo de **cómo se consiguen los puntos**.

## Estructura

```text
fp-match-madrid/
├── app.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml
├── data/
│   ├── raw/
│   │   ├── baremo_25-26_gm_vf.pdf
│   │   ├── baremo_25-26_gs_vf.pdf
│   │   ├── ANEXO-II-Baremo-Grado-Medio.pdf
│   │   └── Anexo-II-A-BAremo-según-vías-de-acceso.pdf
│   └── processed/
│       ├── fp_match_madrid_2025_2026.csv
│       ├── grado_medio_2025_2026.csv
│       └── grado_superior_2025_2026.csv
└── src/
    ├── load_data.py
    ├── process_pdf.py
    └── search.py
```

## Ejecutarlo en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Subirlo a GitHub

1. Crea un repositorio nuevo con el nombre `fp-match-madrid`
2. Sube todo el contenido de esta carpeta
3. Haz commit y push

## Publicarlo en Streamlit Community Cloud

1. Entra en Streamlit Community Cloud
2. Conecta tu cuenta de GitHub
3. Selecciona el repo `fp-match-madrid`
4. Indica `app.py` como archivo principal
5. Pulsa en deploy

## Regenerar el CSV desde los PDFs

Ya te dejo el CSV generado, así que no hace falta hacerlo para desplegar.

Si quieres regenerarlo:

```bash
python src/process_pdf.py
```

## Notas

- La app usa los **baremos de corte 2025-2026**.
- En **Grado Medio** se muestra la columna **Corte vía A**.
- En **Grado Superior** se muestran **Corte vía A1** y **Corte vía A2**.
- La explicación de puntuación se ha resumido a partir de los anexos de baremación incluidos en `data/raw/`.
