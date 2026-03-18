import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro", layout="wide")

def main():
    st.title("🛡️ Sistema de Auditoría: Control de Penalizaciones")

    # =============================
    # SIDEBAR
    # =============================
    st.sidebar.header("⚙️ Configuración")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:

        df = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo)
        df.columns = df.columns.str.strip()

        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        df = df.dropna(subset=['Fecha_DT', 'Folio', 'N.° de equipo'])

        # DEBUG
        st.sidebar.write("📊 Registros:", len(df))
        st.sidebar.write("📅 Rango:", df['Fecha_DT'].min(), "→", df['Fecha_DT'].max())

        # =============================
        # SELECTOR MES/AÑO (COMO TE GUSTA)
        # =============================
        meses_dict = {
            1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
            7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"
        }

        col1, col2 = st.sidebar.columns(2)
        mes_eval = col1.selectbox("Mes", list(meses_dict.keys()), format_func=lambda x: meses_dict[x])
        anio_eval = col2.number_input("Año", value=2025)

        ventana = st.sidebar.slider("Ventana de penalización (meses)", 1, 12, 3)

        # =============================
        # FILTRO MES (CORRECTO)
        # =============================
        df_mes = df[
            (df['Fecha_DT'].dt.month == mes_eval) &
            (df['Fecha_DT'].dt.year == anio_eval)
        ]

        # DEBUG CLAVE
        st.write("📌 Registros en mes seleccionado:", len(df_mes))

        # =============================
        # RESUELTOS
        # =============================
        resueltos = df_mes[
            df_mes['Estatus'].str.upper().isin(["RESUELTO", "CERRADO", "FINALIZADO"])
        ]

        resumen_resueltos = resueltos.groupby('Técnico').size().reset_index(name='Resueltos')

        # =============================
        # PENALIZACIONES
        # =============================
        fecha_fin = datetime(anio_eval, mes_eval, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio = fecha_fin - relativedelta(months=ventana)

        df_rango = df[
            (df['Fecha_DT'] >= fecha_inicio) &
            (df['Fecha_DT'] <= fecha_fin)
        ]

        df_corr = df_rango[
            df_rango['Categoría'].str.upper().str.contains("CORRECT", na=False) &
            df_rango['Estatus'].str.upper().isin(["RESUELTO", "CERRADO", "FINALIZADO"])
        ].copy()

        df_corr = df_corr.sort_values(['N.° de equipo', 'Fecha_DT'])

        penalizaciones_idx = []

        for equipo, grupo in df_corr.groupby('N.° de equipo'):

            if len(grupo) > 1:
                grupo_ventana = grupo.copy()

                if len(grupo_ventana) > 1:
                    penalizados = grupo_ventana.iloc[:-1]
                    penalizaciones_idx.extend(penalizados.index.tolist())

        df['Es_Penalizacion'] = 0
        df.loc[penalizaciones_idx, 'Es_Penalizacion'] = 1

        df_penal_mes = df[
            (df['Es_Penalizacion'] == 1) &
            (df['Fecha_DT'].dt.month == mes_eval) &
            (df['Fecha_DT'].dt.year == anio_eval)
        ]

        resumen_penal = df_penal_mes.groupby('Técnico').size().reset_index(name='Penalizaciones')

        # =============================
        # FINAL
        # =============================
        resumen_final = pd.merge(resumen_resueltos, resumen_penal, on='Técnico', how='left')
        resumen_final['Penalizaciones'] = resumen_final['Penalizaciones'].fillna(0)
        resumen_final['Total'] = resumen_final['Resueltos'] - resumen_final['Penalizaciones']

        # KPIs
        col1, col2, col3 = st.columns(3)
        col1.metric("Resueltos", int(resumen_final['Resueltos'].sum()) if not resumen_final.empty else 0)
        col2.metric("Penalizaciones", int(resumen_final['Penalizaciones'].sum()) if not resumen_final.empty else 0)
        col3.metric("Total Neto", int(resumen_final['Total'].sum()) if not resumen_final.empty else 0)

        # TABS
        tab1, tab2, tab3 = st.tabs(["Resumen", "Penalizaciones", "Detalle"])

        with tab1:
            if resumen_final.empty:
                st.warning("⚠️ No hay datos en este mes")
            else:
                st.dataframe(resumen_final, use_container_width=True)

        with tab2:
            st.dataframe(resumen_penal, use_container_width=True)

        with tab3:
            st.dataframe(df_penal_mes, use_container_width=True)

    else:
        st.info("Sube tu archivo")

if __name__ == "__main__":
    main()
