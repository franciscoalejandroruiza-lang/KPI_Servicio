import streamlit as st
import pandas as pd
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
        # CARGA
        # =============================
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
        df.columns = df.columns.str.strip()

        # Fecha
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')

        # Limpiar
        df = df.dropna(subset=['Fecha_DT', 'Folio', 'N.° de equipo'])

        # DEBUG (puedes quitar luego)
        st.sidebar.write("📊 Registros:", len(df))
        st.sidebar.write("📅 Rango:", df['Fecha_DT'].min(), "→", df['Fecha_DT'].max())

        # =============================
        # SELECTOR DE MES (DINÁMICO)
        # =============================
        meses_disponibles = df['Fecha_DT'].dt.to_period("M").astype(str).unique()
        mes_sel = st.sidebar.selectbox("Selecciona el mes", sorted(meses_disponibles))

        ventana = st.sidebar.slider("Ventana de penalización (meses)", 1, 12, 3)

        # =============================
        # FILTRO MES
        # =============================
        df_mes = df[df['Fecha_DT'].dt.to_period("M").astype(str) == mes_sel]

        # =============================
        # RESUELTOS
        # =============================
        resueltos = df_mes[
            df_mes['Estatus'].str.upper().isin(["RESUELTO", "CERRADO", "FINALIZADO"])
        ]

        resumen_resueltos = resueltos.groupby('Técnico').size().reset_index(name='Resueltos')

        # =============================
        # PENALIZACIONES (CORRECTO)
        # =============================
        df_corr = df[
            df['Categoría'].str.upper().str.contains("CORRECT", na=False) &
            df['Estatus'].str.upper().isin(["RESUELTO", "CERRADO", "FINALIZADO"])
        ].copy()

        df_corr = df_corr.sort_values(['N.° de equipo', 'Fecha_DT'])

        penalizaciones_idx = []

        for equipo, grupo in df_corr.groupby('N.° de equipo'):

            if len(grupo) > 1:

                fecha_max = grupo['Fecha_DT'].max()
                fecha_min = fecha_max - relativedelta(months=ventana)

                grupo_ventana = grupo[grupo['Fecha_DT'] >= fecha_min]

                if len(grupo_ventana) > 1:
                    penalizados = grupo_ventana.iloc[:-1]  # excluir último
                    penalizaciones_idx.extend(penalizados.index.tolist())

        df['Es_Penalizacion'] = 0
        df.loc[penalizaciones_idx, 'Es_Penalizacion'] = 1

        # Penalizaciones del mes seleccionado
        df_penal_mes = df[
            (df['Es_Penalizacion'] == 1) &
            (df['Fecha_DT'].dt.to_period("M").astype(str) == mes_sel)
        ]

        resumen_penal = df_penal_mes.groupby('Técnico').size().reset_index(name='Penalizaciones')

        # =============================
        # UNION FINAL
        # =============================
        resumen_final = pd.merge(resumen_resueltos, resumen_penal, on='Técnico', how='left')
        resumen_final['Penalizaciones'] = resumen_final['Penalizaciones'].fillna(0)
        resumen_final['Total'] = resumen_final['Resueltos'] - resumen_final['Penalizaciones']

        # =============================
        # KPIs
        # =============================
        col1, col2, col3 = st.columns(3)
        col1.metric("📄 Resueltos", int(resumen_final['Resueltos'].sum()) if not resumen_final.empty else 0)
        col2.metric("⚠️ Penalizaciones", int(resumen_final['Penalizaciones'].sum()) if not resumen_final.empty else 0)
        col3.metric("✅ Total Neto", int(resumen_final['Total'].sum()) if not resumen_final.empty else 0)

        # =============================
        # TABS
        # =============================
        tab1, tab2, tab3 = st.tabs([
            "📊 Resumen",
            "⚠️ Penalizaciones",
            "🔍 Detalle"
        ])

        # TAB 1
        with tab1:
            st.subheader("Resumen por Técnico")

            if resumen_final.empty:
                st.warning("⚠️ No hay datos en este mes")
            else:
                st.dataframe(resumen_final.sort_values("Total", ascending=False),
                             use_container_width=True, hide_index=True)

        # TAB 2
        with tab2:
            st.subheader("Penalizaciones por Técnico")

            if resumen_penal.empty:
                st.info("No hay penalizaciones en este mes")
            else:
                st.dataframe(resumen_penal.sort_values("Penalizaciones", ascending=False),
                             use_container_width=True, hide_index=True)

        # TAB 3
        with tab3:
            st.subheader("Detalle de Penalizaciones")

            if df_penal_mes.empty:
                st.info("No hay registros")
            else:
                tecnicos = ["Todos"] + sorted(df_penal_mes['Técnico'].dropna().unique().tolist())
                tecnico_sel = st.selectbox("Filtrar técnico", tecnicos)

                df_detalle = df_penal_mes[
                    ['Folio', 'N.° de equipo', 'Técnico', 'Última visita', 'Categoría']
                ]

                if tecnico_sel != "Todos":
                    df_detalle = df_detalle[df_detalle['Técnico'] == tecnico_sel]

                st.dataframe(df_detalle, use_container_width=True, hide_index=True)

                st.download_button(
                    "📥 Descargar CSV",
                    df_detalle.to_csv(index=False),
                    "penalizaciones.csv",
                    "text/csv"
                )

    else:
        st.info("👋 Sube tu archivo para comenzar")

if __name__ == "__main__":
    main()
