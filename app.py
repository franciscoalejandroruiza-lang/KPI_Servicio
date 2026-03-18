import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit - Auditoría de Penalizaciones", layout="wide")

def main():
    st.title("🛡️ Auditoría de Calidad: Penalizaciones por Técnico")
    
    st.sidebar.header("Configuración")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:
        # 1. Carga y Limpieza
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo, engine='openpyxl')
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        df = df.dropna(subset=['Fecha_DT', 'Folio', 'N.° de serie'])

        # 2. Rango de Historial
        meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                      7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        col1, col2 = st.sidebar.columns(2)
        mes_eval = col1.selectbox("Mes a evaluar", options=range(1, 13), format_func=lambda x: meses_dict[x], index=datetime.now().month - 1)
        anio_eval = col2.number_input("Año", value=2026)
        meses_atras = st.sidebar.slider("Meses de historial para rastreo", 1, 6, 3)

        # 3. Definición de Fechas
        fecha_fin = datetime(anio_eval, mes_eval, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio = datetime(anio_eval, mes_eval, 1) - relativedelta(months=meses_atras)

        # 4. Procesamiento de Penalizaciones
        mask_rango = (df['Fecha_DT'] >= pd.Timestamp(fecha_inicio)) & (df['Fecha_DT'] <= pd.Timestamp(fecha_fin))
        df_rango = df.loc[mask_rango].copy().drop_duplicates(subset=['Folio'])
        df_rango = df_rango.sort_values(['N.° de serie', 'Fecha_DT'], ascending=[True, False])

        # Crear columna de penalización
        df_rango['Penalizacion'] = 0

        for serie, grupo in df_rango.groupby('N.° de serie'):
            if len(grupo) > 1:
                indices = grupo.index
                for i in range(len(indices) - 1):
                    # Si el reporte anterior fue CORRECTIVO, sumamos penalización a ese folio
                    if str(df_rango.loc[indices[i+1], 'Categoría']).upper() == 'CORRECTIVO':
                        df_rango.loc[indices[i+1], 'Penalizacion'] = 1

        # 5. Filtrar solo los datos que corresponden al mes evaluado para mostrar resultados
        mask_mes_eval = (df_rango['Fecha_DT'].dt.month == mes_eval) & (df_rango['Fecha_DT'].dt.year == anio_eval)
        df_final = df_rango.loc[mask_mes_eval]

        # 6. Tabla Resumen (Como en tu imagen)
        st.subheader(f"Resumen de Penalizaciones - {meses_dict[mes_eval]} {anio_eval}")
        
        resumen = df_final.groupby('Técnico').agg(
            penalizaciones=('Penalizacion', 'sum')
        ).reset_index()

        # Renombrar columnas para que coincidan con tu imagen
        resumen.columns = ['tecnico', 'penalizaciones']
        resumen = resumen.sort_values('penalizaciones', ascending=False)

        # Mostrar tabla limpia
        st.table(resumen)

    else:
        st.info("👋 Sube el archivo Excel para contabilizar las penalizaciones del equipo.")

if __name__ == "__main__":
    main()
