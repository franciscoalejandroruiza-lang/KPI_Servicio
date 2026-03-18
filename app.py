import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro - Auditoría de Calidad", layout="wide")

def main():
    st.title("🛡️ Sistema de Auditoría: Control de Penalizaciones")
    
    st.sidebar.header("Configuración de Auditoría")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:
        # 1. Carga y limpieza de datos
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo, engine='openpyxl')
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        df = df.dropna(subset=['Fecha_DT', 'Folio', 'N.° de serie'])

        # 2. Configuración de Periodos
        meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                      7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        col1, col2 = st.sidebar.columns(2)
        mes_eval = col1.selectbox("Mes a evaluar", options=range(1, 13), format_func=lambda x: meses_dict[x], index=1) # Default Febrero
        anio_eval = col2.number_input("Año", value=2026)
        meses_atras = st.sidebar.slider("Meses de historial (retroactivo)", 1, 12, 3)

        # 3. Definición de Rangos de Fecha
        fecha_fin_eval = datetime(anio_eval, mes_eval, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio_historial = datetime(anio_eval, mes_eval, 1) - relativedelta(months=meses_atras)

        # 4. LÓGICA DE PENALIZACIÓN (CORREGIDA)
        # Filtramos el rango total para el análisis de reincidencias
        mask_rango = (df['Fecha_DT'] >= pd.Timestamp(fecha_inicio_historial)) & (df['Fecha_DT'] <= pd.Timestamp(fecha_fin_eval))
        df_analisis = df.loc[mask_rango].copy().sort_values(['N.° de serie', 'Fecha_DT'], ascending=True)

        df_analisis['Es_Penalizacion'] = 0

        # Procesamos cada serie individualmente
        for serie, grupo in df_analisis.groupby('N.° de serie'):
            if len(grupo) > 1:
                # Obtenemos los índices ordenados por fecha
                indices = grupo.index.tolist()
                
                # REGLA MAESTRA: El último folio (el más reciente) NO se penaliza.
                # Solo evaluamos desde el primero hasta el penúltimo [indices[:-1]]
                for idx in indices[:-1]:
                    # Si el reporte anterior es CORRECTIVO, se marca como penalización
                    if str(df_analisis.loc[idx, 'Categoría']).upper() == 'CORRECTIVO':
                        df_analisis.loc[idx, 'Es_Penalizacion'] = 1

        # Filtramos para obtener solo lo que corresponde al mes de reporte seleccionado
        df_mes_actual = df_analisis[(df_analisis['Fecha_DT'].dt.month == mes_eval) & (df_analisis['Fecha_DT'].dt.year == anio_eval)]

        # --- INTERFAZ DE USUARIO (PESTAÑAS) ---
        tab1, tab2, tab3 = st.tabs(["📊 Resumen", "⚠️ Penalizaciones", "🔍 Detalle de Auditoría"])

        with tab1:
            st.subheader(f"Reportes Resueltos en {meses_dict[mes_eval]}")
            resumen_prod = df_mes_actual.groupby('Técnico').size().reset_index(name='Folios Totales')
            st.dataframe(resumen_prod.sort_values('Folios Totales', ascending=False), use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("Conteo Final de Penalizaciones")
            # Mostramos penalizaciones detectadas en el mes evaluado
            resumen_penal = df_mes_actual.groupby('Técnico')['Es_Penalizacion'].sum().reset_index(name='penalizaciones')
            # Incluimos también a los técnicos que penalizaron en el historial si es necesario, 
            # o solo los del mes actual según tu preferencia. Aquí sumamos las del mes actual:
            resumen_penal = resumen_penal[resumen_penal['penalizaciones'] > 0].sort_values('penalizaciones', ascending=False)
            st.table(resumen_penal)

        with tab3:
            st.subheader("Evidencia de Fallas por Técnico")
            # Lista de técnicos con penalizaciones en todo el periodo analizado
            lista_tecnicos = sorted(df_analisis[df_analisis['Es_Penalizacion'] == 1]['Técnico'].unique())
            tecnico_sel = st.selectbox("Seleccionar Técnico para revisar", options=["Todos"] + lista_tecnicos)

            df_detalles = df_analisis[df_analisis['Es_Penalizacion'] == 1][['Folio', 'N.° de serie', 'Técnico', 'Última visita', 'Categoría', 'Problema reportado']]
            
            if tecnico_sel != "Todos":
                df_detalles = df_detalles[df_detalles['Técnico'] == tecnico_sel]

            st.dataframe(df_detalles, use_container_width=True, hide_index=True)
            st.download_button(label="Descargar Detalle (CSV)", data=df_detalles.to_csv(index=False), file_name=f"detalle_penalizaciones_{tecnico_sel}.csv", mime="text/csv")

    else:
        st.info("👋 Por favor, carga el archivo Excel para iniciar la auditoría de Chihuahua.")

if __name__ == "__main__":
    main()
