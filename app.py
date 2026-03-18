import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro - Auditoría de Calidad", layout="wide")

def main():
    st.title("🛡️ Sistema de Auditoría: Control de Penalizaciones")

    # =============================
    # SIDEBAR
    # =============================
    st.sidebar.header("⚙️ Configuración")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:

        # =============================
        # CARGA DE DATOS
        # =============================
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo, engine='openpyxl')
        df.columns = df.columns.str.strip()

        # Convertir fechas
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')

        # Limpiar datos importantes
        df = df.dropna(subset=['Fecha_DT', 'Folio', 'N.° de equipo'])

        # =============================
        # CONFIGURACIÓN DE FECHAS
        # =============================
        meses_dict = {
            1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril",
            5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto",
            9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"
        }

        col1, col2 = st.sidebar.columns(2)
        mes_eval = col1.selectbox("Mes a evaluar", options=range(1, 13),
                                 format_func=lambda x: meses_dict[x])
        anio_eval = col2.number_input("Año", value=datetime.now().year)

        meses_atras = st.sidebar.slider("Ventana de penalización (meses)", 1, 12, 3)

        fecha_inicio_mes = datetime(anio_eval, mes_eval, 1)
        fecha_fin_mes = fecha_inicio_mes + relativedelta(months=1) - relativedelta(days=1)

        fecha_inicio_historial = fecha_inicio_mes - relativedelta(months=meses_atras)

        # =============================
        # FILTRO BASE
        # =============================
        df_rango = df[
            (df['Fecha_DT'] >= fecha_inicio_historial) &
            (df['Fecha_DT'] <= fecha_fin_mes)
        ].copy()

        # =============================
        # RESUELTOS DEL MES
        # =============================
        df_mes = df[
            (df['Fecha_DT'] >= fecha_inicio_mes) &
            (df['Fecha_DT'] <= fecha_fin_mes)
        ].copy()

        resueltos = df_mes[
            df_mes['Estatus'].str.upper().str.contains("RESUELTO", na=False)
        ]

        resumen_resueltos = resueltos.groupby('Técnico').size().reset_index(name='Resueltos')

        # =============================
        # PENALIZACIONES (LÓGICA CORRECTA)
        # =============================
        df_corr = df_rango[
            df_rango['Categoría'].str.upper().str.contains("CORRECT", na=False) &
            df_rango['Estatus'].str.upper().str.contains("RESUELTO", na=False)
        ].copy()

        df_corr = df_corr.sort_values(['N.° de equipo', 'Fecha_DT'])

        penalizaciones_idx = []

        for equipo, grupo in df_corr.groupby('N.° de equipo'):

            if len(grupo) > 1:

                fecha_max = grupo['Fecha_DT'].max()
                fecha_min = fecha_max - relativedelta(months=meses_atras)

                grupo_ventana = grupo[grupo['Fecha_DT'] >= fecha_min]

                if len(grupo_ventana) > 1:
                    # excluir el más reciente
                    penalizados = grupo_ventana.iloc[:-1]
                    penalizaciones_idx.extend(penalizados.index.tolist())

        # Marcar penalizaciones en df original
        df['Es_Penalizacion'] = 0
        df.loc[penalizaciones_idx, 'Es_Penalizacion'] = 1

        # Penalizaciones del mes
        df_penal_mes = df[
            (df['Es_Penalizacion'] == 1) &
            (df['Fecha_DT'] >= fecha_inicio_mes) &
            (df['Fecha_DT'] <= fecha_fin_mes)
        ]

        resumen_penal = df_penal_mes.groupby('Técnico').size().reset_index(name='Penalizaciones')

        # =============================
        # UNIÓN FINAL
        # =============================
        resumen_final = pd.merge(resumen_resueltos, resumen_penal, on='Técnico', how='left')
        resumen_final['Penalizaciones'] = resumen_final['Penalizaciones'].fillna(0)

        resumen_final['Total'] = resumen_final['Resueltos'] - resumen_final['Penalizaciones']

        # =============================
        # KPIs
        # =============================
        col1, col2, col3 = st.columns(3)
        col1.metric("📄 Resueltos", int(resumen_final['Resueltos'].sum()))
        col2.metric("⚠️ Penalizaciones", int(resumen_final['Penalizaciones'].sum()))
        col3.metric("✅ Total Neto", int(resumen_final['Total'].sum()))

        # =============================
        # TABS
        # =============================
        tab1, tab2, tab3 = st.tabs([
            "📊 Resumen por Técnico",
            "⚠️ Penalizaciones",
            "🔍 Detalle"
        ])

        # =============================
        # TAB 1
        # =============================
        with tab1:
            st.subheader("Resumen Final")
            st.dataframe(resumen_final.sort_values("Total", ascending=False),
                         use_container_width=True, hide_index=True)

        # =============================
        # TAB 2
        # =============================
        with tab2:
            st.subheader("Penalizaciones por Técnico")
            st.dataframe(resumen_penal.sort_values("Penalizaciones", ascending=False),
                         use_container_width=True, hide_index=True)

        # =============================
        # TAB 3
        # =============================
        with tab3:
            st.subheader("Detalle de Penalizaciones")

            tecnicos = ["Todos"] + sorted(df_penal_mes['Técnico'].dropna().unique().tolist())
            tecnico_sel = st.selectbox("Filtrar por Técnico", tecnicos)

            df_detalle = df_penal_mes[
                ['Folio', 'N.° de equipo', 'Técnico', 'Última visita', 'Categoría']
            ]

            if tecnico_sel != "Todos":
                df_detalle = df_detalle[df_detalle['Técnico'] == tecnico_sel]

            st.dataframe(df_detalle, use_container_width=True, hide_index=True)

            st.download_button(
                label="📥 Descargar CSV",
                data=df_detalle.to_csv(index=False),
                file_name="penalizaciones.csv",
                mime="text/csv"
            )

    else:
        st.info("👋 Sube tu archivo para comenzar")

if __name__ == "__main__":
    main()
