import streamlit as st
import pandas as pd
import plotly.express as px
from logic import process_data, calculate_penalties

# Configuración visual estilo profesional
st.set_page_config(page_title="Dashboard Servicio Técnico", layout="wide")

# Mantener estado de las asignaciones especiales entre clics
if 'special_tasks' not in st.session_state:
    st.session_state.special_tasks = pd.DataFrame(columns=['Técnico', 'Actividad', 'Puntaje'])

st.title("📊 Análisis de Reportes de Servicio")

# Sidebar para carga de archivos
with st.sidebar:
    st.header("Carga de Datos")
    uploaded_file = st.file_uploader("Subir CSV o Excel", type=['csv', 'xlsx'])
    st.divider()
    st.info("Configura los meses y penalizaciones en la primera pestaña.")

if uploaded_file:
    # Carga automática según extensión
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Definición de Pestañas (Igual a tu requerimiento)
    t1, t2, t3, t4, t5, t6 = st.tabs([
        "Configuración", "Matriz de penalizaciones", 
        "Reporte por técnico", "Top 3 fallas", 
        "Asignación especial", "Resultado final"
    ])

    with t1:
        st.subheader("Configuración de Periodo y Puntajes")
        c1, c2 = st.columns(2)
        with c1:
            mes_ref = st.date_input("Mes de análisis", value=pd.to_datetime("2026-03-10"))
            meses_hist = st.number_input("Meses de historial", 0, 12, 1)
        with c2:
            sc_corr = st.number_input("Puntos por Correctivo", value=1.0)
            sc_rein = st.number_input("Puntos por Reincidencia", value=1.0)
            scores = {"CORRECTIVO": sc_corr, "REINCIDENCIA": sc_rein}

        df_filtro = process_data(df_raw, mes_ref, meses_hist)
        
        # Métrica resaltada
        resueltas = df_filtro[df_filtro['Estatus'] == 'RESUELTA'].shape[0]
        st.metric("Total Reportes Resueltos", resueltas)

    with t2:
        st.subheader("Matriz de Penalizaciones")
        matriz_df = calculate_penalties(df_filtro, scores)
        st.dataframe(matriz_df, use_container_width=True, hide_index=True)

    with t3:
        st.subheader("Reporte por Técnico")
        reporte_t = df_filtro.groupby(['Técnico', 'Categoría']).size().reset_index(name='Total')
        fig = px.bar(reporte_t, x='Técnico', y='Total', color='Categoría', barmode='group')
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(reporte_t.pivot(index='Técnico', columns='Categoría', values='Total').fillna(0), use_container_width=True)

    with t4:
        st.subheader("Top 3 Fallas Más Frecuentes")
        fallas = df_filtro['Problema reportado'].value_counts().head(3).reset_index()
        fallas.columns = ['Falla', 'Cantidad']
        fallas['%'] = (fallas['Cantidad'] / fallas['Cantidad'].sum() * 100).round(1)
        st.table(fallas)
        st.plotly_chart(px.pie(fallas, values='Cantidad', names='Falla'), use_container_width=True)

    with t5:
        st.subheader("Asignación Especial")
        with st.form("extra_points"):
            t_asig = st.selectbox("Técnico", sorted(df_raw['Técnico'].unique()))
            act_asig = st.selectbox("Actividad", ["Capacitación", "Apoyo en campo", "Soporte crítico"])
            pts_asig = st.number_input("Puntaje", value=0.0)
            if st.form_submit_button("Añadir"):
                nueva = pd.DataFrame([{'Técnico': t_asig, 'Actividad': act_asig, 'Puntaje': pts_asig}])
                st.session_state.special_tasks = pd.concat([st.session_state.special_tasks, nueva], ignore_index=True)
        st.dataframe(st.session_state.special_tasks, use_container_width=True)

    with t6:
        st.subheader("Consolidado Final")
        final = df_filtro.groupby('Técnico').size().reset_index(name='Reportes atendidos')
        final = final.merge(matriz_df[['Técnico', 'Total penalizaciones']], on='Técnico', how='left').fillna(0)
        esp_sum = st.session_state.special_tasks.groupby('Técnico')['Puntaje'].sum().reset_index()
        final = final.merge(esp_sum, on='Técnico', how='left').fillna(0)
        final['Puntaje Final'] = final['Reportes atendidos'] - final['Total penalizaciones'] + final['Puntaje']
        st.dataframe(final.sort_values(by='Puntaje Final', ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("Sube el archivo de reporte para activar el tablero.")
