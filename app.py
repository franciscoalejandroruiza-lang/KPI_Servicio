import streamlit as st
import pandas as pd
import plotly.express as px
from logic import get_data_universe, calculate_penalties

st.set_page_config(page_title="KPI Servicio Técnico", layout="wide")

if 'special_tasks' not in st.session_state:
    st.session_state.special_tasks = pd.DataFrame(columns=['Técnico', 'Actividad', 'Puntaje'])

st.title("📊 Análisis de Servicio Técnico y Reincidencias")

with st.sidebar:
    st.header("Carga de Datos")
    uploaded_file = st.file_uploader("Subir Reporte (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "Configuración", "Resumen por Técnico", "Reporte Detallado", 
        "Top Fallas (N/S)", "Asignación Especial", "Resultado Final"
    ])

    # --- PESTAÑA 1: CONFIGURACIÓN ---
    with t1:
        st.subheader("Parámetros del Sistema")
        c1, c2, c3 = st.columns(3)
        with c1:
            mes_sel = st.selectbox("Mes de análisis", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=2)
        with c2:
            año_sel = st.selectbox("Año", [2025, 2026], index=1)
        with c3:
            hist_sel = st.number_input("Meses de historial para penalizar", 0, 12, 1)
        
        st.divider()
        cp1, cp2 = st.columns(2)
        p_corr = cp1.number_input("Puntos Penalización Correctivo", value=1.0)
        p_rein = cp2.number_input("Puntos Penalización Reincidencia", value=1.0)
        scores = {"CORRECTIVO": p_corr, "REINCIDENCIA": p_rein}

        # Obtenemos los dos dataframes: el del mes actual y el del historial completo
        df_history, df_current = get_data_universe(df_raw, mes_sel, año_sel, hist_sel)

    # --- PESTAÑA 2: RESUMEN POR TÉCNICO ---
    with t2:
        st.subheader(f"Desempeño Operativo: {mes_sel} {año_sel}")
        
        # 1. Reportes RESUELTOS (Solo del mes seleccionado)
        resueltos = df_current[df_current['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Reportes Resueltos')
        
        # 2. Penalizaciones (Basadas en el Historial Configurado)
        penalizaciones = calculate_penalties(df_history, scores)
        
        # 3. Consolidación
        resumen = pd.merge(resueltos, penalizaciones, on='Técnico', how='outer').fillna(0)
        resumen['Total Neto'] = resumen['Reportes Resueltos'] - resumen['Penalizaciones']
        
        st.dataframe(resumen.sort_values(by='Total Neto', ascending=False), use_container_width=True, hide_index=True)
        
        fig = px.bar(resumen, x='Técnico', y=['Reportes Resueltos', 'Penalizaciones'], 
                     title=f"Balance: Resueltos en {mes_sel} vs Penalizaciones del Historial", barmode='group')
        st.plotly_chart(fig, use_container_width=True)

    
    # --- PESTAÑA 4: TOP FALLAS (N/S) ---
    with t4:
        st.subheader("Equipos con mayor recurrencia de fallas")
        # Usamos el historial para ver qué equipos han dado más problemas en el tiempo
        df_fallas = df_history[df_history['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])]
        top_ns = df_fallas.groupby(['N.° de serie', 'Modelo', 'Nombre comercial']).size().reset_index(name='Total Intervenciones')
        top_ns = top_ns.sort_values(by='Total Intervenciones', ascending=False).head(10)
        
        st.table(top_ns)
        st.plotly_chart(px.bar(top_ns, x='N.° de serie', y='Total Intervenciones', color='Modelo', title="Top 10 Equipos Críticos"))
# Dentro de app.py, busca la sección de las pestañas:

    # --- PESTAÑA 3: REPORTE DETALLADO (Concentrado de Resueltos) ---
    with t3:
        st.subheader(f"Concentrado de Servicios Resueltos - {mes_sel}")
        # Filtramos solo lo resuelto en el mes actual
        df_resueltos_det = df_current[df_current['Estatus'] == 'RESUELTA'].copy()
        
        if not df_resueltos_det.empty:
            # Agrupación para ver volumen por técnico
            resumen_v = df_resueltos_det.groupby('Técnico').size().reset_index(name='Total Resueltos')
            st.dataframe(resumen_v.sort_values(by='Total Resueltos', ascending=False), use_container_width=True)
            
            st.divider()
            st.write("### Detalle de Folios")
            st.dataframe(df_resueltos_det[['Fecha recepción', 'Folio', 'Técnico', 'N.° de serie', 'Modelo', 'Falla']], use_container_width=True)
        else:
            st.warning("No hay datos de servicios resueltos en este periodo.")

    # --- PESTAÑA 5: PENALIZACIÓN POR TÉCNICOS ---
    # (Cambiamos el uso de la pestaña 5 que estaba como "Asignación Especial" o creamos una nueva)
    with t5:
        st.subheader("Auditoría de Penalizaciones (Historial)")
        from logic import get_detailed_penalties # Asegúrate de importar o tenerla disponible
        
        df_penal_det = get_detailed_penalties(df_history, scores)
        
        if not df_penal_det.empty:
            # Vista agrupada por técnico para ver quién tiene más incidencias
            agrupado_p = df_penal_det.groupby('Técnico').agg({
                'N.° de serie': 'count',
                'Puntos': 'sum'
            }).rename(columns={'N.° de serie': 'Equipos Reincidentes', 'Puntos': 'Total Penalización'}).reset_index()
            
            st.dataframe(agrupado_p.sort_values(by='Total Penalización', ascending=False), use_container_width=True)
            
            st.divider()
            st.write("### Desglose de Equipos que Penalizaron")
            st.info("Estos equipos fueron atendidos por el técnico, pero volvieron a fallar y fueron cerrados por alguien más después.")
            st.dataframe(df_penal_det, use_container_width=True)
        else:
            st.success("No se encontraron penalizaciones en el periodo seleccionado.")
    # --- PESTAÑA 6: RESULTADO FINAL ---
    with t6:
        st.subheader("Cómputo de Productividad Final")
        final = resumen.copy()
        esp = st.session_state.special_tasks.groupby('Técnico')['Puntaje'].sum().reset_index()
        final = pd.merge(final, esp, on='Técnico', how='left').fillna(0)
        final['Puntaje Final'] = final['Total Neto'] + final['Puntaje']
        
        st.dataframe(final[['Técnico', 'Reportes Resueltos', 'Penalizaciones', 'Puntaje', 'Puntaje Final']].sort_values(by='Puntaje Final', ascending=False), 
                     use_container_width=True, hide_index=True)

else:
    st.info("Favor de subir el reporte de órdenes de servicio para iniciar el análisis.")
