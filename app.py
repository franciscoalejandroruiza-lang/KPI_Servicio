import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Auditoría Directa", layout="wide")

def main():
    st.title("🛡️ Auditoría SenAudit Pro: Control de Garantías")
    st.markdown("Criterio: Penalizar folios con reincidencia reportada dentro del periodo de garantía.")

    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio (.xlsx)", type=["xlsx"])

    if archivo:
        try:
            # 1. Carga de datos
            df = pd.read_excel(archivo, engine='openpyxl')
            df.columns = df.columns.str.strip()
            
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Limpieza de fechas y textos
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            
            # 2. Configuración
            st.sidebar.header("Parámetros")
            dias_garantia = st.sidebar.slider("Días de garantía", 1, 365, 30)
            
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = st.sidebar.selectbox("Mes a evaluar", meses_nombres, index=datetime.now().month - 1)
            mes_num = meses_nombres.index(mes_sel) + 1
            anio_eval = st.sidebar.number_input("Año", value=2026)

            # 3. Lógica de Marcado de Penalizaciones
            # Filtramos solo lo que puede ser penalizado: Correctivos Resueltos
            # Nota: No filtramos el DF completo para no perder el historial de reincidencia
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)
            df['Es_Penalizacion'] = 0
            df['Dias_hasta_reincidencia'] = 0
            df['Folio_Reincidente'] = ""

            # Agrupamos por serie para comparar cronológicamente
            for serie, grupo in df.groupby(col_serie):
                if len(grupo) > 1:
                    for i in range(len(grupo) - 1):
                        idx_actual = grupo.index[i]
                        idx_siguiente = grupo.index[i+1]
                        
                        # Condiciones para penalizar el folio 'actual':
                        # 1. Debe ser CORRECTIVO y RESUELTA
                        # 2. El siguiente reporte debe estar dentro de los días de garantía
                        es_correctivo = "CORRECTIVO" in str(df.loc[idx_actual, 'Categoría']).upper()
                        es_resuelta = "RESUELTA" in str(df.loc[idx_actual, 'Estatus']).upper()
                        
                        dif = (df.loc[idx_siguiente, 'Fecha_DT'] - df.loc[idx_actual, 'Fecha_DT']).days
                        
                        if es_correctivo and es_resuelta and (0 <= dif <= dias_garantia):
                            df.at[idx_actual, 'Es_Penalizacion'] = 1
                            df.at[idx_actual, 'Dias_hasta_reincidencia'] = dif
                            df.at[idx_actual, 'Folio_Reincidente'] = df.loc[idx_siguiente, 'Folio']

            # 4. Filtrado del Mes de Reporte
            df_mes = df[(df['Fecha_DT'].dt.month == mes_num) & (df['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- RESULTADOS ---
            c1, c2 = st.columns(2)
            with c1:
                st.subheader(f"KPI Técnicos: {mes_sel}")
                resumen = df_mes.groupby('Técnico').agg(
                    Total_Folios=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with c2:
                st.subheader("Buscador de Evidencia")
                tec_input = st.text_input("Filtrar por Técnico:", "ALEJANDRO RUIZ").upper()
                if tec_input:
                    total_tec = df_mes[df_mes['Técnico'].str.contains(tec_input, na=False)]['Es_Penalizacion'].sum()
                    st.metric(f"Penalizaciones detectadas para {tec_input}", total_tec)

            st.divider()
            st.subheader("📋 Detalle de Folios Penalizados")
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            if not evidencia.empty:
                st.dataframe(evidencia[[col_serie, 'Folio', 'Técnico', 'Fecha_DT', 'Dias_hasta_reincidencia', 'Folio_Reincidente']], use_container_width=True)
            else:
                st.info("No se encontraron penalizaciones con los días de garantía seleccionados.")

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("Carga el archivo Excel para procesar los datos.")

if __name__ == "__main__":
    main()
