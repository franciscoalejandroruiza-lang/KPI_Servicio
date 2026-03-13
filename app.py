import streamlit as st
import pandas as pd
import plotly.express as px
from logic import get_data_universe, calculate_penalties, get_detailed_penalties

st.set_page_config(page_title="SenAudit Pro - KPI Técnico", layout="wide")

# Inicialización de estado para tareas manuales
if 'special_tasks' not in st.session_state:
    st.session_state.special_tasks = pd.DataFrame(columns=['Técnico', 'Actividad', 'Puntaje'])

st.title("📊 Análisis de Servicio Técnico y Reincidencias")

with st.sidebar:
    st.header("Carga de Datos")
    uploaded_file = st.file_uploader("Subir Reporte (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    # Lectura flexible
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "⚙️ Configuración", "📈 Resumen", "📋 Reporte Detallado", 
        "⚠️ Penalización por Técnico", "🔍 Top Fallas (N/S)", "🏆 Resultado Final"
    ])

    with t1:
        st.subheader("Parámetros de Evaluación")
        c1, c2, c3 = st.columns(3)
        with c1:
            mes_sel = st.selectbox("Mes de análisis", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=2)
        with c2:
            año_sel = st.selectbox("Año", [2025, 2026], index=1)
        with c3:
            hist_sel = st.number_input("Meses de historial para auditar", 0, 12, 1)
        
        cp1, cp2 = st.columns(2)
        p_corr = cp1.number_input("Puntos x Penalización Correctivo", value=1.0)
        p_rein = cp2.number_input("Puntos x Penalización Reincidencia", value=1.0)
        scores = {"CORRECTIVO": p_corr, "REINCIDENCIA": p_rein}

        df_history, df_current = get_data_universe(df_raw, mes_sel, año_sel, hist_sel)

    with t2:
        st.subheader(f"Balance Operativo: {mes_sel} {año_sel}")
        resueltos = df_current[df_current['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Reportes Resueltos')
        penalizaciones = calculate_penalties(df_history, scores)
        
        resumen = pd.merge(resueltos, penalizaciones, on='Técnico', how='outer').fillna(0)
        resumen['Total Neto'] = resumen['Reportes Resueltos'] - resumen['Penalizaciones']
        
        st.dataframe(resumen.sort_values(by='Total Neto', ascending=False), use_container_width=True, hide_index=True)
        st.plotly_chart(px.bar(resumen, x='Técnico', y=['Reportes Resueltos', 'Penalizaciones'], barmode='group'), use_container_width=True)

    with t3:
        st.subheader("Concentrado de Servicios Resueltos")
        df_res_det = df_current[df_current['Estatus'] == 'RESUELTA'].copy()
        if not df_res_det.empty:
            st.dataframe(df_res_det.groupby('Técnico').size().reset_index(name='Servicios'), use_container_width=True)
            
            # SELECCIÓN SEGURA DE COLUMNAS
            cols_deseadas = ['Fecha recepción', 'Folio', 'Técnico', 'N.° de serie', 'Modelo', 'Falla']
            cols_reales = [c for c in cols_deseadas if c in df_res_det.columns]
            st.write("### Detalle Individual")
            st.dataframe(df_res_det[cols_reales], use_container_width=True, hide_index=True)
        else:
            st.warning("Sin datos resueltos en este periodo.")

    with t4:
        st.subheader("Análisis de Tendencias de Penalización")
        df_penal_det = get_detailed_penalties(df_history, scores)
        
        if not df_penal_det.empty:
            # Gráficos de Análisis
            g1, g2 = st.columns(2)
            with g1:
                st.plotly_chart(px.bar(df_penal_det.groupby('Técnico').size().reset_index(name='Eventos'), 
                                       x='Técnico', y='Eventos', title="Reincidencias por Técnico", color_discrete_sequence=['#FF4B4B']), use_container_width=True)
            with g2:
                st.plotly_chart(px.pie(df_penal_det, names='Modelo', title="Modelos con más reincidencias"), use_container_width=True)

            st.write("### Agrupado para Análisis de Mejora")
            agrup_audit = df_penal_det.groupby('Técnico').agg({'Puntos': 'sum', 'N.° de serie': 'count'}).reset_index()
            agrup_audit.columns = ['Técnico', 'Puntos Restados', 'Número de Eventos']
            st.dataframe(agrup_audit.sort_values(by='Puntos Restados', ascending=False), use_container_width=True, hide_index=True)
            
            with st.expander("Ver folios específicos para retroalimentación"):
                cols_audit = [c for c in ['Fecha recepción', 'Técnico', 'N.° de serie', 'Modelo', 'Categoría', 'Puntos'] if c in df_penal_det.columns]
                st.dataframe(df_penal_det[cols_audit], use_container_width=True, hide_index=True)
        else:
            st.success("No se detectaron tendencias de penalización.")

    with t5:
        st.subheader("Top 10 Equipos Críticos")
        df_f = df_history[df_history['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])]
        if not df_f.empty:
            top = df_f.groupby(['N.° de serie', 'Modelo']).size().reset_index(name='Intervenciones').sort_values(by='Intervenciones', ascending=False).head(10)
            st.table(top)
        else:
            st.info("No hay datos de fallas suficientes.")

    with t6:
        st.subheader("Puntaje Final de Productividad")
        final = resumen.copy()
        esp = st.session_state.special_tasks.groupby('Técnico')['Puntaje'].sum().reset_index()
        final = pd.merge(final, esp, on='Técnico', how='left').fillna(0)
        final['Puntaje Final'] = final['Total Neto'] + final['Puntaje']
        st.dataframe(final.sort_values(by='Puntaje Final', ascending=False), use_container_width=True, hide_index=True)

else:
    st.info("Sube un archivo para comenzar el análisis.")
