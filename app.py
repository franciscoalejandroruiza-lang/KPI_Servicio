import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_config(page_title="SenAudit Pro - Reportes Mensuales", layout="wide")

def main():
    st.title("📊 SenAudit Pro: Productividad por Mes")
    
    # --- BARRA LATERAL ---
    st.sidebar.header("📂 Carga de Datos")
    archivo = st.sidebar.file_uploader("Subir Reporte (XLSB o XLSX)", type=["xlsx", "xlsb"])

    if archivo:
        try:
            # 1. Carga y Preparación de Datos
            engine = 'openpyxl' if archivo.name.endswith('xlsx') else 'pyxlsb'
            df = pd.read_excel(archivo, engine=engine)
            df.columns = df.columns.str.strip()
            
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            
            # Crear columnas de Mes y Año para agrupar
            df['Mes_Num'] = df['Fecha_DT'].dt.month
            df['Año'] = df['Fecha_DT'].dt.year
            df['Mes_Nombre'] = df['Fecha_DT'].dt.month_name()

            # --- FILTROS DE INTERFAZ ---
            st.sidebar.header("📅 Filtros de Vista")
            lista_anios = sorted(df['Año'].unique().tolist(), reverse=True)
            anio_sel = st.sidebar.selectbox("Seleccionar Año:", lista_anios)
            
            # Solo folios RESUELTOS para esta pestaña
            df_resueltos = df[(df['Estatus'].str.contains('RESUELTA', case=False, na=False)) & (df['Año'] == anio_sel)]

            # --- PESTAÑAS ---
            tab_general, tab_auditoria = st.tabs(["📅 Reportes por Mes", "⚠️ Penalizaciones (Garantía)"])

            with tab_general:
                st.subheader(f"Resumen de Folios Resueltos - Año {anio_sel}")
                
                # Crear la Matriz: Filas (Técnicos) / Columnas (Meses)
                # Ordenamos los meses cronológicamente del 1 al 12
                matriz_mensual = df_resueltos.pivot_table(
                    index='Técnico', 
                    columns='Mes_Num', 
                    values='Folio', 
                    aggfunc='count', 
                    fill_value=0
                )
                
                # Renombrar columnas de números a nombres de meses
                nombres_meses = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 
                                 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
                matriz_mensual = matriz_mensual.rename(columns=nombres_meses)

                # Mostrar la tabla principal
                st.markdown("#### Histórico de Folios Resueltos por Técnico")
                st.dataframe(matriz_mensual.style.background_gradient(cmap='Blues'), use_container_width=True)

                # Gráfico Comparativo
                st.markdown("#### Comparativa Visual")
                st.line_chart(matriz_mensual.T)

            with tab_auditoria:
                st.subheader("Auditoría de Garantía de 3 Meses")
                st.info("Selecciona un mes en la barra lateral para ver a quién penalizó ese mes por fallas en el pasado.")
                # Aquí conectaremos la lógica de los 89 casos de Alejandro

        except Exception as e:
            st.error(f"Error en los datos: {e}")
    else:
        st.info("👈 Carga el archivo para ver el desglose por meses.")

if __name__ == "__main__":
    main()
