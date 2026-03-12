import streamlit as st
import pandas as pd
import plotly.express as px
from logic import process_data, calculate_penalties

st.set_page_config(page_title="Analytics Servicio Técnico", layout="wide")

if 'special_tasks' not in st.session_state:
    st.session_state.special_tasks = pd.DataFrame(columns=['Técnico', 'Actividad', 'Puntaje'])

st.title("📊 Control de Servicio y Reincidencias")

with st.sidebar:
    st.header("Carga de Archivo")
    uploaded_file = st.file_uploader("Subir Reporte", type=['csv', 'xlsx'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "Configuración", "Matriz de penalizaciones", 
        "Reporte por técnico", "Top Equipos con Fallas", 
        "Asignación especial", "Resultado final"
    ])

    # --- PESTAÑA 1: CONFIGURACIÓN (POR MES) ---
    with t1:
        st.subheader("Parámetros de Tiempo")
        c1, c2, c3 = st.columns(3)
        with c1:
            mes_sel = st.selectbox("Mes a analizar", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=2)
        with c2:
            año_sel = st.selectbox("Año", [2025, 2026], index=1)
        with c3:
            hist_sel = st.number_input("Meses previos de historial", 0, 12, 1)
        
        st.divider()
        st.subheader("Configuración de Pesos")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_corr = st.number_input("Puntos Correctivo previo", value=1.0)
        with col_p2:
            p_rein = st.number_input("Puntos Reincidencia previa", value=1.0)
        
        scores = {"CORRECTIVO": p_corr, "REINCIDENCIA": p_rein}
        df_filtro = process_data(df_raw, mes_sel, año_sel, hist_sel)
        
        total_r = df_filtro[df_filtro['Estatus'] == 'RESUELTA'].shape[0]
        st.metric(f"Total Resueltas ({mes_sel})", total_r)

    # --- PESTAÑA 2: MATRIZ ---
    with t2:
        st.subheader("Penalizaciones por no cierre definitivo")
        matriz_df = calculate_penalties(df_filtro, scores)
        st.dataframe(matriz_df, use_container_width=True, hide_index=True)

    # --- PESTAÑA 3: POR TÉCNICO ---
    with t3:
        st.subheader("Actividad General")
        rep_t = df_filtro.groupby(['Técnico', 'Categoría']).size().reset_index(name='Total')
        st.plotly_chart(px.bar(rep_t, x='Técnico', y='Total', color='Categoría', barmode='group'), use_container_width=True)

    # --- PESTAÑA 4: TOP EQUIPOS (SERIES) ---
    with t4:
        st.subheader("Top 5 Números de Serie con más Fallas")
        st.write(f"Análisis basado en el periodo: {mes_sel} y {hist_sel} meses de historial.")
        
        # Filtramos solo por fallas reales (Correctivos y Reincidencias)
        df_fallas_equipo = df_filtro[df_filtro['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])]
        
        top_series = df_fallas_equipo.groupby(['N.° de serie', 'Modelo']).size().reset_index(name='Cant. Fallas')
        top_series = top_series.sort_values(by='Cant. Fallas', ascending=False).head(5)
        
        c_t, c_g = st.columns([1, 1])
        with c_t:
            st.table(top_series)
        with c_g:
            fig_series = px.pie(top_series, values='Cant. Fallas', names='N.° de serie', hover_data=['Modelo'], title="Distribución de Fallas por Serie")
            st.plotly_chart(fig_series, use_container_width=True)

    # --- PESTAÑA 5: ASIGNACIÓN ---
    with t5:
        st.subheader("Asignación de Actividades Extra")
        with st.form("form_esp"):
            tec = st.selectbox("Técnico", sorted(df_raw['Técnico'].dropna().unique()))
            act = st.selectbox("Actividad", ["Capacitación", "Apoyo campo", "Soporte"])
            pts = st.number_input("Puntos", value=0.0)
            if st.form_submit_button("Añadir"):
                nueva = pd.DataFrame([{'Técnico': tec, 'Actividad': act, 'Puntaje': pts}])
                st.session_state.special_tasks = pd.concat([st.session_state.special_tasks, nueva], ignore_index=True)
        st.dataframe(st.session_state.special_tasks, use_container_width=True)

    # --- PESTAÑA 6: RESULTADO FINAL ---
    with t6:
        st.subheader("Cómputo Final")
        res = df_filtro.groupby('Técnico').size().reset_index(name='Reportes')
        res = res.merge(matriz_df[['Técnico', 'Total penalizaciones']], on='Técnico', how='left').fillna(0)
        esp = st.session_state.special_tasks.groupby('Técnico')['Puntaje'].sum().reset_index()
        res = res.merge(esp, on='Técnico', how='left').fillna(0)
        res['Puntaje Final'] = res['Reportes'] - res['Total penalizaciones'] + res['Puntaje']
        st.dataframe(res.sort_values(by='Puntaje Final', ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("Carga el archivo para activar los selectores de mes y año.")
