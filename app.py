import streamlit as st
import pandas as pd
import plotly.express as px
from logic import process_data, calculate_penalties

st.set_page_config(page_title="KPI Servicio Técnico", layout="wide")

if 'special_tasks' not in st.session_state:
    st.session_state.special_tasks = pd.DataFrame(columns=['Técnico', 'Actividad', 'Puntaje'])

st.title("🚀 Sistema de Análisis de Servicio Técnico")

with st.sidebar:
    st.header("Carga de Datos")
    uploaded_file = st.file_uploader("Archivo de Reportes (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)

    # Definición de las nuevas pestañas
    t1, t2, t3, t4, t5, t6 = st.tabs([
        "Configuración", 
        "Resumen por Técnico", 
        "Reporte Detallado", 
        "Top Fallas (N/S)", 
        "Asignación Especial", 
        "Resultado Final"
    ])

    # --- PESTAÑA 1: CONFIGURACIÓN ---
    with t1:
        st.subheader("Parámetros del Análisis")
        c1, c2, c3 = st.columns(3)
        with c1:
            mes_sel = st.selectbox("Mes de corte", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=2)
        with c2:
            año_sel = st.selectbox("Año", [2025, 2026], index=1)
        with c3:
            hist_sel = st.number_input("Historial (meses previos)", 0, 12, 1)
        
        st.divider()
        st.write("**Puntajes de Penalización**")
        cp1, cp2 = st.columns(2)
        p_corr = cp1.number_input("Puntos por Correctivo", value=1.0)
        p_rein = cp2.number_input("Puntos por Reincidencia", value=1.0)
        scores = {"CORRECTIVO": p_corr, "REINCIDENCIA": p_rein}

        df_filtro = process_data(df_raw, mes_sel, año_sel, hist_sel)

    # --- PESTAÑA 2: RESUMEN POR TÉCNICO (NUEVA) ---
    with t2:
        st.subheader(f"Balance de Servicio: {mes_sel}")
        
        # 1. Calcular Resueltos por Técnico (Solo Estatus RESUELTA)
        resueltos = df_filtro[df_filtro['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Reportes Resueltos')
        
        # 2. Calcular Penalizaciones
        penalizaciones = calculate_penalties(df_filtro, scores)
        
        # 3. Unir y calcular Total
        resumen_ejecutivo = pd.merge(resueltos, penalizaciones, on='Técnico', how='left').fillna(0)
        resumen_ejecutivo['Total Neto'] = resumen_ejecutivo['Reportes Resueltos'] - resumen_ejecutivo['Penalizaciones']
        
        st.dataframe(resumen_ejecutivo.sort_values(by='Total Neto', ascending=False), use_container_width=True, hide_index=True)
        
        # Gráfico comparativo
        fig_resumen = px.bar(resumen_ejecutivo, x='Técnico', y=['Reportes Resueltos', 'Penalizaciones'], 
                             title="Comparativa Resueltos vs Penalizaciones", barmode='group')
        st.plotly_chart(fig_resumen, use_container_width=True)

    # --- PESTAÑA 3: REPORTE DETALLADO ---
    with t3:
        st.subheader("Distribución de Categorías")
        df_det = df_filtro.groupby(['Técnico', 'Categoría']).size().reset_index(name='Cantidad')
        st.plotly_chart(px.bar(df_det, x='Técnico', y='Cantidad', color='Categoría'), use_container_width=True)

    # --- PESTAÑA 4: TOP FALLAS (N/S) ---
    with t4:
        st.subheader("Equipos Críticos (Mayor incidencia)")
        # Filtramos categorías que representen fallas
        df_ns = df_filtro[df_filtro['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])]
        top_ns = df_ns.groupby(['N.° de serie', 'Modelo', 'Nombre comercial']).size().reset_index(name='Fallas')
        top_ns = top_ns.sort_values(by='Fallas', ascending=False).head(10)
        
        st.write("Top 10 Números de Serie con más intervenciones:")
        st.table(top_ns)
        st.plotly_chart(px.pie(top_ns, values='Fallas', names='N.° de serie', title="Impacto por Equipo"), use_container_width=True)

    # --- PESTAÑA 5: ASIGNACIÓN ESPECIAL ---
    with t5:
        st.subheader("Puntos Extra o Ajustes")
        with st.form("form_ajuste"):
            t_sel = st.selectbox("Técnico", sorted(df_raw['Técnico'].dropna().unique()))
            act = st.text_input("Descripción de la actividad")
            pts = st.number_input("Puntaje (+/-)", value=0.0)
            if st.form_submit_button("Guardar Asignación"):
                nueva = pd.DataFrame([{'Técnico': t_sel, 'Actividad': act, 'Puntaje': pts}])
                st.session_state.special_tasks = pd.concat([st.session_state.special_tasks, nueva], ignore_index=True)
        st.dataframe(st.session_state.special_tasks, use_container_width=True)

    # --- PESTAÑA 6: RESULTADO FINAL ---
    with t6:
        st.subheader("Cómputo Final Consolidado")
        final_df = resumen_ejecutivo.copy()
        
        # Sumar puntos de asignación especial
        especiales = st.session_state.special_tasks.groupby('Técnico')['Puntaje'].sum().reset_index()
        final_df = pd.merge(final_df, especiales, on='Técnico', how='left').fillna(0)
        
        final_df['Puntaje Final'] = final_df['Total Neto'] + final_df['Puntaje']
        
        columnas_final = ['Técnico', 'Reportes Resueltos', 'Penalizaciones', 'Puntaje', 'Puntaje Final']
        st.dataframe(final_df[columnas_final].sort_values(by='Puntaje Final', ascending=False), use_container_width=True, hide_index=True)

else:
    st.warning("Favor de subir el archivo de Excel o CSV para comenzar el análisis.")
