import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro", layout="wide")

def main():
    st.title("🚀 Sistema de Auditoría SenIntegral")
    
    st.sidebar.header("Configuración de Datos")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:
        # 1. Procesamiento de datos
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo, engine='openpyxl')
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        df = df.dropna(subset=['Fecha_DT', 'Folio', 'N.° de serie'])

        # 2. Selectores de Periodo
        meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                      7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        col1, col2 = st.sidebar.columns(2)
        mes_eval = col1.selectbox("Mes a evaluar", options=range(1, 13), format_func=lambda x: meses_dict[x], index=datetime.now().month - 1)
        anio_eval = col2.number_input("Año", value=2026)
        
        # El usuario decide cuántos meses rastrear (de 1 a 12)
        meses_atras = st.sidebar.slider("Meses de historial para penalizaciones", 1, 12, 3)

        # 3. Lógica de Fechas
        fecha_fin = datetime(anio_eval, mes_eval, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio_historial = datetime(anio_eval, mes_eval, 1) - relativedelta(months=meses_atras)

        # 4. Cálculo de Penalizaciones (Basado en historial, sin regla de días)
        mask_historial = (df['Fecha_DT'] >= pd.Timestamp(fecha_inicio_historial)) & (df['Fecha_DT'] <= pd.Timestamp(fecha_fin))
        df_historial = df.loc[mask_historial].copy().drop_duplicates(subset=['Folio'])
        df_historial = df_historial.sort_values(['N.° de serie', 'Fecha_DT'], ascending=[True, False])

        df_historial['Es_Penalizable'] = 0
        for serie, grupo in df_historial.groupby('N.° de serie'):
            if len(grupo) > 1:
                indices = grupo.index
                for i in range(len(indices) - 1):
                    # Si el reporte anterior en el historial fue CORRECTIVO, el técnico anterior recibe penalización
                    if str(df_historial.loc[indices[i+1], 'Categoría']).upper() == 'CORRECTIVO':
                        df_historial.loc[indices[i+1], 'Es_Penalizable'] = 1

        # 5. Filtrar datos solo del mes seleccionado para los reportes
        mask_mes_actual = (df_historial['Fecha_DT'].dt.month == mes_eval) & (df_historial['Fecha_DT'].dt.year == anio_eval)
        df_mes = df_historial.loc[mask_mes_actual]

        # --- INTERFAZ DE PESTAÑAS ---
        tab1, tab2 = st.tabs(["📊 Resumen de Productividad", "⚠️ Auditoría de Penalizaciones"])

        with tab1:
            st.subheader(f"Reportes Resueltos en {meses_dict[mes_eval]}")
            resumen_prod = df_mes.groupby('Técnico').agg(
                reportes_resueltos=('Folio', 'count')
            ).reset_index().sort_values('reportes_resueltos', ascending=False)
            
            st.dataframe(resumen_prod, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader(f"Contabilización de Penalizaciones ({meses_atras} meses de historial)")
            resumen_penal = df_mes.groupby('Técnico').agg(
                penalizaciones=('Es_Penalizable', 'sum')
            ).reset_index().sort_values('penalizaciones', ascending=False)
            
            # Formato idéntico al solicitado
            st.table(resumen_penal)

    else:
        st.info("Por favor, carga el archivo de servicios para comenzar el análisis.")

if __name__ == "__main__":
    main()
