import streamlit as st
import pandas as pd
import plotly.express as px
from logic import get_data_universe, calculate_penalties, get_detailed_penalties

st.set_page_config(page_title="SenAudit Pro - KPI", layout="wide")

if 'special_tasks' not in st.session_state:
    st.session_state.special_tasks = pd.DataFrame(columns=['Técnico', 'Actividad', 'Puntaje'])

st.title("📊 Análisis de Servicio Técnico y Reincidencias")

with st.sidebar:
    st.header("Carga de Datos")
    uploaded_file = st.file_uploader("Subir Reporte (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "⚙️ Configuración", "📈 Resumen", "📋 Reporte Detallado", 
        "⚠️ Penalización por Técnico", "🔍 Top Fallas", "🏆 Resultado Final"
    ])

    with t1:
        st.subheader("Parámetros del Sistema")
        c1, c2, c3 = st.columns(3)
        with c1:
            mes_sel = st.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=2)
        with c2:
            año_sel = st.selectbox("Año", [2025, 2026], index=1)
        with c3:
            hist_sel = st.number_input("Meses de historial", 0, 12, 1)
        
        scores = {"CORRECTIVO": 1.0, "REINCIDENCIA": 1.0}
        df_history, df_current = get_data_universe(df_raw, mes_sel, año_sel, hist_sel)

    with t2:
        st.subheader(f"Balance Operativo: {mes_sel}")
        resueltos = df_current[df_current['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Reportes Resueltos')
        penal_res = calculate_penalties(df_history, scores)
        resumen = pd.merge(resueltos, penal_res, on='Técnico', how='outer').fillna(0)
        resumen['Total Neto'] = resumen['Reportes Resueltos'] - resumen['Penalizaciones']
        st.dataframe(resumen.sort_values(by='Total Neto', ascending=False), use_container_width=True, hide_index=True)

    with t3:
        st.subheader("Concentrado de Servicios")
        df_res_det = df_current[df_current['Estatus'] == 'RESUELTA'].copy()
        if not df_res_det.empty:
            # Selección segura de columnas para evitar KeyError
            cols_deseadas = ['Fecha recepción', 'Folio', 'Técnico', 'N.° de serie', 'Modelo', 'Falla']
            cols_reales = [c for c in cols_deseadas if c in df_res_det.columns]
            st.dataframe(df_res_det[cols_reales], use_container_width=True, hide_index=True)

    with t4:
        st.header("🔍 Auditoría Detallada")
        df_penal_det = get_detailed_penalties(df_history, scores)
        if not df_penal_det.empty:
            tecnicos = ["Todos"] + sorted(df_penal_det['Técnico'].unique().tolist())
            tec_sel = st.selectbox("Selecciona un técnico para auditar:", tecnicos)
            
            df_view = df_penal_det if tec_sel == "Todos" else df_penal_det[df_penal_det['Técnico'] == tec_sel]
            
            cols_map = {'Fecha recepción': 'Fecha', 'Folio': 'Folio', 'N.° de serie': 'Serie', 'Nombre comercial': 'Cliente', 'Puntos': 'Puntos -'}
            cols_audit = [c for c in cols_map.keys() if c in df_view.columns]
            st.dataframe(df_view[cols_audit].rename(columns=cols_map), use_container_width=True, hide_index=True)
        else:
            st.success("Sin penalizaciones.")

    with t6:
        st.subheader("Resultado Final")
        st.dataframe(resumen, use_container_width=True)

else:
    st.info("Sube un archivo para comenzar.")
