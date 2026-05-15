from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st

from parser_pdf import extraer_expedientes
from database import (
    guardar_importacion,
    cargar_expedientes,
    cargar_cambios,
    cargar_importaciones,
    resetear_base,
)


st.set_page_config(
    page_title="Control de expedientes",
    page_icon="⚖️",
    layout="wide",
)

st.title("⚖️ Control de procedimientos del juzgado")
st.caption("Sube el PDF diario, actualiza expedientes y revisa los cambios detectados.")


def descargar_excel(df_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for nombre, df in df_dict.items():
            df.to_excel(writer, index=False, sheet_name=nombre[:31])
    return output.getvalue()


with st.sidebar:
    st.header("Importar PDF")
    pdf = st.file_uploader("PDF diario", type=["pdf"])

    if pdf is not None:
        if st.button("Procesar PDF", type="primary"):
            with st.spinner("Leyendo PDF y actualizando base de datos..."):
                registros = extraer_expedientes(pdf)
                cambios = guardar_importacion(registros, nombre_archivo=pdf.name)

            st.success(f"Expedientes leídos: {len(registros)}")
            st.info(f"Cambios/nuevos detectados: {len(cambios)}")

            if len(cambios):
                st.dataframe(cambios, use_container_width=True)

    st.divider()
    st.warning("Zona de mantenimiento")
    confirmar = st.checkbox("Confirmo que quiero borrar la base local")
    if confirmar and st.button("Borrar base de datos"):
        resetear_base()
        st.success("Base reiniciada.")


df = cargar_expedientes()
df_cambios = cargar_cambios()
df_importaciones = cargar_importaciones()

metricas = st.columns(4)
metricas[0].metric("Expedientes actuales", len(df))
metricas[1].metric("Cambios históricos", len(df_cambios))
metricas[2].metric("Importaciones", len(df_importaciones))
metricas[3].metric(
    "Última importación",
    df_importaciones["Fecha importación"].iloc[0] if len(df_importaciones) else "Sin datos",
)

tab_actuales, tab_cambios, tab_importaciones, tab_exportar = st.tabs(
    ["Expedientes actuales", "Cambios", "Importaciones", "Exportar"]
)

with tab_actuales:
    st.subheader("Expedientes actuales")

    if df.empty:
        st.info("Aún no hay expedientes. Sube un PDF desde la barra lateral.")
    else:
        col1, col2, col3 = st.columns(3)

        procedimientos = sorted([x for x in df["Procedimiento"].dropna().unique() if x])
        fases = sorted([x for x in df["Fase Procesal"].dropna().unique() if x])
        materias = sorted([x for x in df["Materia"].dropna().unique() if x])

        procedimiento = col1.multiselect("Procedimiento", procedimientos)
        fase = col2.multiselect("Fase procesal", fases)
        materia = col3.multiselect("Materia", materias)

        texto = st.text_input("Buscar por nº, trámite, materia o procedimiento")

        filtrado = df.copy()

        if procedimiento:
            filtrado = filtrado[filtrado["Procedimiento"].isin(procedimiento)]
        if fase:
            filtrado = filtrado[filtrado["Fase Procesal"].isin(fase)]
        if materia:
            filtrado = filtrado[filtrado["Materia"].isin(materia)]
        if texto:
            patron = texto.lower()
            mascara = filtrado.apply(
                lambda row: patron in " ".join(row.astype(str)).lower(),
                axis=1,
            )
            filtrado = filtrado[mascara]

        st.write(f"Mostrando {len(filtrado)} de {len(df)} expedientes.")
        st.dataframe(filtrado.drop(columns=["clave_expediente"]), use_container_width=True, height=600)

with tab_cambios:
    st.subheader("Histórico de cambios")

    if df_cambios.empty:
        st.info("Aún no hay cambios registrados.")
    else:
        texto_cambio = st.text_input("Buscar en cambios")
        filtrado_cambios = df_cambios.copy()

        if texto_cambio:
            patron = texto_cambio.lower()
            mascara = filtrado_cambios.apply(
                lambda row: patron in " ".join(row.astype(str)).lower(),
                axis=1,
            )
            filtrado_cambios = filtrado_cambios[mascara]

        st.dataframe(
            filtrado_cambios.drop(columns=["clave_expediente"]),
            use_container_width=True,
            height=600,
        )

with tab_importaciones:
    st.subheader("Importaciones realizadas")
    st.dataframe(df_importaciones, use_container_width=True, height=500)

with tab_exportar:
    st.subheader("Exportar datos")

    excel = descargar_excel(
        {
            "Expedientes actuales": df.drop(columns=["clave_expediente"], errors="ignore"),
            "Cambios": df_cambios.drop(columns=["clave_expediente"], errors="ignore"),
            "Importaciones": df_importaciones,
        }
    )

    nombre = f"expedientes_juzgado_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    st.download_button(
        "Descargar Excel",
        data=excel,
        file_name=nombre,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.info(
        "Recomendación: descarga periódicamente este Excel como copia de seguridad, "
        "especialmente si ejecutas la app en Streamlit Community Cloud."
    )
