import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro - Auditoría Detallada", layout="wide")

def main():
    st.title("🛡️ Sistema de Auditoría y Control de Calidad")
    
    st.sidebar.header("Configuración de Auditoría")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:
        # 1. Procesamiento Inicial
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo, engine='openpyxl')
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        df = df.dropna(subset=['Fecha_DT', 'Folio', 'N.° de serie'])

        # 2. Configuración de Tiempos
        meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                      7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        col1, col2 = st.sidebar.columns(2)
        mes_eval = col1.selectbox("Mes a evaluar", options=range(1, 13), format_func=lambda x: meses_dict[x], index=datetime.now().month - 1)
        anio_eval = col2.number_input("Año", value=2026)
        meses_atras = st.sidebar.slider("Meses de historial (retroactivo)", 1, 12, 3)

        # 3. Cálculo de Rangos
        fecha_fin_eval = datetime(anio_eval, mes_eval, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio_historial = datetime(anio_eval, mes_eval, 1) - relativedelta(months=meses_atras)

        # 4. Lógica de Penalización por Antecedentes (Efecto Dominó)
        mask_rango = (df['Fecha_DT'] >= pd.Timestamp(fecha_inicio_historial)) & (df['Fecha_DT'] <= pd.Timestamp(fecha_fin_eval))
        df_analisis = df.loc[mask_rango].copy().sort_values(['N.° de serie', 'Fecha_DT'], ascending=True)

        df_analisis['Es_Penalizacion'] = 0
        for serie, grupo in df_analisis.groupby('N.° de serie'):
            if len(grupo) > 1:
                # El último folio queda libre, los anteriores correctivos se penalizan
                anteriores_indices = grupo.index[:-1]
                for idx in anteriores_indices:
                    if str(df_analisis.loc[idx, 'Categoría']).upper() == 'CORRECTIVO':
                        df_analisis.loc[idx, 'Es_Penalizacion'] = 1

        # Filtramos para el mes de reporte
        df_mes_actual = df_analisis[(df_analisis['Fecha_DT'].dt.month == mes_eval) & (df_analisis['Fecha_DT'].dt.year == anio_eval)]

        # --- INTERFAZ DE PESTAÑAS ---
        tab1, tab2, tab3 = st.tabs(["📊 Resumen", "⚠️ Penalizaciones", "🔍 Detalle de Auditoría"])

        with tab1:
            st.subheader("Productividad Mensual")
            resumen_prod = df_mes_actual.groupby('Técnico').size().reset_index(name='Folios Resueltos')
            st.dataframe(resumen_prod.sort_values('Folios Resueltos', ascending=False), use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("Conteo de Penalizaciones")
            # Sumamos todas las penalizaciones detectadas en el rango (mes + historial)
            resumen_penal = df_analisis[df_analisis['Es_Penalizacion'] == 1].groupby('Técnico').size().reset_index(name='penalizaciones')
            st.table(resumen_penal.sort_values('penalizaciones', ascending=False))

        with tab3:
            st.subheader("Revisión Individual de Fallas")
            st.write("Selecciona un técnico para ver qué folios específicos generaron penalización:")
            
            # Filtro por técnico
            lista_tecnicos = sorted(df_analisis[df_analisis['Es_Penalizacion'] == 1]['Técnico'].unique())
            tecnico_sel = st.selectbox("Elegir Técnico", options=["Todos"] + lista_tecnicos)

            # Filtrar DataFrame de penalizaciones
            df_detalles = df_analisis[df_analisis['Es_Penalizacion'] == 1][['Folio', 'N.° de serie', 'Técnico', 'Última visita', 'Categoría', 'Problema reportado']]
            
            if tecnico_sel != "Todos":
                df_detalles = df_detalles[df_detalles['Técnico'] == tecnico_sel]

            st.dataframe(df_detalles, use_container_width=True, hide_index=True)
            
            st.info("💡 Estos folios aparecen aquí porque después de ellos hubo otra intervención en la misma máquina dentro del historial.")

    else:
        st.info("Carga el reporte para habilitar el desglose individual por técnico.")

if __name__ == "__main__":
    main()
