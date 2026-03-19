import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN CORRECTA DE LA PÁGINA ---
st.set_page_config(page_title="SenAudit Pro - Reportes Mensuales", layout="wide")

def main():
    st.title("📊 SenAudit Pro: Productividad Mensual")
    
    # --- BARRA LATERAL ---
    st.sidebar.header("📂 Carga de Datos")
    archivo = st.sidebar.file_uploader("Subir Reporte (XLSB o XLSX)", type=["xlsx", "xlsb"])

    if archivo:
        try:
            # 1. Carga y Preparación
            engine = 'openpyxl' if archivo.name.endswith('xlsx') else 'pyxlsb'
            df = pd.read_excel(archivo, engine=engine)
            df.columns = df.columns.str.strip()
            
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            
            # Extraer Mes y Año
            df['Mes_Num'] = df['Fecha_DT'].dt.month
            df['Año'] = df['Fecha_DT'].dt.year

            # --- FILTROS ---
            st.sidebar.header("📅 Filtros de Vista")
            lista_anios = sorted(df['Año'].dropna().unique().astype(int).tolist(), reverse=True)
            anio_sel = st.sidebar.selectbox("Seleccionar Año:", lista_anios)
            
            # Solo folios RESUELTOS del año seleccionado
            df_resueltos = df[(df['Estatus'].str.contains('RESUELTA', case=False, na=False)) & (df['Año'] == anio_sel)]

            # --- PESTAÑAS ---
            tab_general, tab_auditoria = st.tabs(["📅 Reportes por Mes", "⚠️ Penalizaciones (Garantía)"])

            with tab_general:
                st.subheader(f"Folios Resueltos por Técnico - {anio_sel}")
                
                # Crear la Matriz: Filas (Técnicos) / Columnas (Meses del 1 al 12)
                matriz = df_resueltos.pivot_table(
                    index='Técnico', 
                    columns='Mes_Num', 
                    values='Folio', 
                    aggfunc='count', 
                    fill_value=0
                )
                
                # Asegurar que aparezcan todos los meses y en orden
                nombres_meses = {
                    1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 
                    7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'
                }
                
                # Reordenar y renombrar columnas
                columnas_existentes = [m for m in range(1, 13) if m in matriz.columns]
                matriz = matriz[columnas_existentes].rename(columns=nombres_meses)

                # Visualización con Estilo (Mapa de calor para ver quién trabajó más)
                st.markdown("#### Histórico Mensual (Vistos/Resueltos)")
                st.dataframe(
                    matriz.style.background_gradient(cmap='Blues', axis=None).format("{:,.0f}"), 
                    use_container_width=True
                )

                # Gráfico de tendencia mensual acumulada
                st.markdown("#### Tendencia de Carga de Trabajo")
                st.line_chart(matriz.T)

            with tab_auditoria:
                st.subheader("Auditoría de Garantía de 3 Meses")
                st.info("Esta sección analizará qué técnicos de meses pasados fallaron según los reportes actuales.")
                # Aquí integraremos la lógica de penalización que desees

        except Exception as e:
            st.error(f"Hubo un problema al leer los datos: {e}")
    else:
        st.info("👈 Por favor, carga el archivo Excel en la barra lateral.")

if __name__ == "__main__":
    main()
