import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SenAudit Pro - Dashboard", layout="wide")

# Estilo personalizado para las métricas (opcional)
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #1E3A8A; }
    [data-testid="stMetricLabel"] { font-size: 16px; font-weight: bold; }
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
        mes_sel = col_side1.selectbox("Mes", options=range(1, 13), format_func=lambda x: meses_nombres[x], index=datetime.now().month - 1)
        anio_sel = col_side2.number_input("Año", value=2026)
        
        ventana_meses = st.sidebar.slider("Meses previos (Historial)", 0, 6, 3)
        dias_reincidencia = st.sidebar.number_input("Días para Reincidencia", value=15)

        # --- PROCESAMIENTO LOGICO ---
        df_raw['Fecha'] = pd.to_datetime(df_raw['Última visita'], errors='coerce')
        df_raw = df_raw.dropna(subset=['Fecha', 'Folio', 'N.° de serie'])
        
        fecha_fin = datetime(anio_sel, mes_sel, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio = datetime(anio_sel, mes_sel, 1) - relativedelta(months=ventana_meses)
        
        # Filtro estricto: Solo RESUELTAS y eliminar duplicados de folio
        mask = (df_raw['Fecha'] >= pd.Timestamp(fecha_inicio)) & \
               (df_raw['Fecha'] <= pd.Timestamp(fecha_fin)) & \
               (df_raw['Estatus'].str.upper() == 'RESUELTA')
        
        df_final = df_raw.loc[mask].copy().drop_duplicates(subset=['Folio'])

        # Cálculo de Reincidencias
        df_final['Es_Reincidente'] = False
        df_final = df_final.sort_values(['N.° de serie', 'Fecha'], ascending=[True, False])

        for serie, grupo in df_final.groupby('N.° de serie'):
            if len(grupo) > 1:
                indices = grupo.index
                for i in range(len(indices) - 1):
                    diff = (df_final.loc[indices[i], 'Fecha'] - df_final.loc[indices[i+1], 'Fecha']).days
                    if diff <= dias_reincidencia:
                        # Regla: Penalizar si el reporte anterior fue CORRECTIVO
                        if str(df_final.loc[indices[i+1], 'Categoría']).upper() == 'CORRECTIVO':
                            df_final.loc[indices[i+1], 'Es_Reincidente'] = True

        # --- SECCIÓN 1: TARJETAS DE MÉTRICAS (Como en tu imagen) ---
        resueltos_netos = len(df_final)
        penalizados_total = int(df_final['Es_Reincidente'].sum())
        efectividad = ((resueltos_netos - penalizados_total) / resueltos_netos * 100) if resueltos_netos > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Reportes Resueltos", resueltos_netos)
        m2.metric("Penalizaciones", penalizados_total)
        m3.metric("Efectividad Real", f"{efectividad:.1f}%")
        m4.metric("Mes Analizado", meses_nombres[mes_sel])

        st.markdown("---")

        # --- SECCIÓN 2: TABLA DE TÉCNICOS ---
        st.subheader("📋 Relación por Técnico")
        
        resumen_tecnicos = df_final.groupby('Técnico').agg(
            Resueltos=('Folio', 'count'),
            Penalizados=('Es_Reincidente', 'sum')
        ).reset_index()

        resumen_tecnicos['Efectividad %'] = (
            (resumen_tecnicos['Resueltos'] - resumen_tecnicos['Penalizados']) / 
            resumen_tecnicos['Resueltos'] * 100
        ).round(1)

        resumen_tecnicos = resumen_tecnicos.sort_values(by='Resueltos', ascending=False)
        
        # Mostrar tabla estilizada
        st.dataframe(
            resumen_tecnicos.style.background_gradient(subset=['Efectividad %'], cmap='RdYlGn'),
            use_container_width=True,
            hide_index=True
        )

        # --- SECCIÓN 3: GRÁFICO ---
        st.markdown("---")
        fig = px.bar(resumen_tecnicos, x='Técnico', y=['Resueltos', 'Penalizados'],
                     title="Balance de Servicios por Técnico", barmode='group',
                     color_discrete_map={"Resueltos": "#22C55E", "Penalizados": "#EF4444"})
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("👋 Bienvenida/o. Por favor carga el archivo Excel para generar el reporte.")

if __name__ == "__main__":
    main()
