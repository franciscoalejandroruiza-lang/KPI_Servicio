import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración básica
st.set_page_config(page_title="SenAudit - Paso 1", layout="wide")

def main():
    st.title("📊 Paso 1: Conteo de Reportes Resueltos")
    
    # 1. Cargar Archivo
    st.sidebar.header("Configuración")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:
        # Leer el archivo
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo, engine='openpyxl')

        # 2. Preparación de Datos (Nombres de columnas exactos de tu archivo)
        # Convertimos la columna de fecha
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        
        # 3. Filtros en Sidebar
        meses_dict = {
            1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
            7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"
        }
        
        mes_sel = st.sidebar.selectbox("Selecciona el Mes", options=range(1, 13), format_func=lambda x: meses_dict[x], index=1) # Default Febrero
        anio_sel = st.sidebar.number_input("Año", value=2026)

        # 4. FILTRADO CRÍTICO
        # Filtramos por Año, Mes y Estatus "RESUELTA"
        mask = (df['Fecha_DT'].dt.month == mes_sel) & \
               (df['Fecha_DT'].dt.year == anio_sel) & \
               (df['Estatus'].str.upper() == 'RESUELTA')
        
        # Aplicamos filtro y eliminamos duplicados de Folio para que el conteo sea real
        df_mes = df.loc[mask].copy().drop_duplicates(subset=['Folio'])

        # 5. MOSTRAR RESULTADOS
        st.subheader(f"Reportes Resueltos en {meses_dict[mes_sel]} {anio_sel}")
        
        # Métricas generales
        total_resueltos = len(df_mes)
        st.metric("Total de Reportes Resueltos (Neto)", total_resueltos)

        # Relación por Técnico
        st.markdown("### Resumen por Técnico")
        resumen_tecnicos = df_mes.groupby('Técnico').agg(
            Reportes_Resueltos=('Folio', 'count')
        ).reset_index().sort_values(by='Reportes_Resueltos', ascending=False)

        st.table(resumen_tecnicos)

        # Mostrar los datos para verificar
        with st.expander("Ver listado completo de este mes"):
            st.write(df_mes[['Folio', 'N.° de serie', 'Técnico', 'Última visita', 'Estatus', 'Categoría']])

    else:
        st.info("Por favor, carga el archivo Excel para comenzar.")

if __name__ == "__main__":
    main()
