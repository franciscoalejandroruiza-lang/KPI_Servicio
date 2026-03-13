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
    # Lectura de datos
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file) [cite: 1]

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "⚙️ Configuración", "📈 Resumen", "📋 Reporte Detallado", 
        "⚠️ Penalización por Técnico", "🔍 Top Fallas", "🏆 Resultado Final"
    ]) [cite: 1]

    # --- PESTAÑA 1: CONFIGURACIÓN ---
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

    # --- PESTAÑA 2: RESUMEN ---
    with t2:
        st.subheader(f"Balance Operativo: {mes_sel}")
        resueltos = df_current[df_current['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Reportes Resueltos') [cite: 1]
        penal_res = calculate_penalties(df_history, scores) [cite: 1]
        resumen = pd.merge(resueltos, penal_res, on='Técnico', how='outer').fillna(0) [cite: 1]
        resumen['Total Neto'] = resumen['Reportes Resueltos'] - resumen['Penalizaciones'] [cite: 1]
        st.dataframe(resumen.sort_values(by='Total Neto', ascending=False), use_container_width=True, hide_index=True) [cite: 1]

    # --- PESTAÑA 3: REPORTE DETALLADO ---
    with t3:
        st.subheader("Servicios Resueltos del Mes")
        df_res_det = df_current[df_current['Estatus'] == 'RESUELTA'].copy()
        if not df_res_det.empty:
            # Selección segura de columnas para evitar KeyError
            cols_deseadas = ['Fecha recepción', 'Folio', 'Técnico', 'N.° de serie', 'Modelo', 'Falla']
            cols_reales = [c for c in cols_deseadas if c in df_res_det.columns]
            st.dataframe(df_res_det[cols_reales], use_container_width=True, hide_index=True)
        else:
            st.warning("Sin datos resueltos en este periodo.")

    # --- PESTAÑA 4: AUDITORÍA DE PENALIZACIONES (DETALLE SOLICITADO) ---
    with t4:
        st.header("🔍 Auditoría de Penalizaciones por Técnico")
        df_penal_det = get_detailed_penalties(df_history, scores)
        
        if not df_penal_det.empty:
            tecnicos_u = ["Todos"] + sorted(df_penal_det['Técnico'].unique().tolist())
            tec_sel = st.selectbox("Filtrar por técnico para auditoría:", tecnicos_u)
            
            df_view = df_penal_det.copy()
            if tec_sel != "Todos":
                df_view = df_penal_det[df_penal_det['Técnico'] == tec_sel]

            st.write(f"### Desglose de Eventos: {tec_sel}")
            
            # Mapeo de columnas para la vista de auditoría
            cols_map = {
                'Fecha recepción': 'Fecha',
                'Folio': 'Folio de Vista',
                'N.° de serie': 'Número de Serie',
                'Nombre comercial': 'Cliente',
                'Modelo': 'Modelo',
                'Categoría': 'Tipo',
                'Puntos': 'Puntos -'
            }
            
            cols_audit = [c for c in cols_map.keys() if c in df_view.columns]
            st.dataframe(df_view[cols_audit].rename(columns=cols_map), use_container_width=True, hide_index=True)
            st.info(f"Se muestran {len(df_view)} registros que generaron penalización por falta de efectividad en la visita.")
        else:
            st.success("No se detectaron penalizaciones en el periodo seleccionado.")

    # --- PESTAÑA 5: TOP FALLAS ---
    with t5:
        st.subheader("Equipos Críticos (Historial)")
        df_f = df_history[df_history['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])] [cite: 1]
        if not df_f.empty:
            top = df_f.groupby(['N.° de serie', 'Modelo', 'Nombre comercial']).size().reset_index(name='Intervenciones') [cite: 1]
            st.table(top.sort_values(by='Intervenciones', ascending=False).head(10)) [cite: 1]

    # --- PESTAÑA 6: RESULTADO FINAL ---
    with t6:
        st.subheader("Puntaje Final de Productividad")
        final = resumen.copy() [cite: 1]
        esp = st.session_state.special_tasks.groupby('Técnico')['Puntaje'].sum().reset_index() [cite: 1]
        final = pd.merge(final, esp, on='Técnico', how='left').fillna(0) [cite: 1]
        final['Puntaje Final'] = final['Total Neto'] + final['Puntaje'] [cite: 1]
        st.dataframe(final.sort_values(by='Puntaje Final', ascending=False), use_container_width=True, hide_index=True) [cite: 1]

else:
    st.info("Favor de subir el reporte de órdenes de servicio para iniciar el análisis.") [cite: 1]
