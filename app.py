import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Configuración de la interfaz
st.set_page_config(page_title="SenAudit Pro", layout="wide")

def main():
    st.title("🚀 SenAudit Pro: Control de Calidad Técnica")
    st.sidebar.header("Configuración de Auditoría")

    archivo = st.sidebar.file_uploader("Cargar Reporte (Excel o CSV)", type=["xlsx", "csv"])

    if archivo:
        # Cargar datos
        if archivo.name.endswith('.csv'):
            df_raw = pd.read_csv(archivo)
        else:
            df_raw = pd.read_excel(archivo, engine='openpyxl')

        # --- PANEL DE FILTROS ---
        meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                         7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        mes_sel = st.sidebar.selectbox("Mes a evaluar", options=range(1, 13), format_func=lambda x: meses_nombres[x], index=datetime.now().month - 1)
        anio_sel = st.sidebar.number_input("Año", value=2026)
        ventana_meses = st.sidebar.slider("Meses previos para historial", 0, 6, 3)
        dias_reincidencia = st.sidebar.number_input("Días para considerar reincidencia", value=15)

        # --- PROCESAMIENTO SENIOR ---
        # 1. Normalización de fechas y limpieza
        df_raw['Fecha'] = pd.to_datetime(df_raw['Última visita'], errors='coerce')
        df_raw = df_raw.dropna(subset=['Fecha', 'Folio', 'N.° de serie'])
        
        # 2. Definir rango (Ej: Febrero + 3 meses atrás)
        fecha_fin = datetime(anio_sel, mes_sel, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio = datetime(anio_sel, mes_sel, 1) - relativedelta(months=ventana_meses)
        
        # 3. FILTRO MAESTRO (Solo RESUELTAS en el rango)
        # Esto asegura que si Alejandro tuvo 105 resueltas, solo aparezcan esas 105.
        mask = (df_raw['Fecha'] >= pd.Timestamp(fecha_inicio)) & \
               (df_raw['Fecha'] <= pd.Timestamp(fecha_fin)) & \
               (df_raw['Estatus'].str.upper() == 'RESUELTA')
        
        df_final = df_raw.loc[mask].copy().drop_duplicates(subset=['Folio'])

        # 4. LÓGICA DE PENALIZACIÓN
        df_final['Es_Reincidente'] = False
        df_final = df_final.sort_values(['N.° de serie', 'Fecha'], ascending=[True, False])

        for serie, grupo in df_final.groupby('N.° de serie'):
            if len(grupo) > 1:
                indices = grupo.index
                for i in range(len(indices) - 1):
                    # Comparamos el actual (i) con el anterior (i+1)
                    diff = (df_final.loc[indices[i], 'Fecha'] - df_final.loc[indices[i+1], 'Fecha']).days
                    
                    # REGLA: Si están cerca Y el anterior era CORRECTIVO, se penaliza el anterior
                    if diff <= dias_reincidencia:
                        if df_final.loc[indices[i+1], 'Categoría'].upper() == 'CORRECTIVO':
                            df_final.loc[indices[i+1], 'Es_Reincidente'] = True

        # --- VISUALIZACIÓN ---
        resueltos_netos = len(df_final)
        penalizados = df_final['Es_Reincidente'].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Reportes Resueltos", resueltos_netos)
        c2.metric("Penalizados (Correctivos)", int(penalizados), delta_color="inverse")
        c3.metric("Efectividad", f"{( (resueltos_netos - penalizados) / resueltos_netos * 100 if resueltos_netos > 0 else 0):.1f}%")

        st.subheader(f"Listado de Auditoría: {meses_nombres[mes_sel]} {anio_sel}")
        
        # Pintar la tabla: Rojo si es reincidente
        def highlight_reincidencia(row):
            return ['background-color: #ffcccc' if row.Es_Reincidente else '' for _ in row]

        st.dataframe(df_final.style.apply(highlight_reincidencia, axis=1), use_container_width=True)

    else:
        st.info("Esperando archivo... Por favor, carga el reporte de órdenes de servicio en el panel de la izquierda.")

if __name__ == "__main__":
    main()
