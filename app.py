import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. CONFIGURACIÓN VISUAL
st.set_page_config(page_title="SenAudit Pro - Dashboard", layout="wide")

# CSS para que las métricas se parezcan a las de tu imagen
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("📊 Resumen de Productividad Técnica")
    
    # --- SIDEBAR ---
    st.sidebar.header("Panel de Filtros")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel/CSV", type=["xlsx", "csv"])

    if archivo:
        # Carga de datos
        df_raw = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo, engine='openpyxl')

        # Filtros de fecha
        meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                         7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        col_side1, col_side2 = st.sidebar.columns(2)
        mes_sel = col_side1.selectbox("Mes", options=range(1, 13), format_func=lambda x: meses_nombres[x], index=1) # Default Febrero
        anio_sel = col_side2.number_input("Año", value=2026)
        
        ventana_meses = st.sidebar.slider("Meses previos para historial", 0, 6, 3)
        dias_reincidencia = st.sidebar.number_input("Días para Reincidencia", value=15)

        # --- PROCESAMIENTO ---
        df_raw['Fecha'] = pd.to_datetime(df_raw['Última visita'], errors='coerce')
        df_raw = df_raw.dropna(subset=['Fecha', 'Folio', 'N.° de serie'])
        
        # Rango de fechas
        fecha_fin = datetime(anio_sel, mes_sel, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio = datetime(anio_sel, mes_sel, 1) - relativedelta(months=ventana_meses)
        
        # FILTRO CRÍTICO: Solo RESUELTAS y eliminar duplicados (evita el error de 210 vs 105)
        mask = (df_raw['Fecha'] >= pd.Timestamp(fecha_inicio)) & \
               (df_raw['Fecha'] <= pd.Timestamp(fecha_fin)) & \
               (df_raw['Estatus'].str.upper() == 'RESUELTA')
        
        df_final = df_raw.loc[mask].copy().drop_duplicates(subset=['Folio'])

        # Lógica de Reincidencias
        df_final['Es_Reincidente'] = False
        df_final = df_final.sort_values(['N.° de serie', 'Fecha'], ascending=[True, False])

        for serie, grupo in df_final.groupby('N.° de serie'):
            if len(grupo) > 1:
                indices = grupo.index
                for i in range(len(indices) - 1):
                    diff = (df_final.loc[indices[i], 'Fecha'] - df_final.loc[indices[i+1], 'Fecha']).days
                    if diff <= dias_reincidencia:
                        if str(df_final.loc[indices[i+1], 'Categoría']).upper() == 'CORRECTIVO':
                            df_final.loc[indices[i+1], 'Es_Reincidente'] = True

        # --- SECCIÓN DE TARJETAS (KPIs) ---
        resueltos_netos = len(df_final)
        penalizados_total = int(df_final['Es_Reincidente'].sum())
        efectividad = ((resueltos_netos - penalizados_total) / resueltos_netos * 100) if resueltos_netos > 0 else 0

        # Diseño de 4 columnas para las métricas superiores
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("✅ Reportes Resueltos", resueltos_netos)
        with m2:
            st.metric("⚠️ Penalizaciones", penalizados_total, delta_color="inverse")
        with m3:
            st.metric("📈 Efectividad Real", f"{efectividad:.1f}%")
        with m4:
            st.metric("📅 Periodo", f"{meses_nombres[mes_
