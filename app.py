import streamlit as st
import pandas as pd
import plotly.express as px
from logic import get_data_universe, calculate_penalties, get_detailed_penalties [cite: 1]

st.set_page_config(page_title="SenAudit Pro - KPI", layout="wide") [cite: 1]

if 'special_tasks' not in st.session_state:
    st.session_state.special_tasks = pd.DataFrame(columns=['Técnico', 'Actividad', 'Puntaje']) [cite: 1]

st.title("📊 Análisis de Servicio Técnico y Reincidencias") [cite: 1]

with st.sidebar:
    st.header("Carga de Datos")
    uploaded_file = st.file_uploader("Subir Reporte (CSV/Excel)", type=['csv', 'xlsx']) [cite: 1]

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file) [cite: 1]

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "⚙️ Configuración", "📈 Resumen", "📋 Reporte Detallado", 
        "⚠️ Penalización por Técnico", "🔍 Top Fallas", "🏆 Resultado Final"
    ])

    with t1:
        st.subheader("Parámetros del Sistema")
        c1, c2, c3 = st.columns(3)
        with c1:
            mes_sel = st.selectbox("Mes de análisis", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=2) [cite: 1]
        with c2:
            año_sel = st.selectbox("Año", [2025, 2026], index=1) [cite: 1]
        with c3:
            hist_sel = st.number_input("Meses de historial", 0, 12, 1) [cite: 1]
        
        scores = {"CORRECTIVO": 1.0, "REINCIDENCIA": 1.0}
        df_history, df_current = get_data_universe(df_raw, mes_sel, año_sel, hist_sel) [cite: 1]

    with t3:
        st.subheader("Concentrado de Servicios Resueltos")
        df_res_det = df_current[df_current['Estatus'] == 'RESUELTA'].copy() [cite: 1]
        if not df_res_det.empty:
            # Selección segura de columnas para evitar KeyError
            cols_deseadas = ['Fecha recepción', 'Folio', 'Técnico', 'N.° de serie', 'Modelo', 'Falla']
            cols_reales = [c for c in cols_deseadas if c in df_res_det.columns]
            st.dataframe(df_res_det[cols_reales], use_container_width=True, hide_index=True)

    # --- PESTAÑA 4: AUDITORÍA DE PENALIZACIONES (LO QUE SOLICITASTE) ---
    with t4:
        st.header("🔍 Auditoría Detallada de Penalizaciones")
        df_penal_det = get_detailed_penalties(df_history, scores)
        
        if not df_penal_det.empty:
            # Buscador por Técnico
            tecnicos = ["Todos"] + sorted(df_penal_det['Técnico'].unique().tolist())
            tec_sel = st.selectbox("Selecciona un técnico para revisar sus eventos:", tecnicos)
            
            df_view = df_penal_det.copy()
            if tec_sel != "Todos":
                df_view = df_penal_det[df_penal_det['Técnico'] == tec_sel]

            st.write(f"### Detalle de Eventos: {tec_sel}")
            
            # Mapeo de columnas para claridad en la revisión
            cols_map = {
                'Fecha recepción': 'Fecha',
                'Folio': 'Folio de Vista',
                'N.° de serie': 'Número de Serie',
                'Nombre comercial': 'Cliente',
                'Modelo': 'Modelo',
                'Puntos': 'Puntos Restados'
            }
            
            cols_finales = [c for c in cols_map.keys() if c in df_view.columns]
            st.dataframe(df_view[cols_finales].rename(columns=cols_map), use_container_width=True, hide_index=True)
            st.info(f"Se encontraron {len(df_view)} eventos que requirieron una segunda visita por otro técnico.")
        else:
            st.success("No se detectaron penalizaciones en el periodo seleccionado.")

    with t6:
        st.subheader("Resultado Final")
        resumen = calculate_penalties(df_history, scores) # Simplificado para el ejemplo
        st.dataframe(resumen, use_container_width=True)

else:
    st.info("Favor de subir el reporte de órdenes de servicio para iniciar el análisis.") [cite: 1]
