import streamlit as st
import pandas as pd
import plotly.express as px
from logic import get_data_universe, calculate_penalties, get_detailed_penalties

st.set_page_config(page_title="SenAudit Pro", layout="wide")

# Estado para asignaciones extra
if 'extra_points' not in st.session_state:
    st.session_state.extra_points = pd.DataFrame(columns=['Técnico', 'Motivo', 'Puntos'])

st.title("📊 Auditoría de Servicio Técnico")

uploaded_file = st.sidebar.file_uploader("Subir Reporte de Órdenes", type=['csv', 'xlsx'])

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    tabs = st.tabs(["⚙️ Configuración", "📈 Resumen", "📋 Detalle Categorías", "⚠️ Penalizaciones", "🔍 Top Fallas", "🏆 Asignación Extra"])

    # 1. CONFIGURACIÓN
    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        mes = c1.selectbox("Mes a revisar", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"], index=2)
        anio = c2.selectbox("Año", [2025, 2026], index=1)
        meses_h = c3.number_input("Meses de historial (Reincidencias)", 0, 12, 1)
        
        st.divider()
        st.write("### Valor de Penalización por Categoría")
        col_p1, col_p2 = st.columns(2)
        v_corr = col_p1.number_input("Puntos Correctivo", 0.0, 5.0, 1.0)
        v_rein = col_p2.number_input("Puntos Reincidencia", 0.0, 5.0, 1.0)
        scores = {"CORRECTIVO": v_corr, "REINCIDENCIA": v_rein}
        
        df_hist, df_curr = get_data_universe(df_raw, mes, anio, meses_h)

    # 2. RESUMEN POR TÉCNICO
    with tabs[1]:
        resueltos = df_curr[df_curr['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Resueltos')
        penales = calculate_penalties(df_hist, scores)
        resumen = pd.merge(resueltos, penales, on='Técnico', how='outer').fillna(0)
        resumen['Neto'] = resumen['Resueltos'] - resumen['Penalizaciones']
        st.dataframe(resumen.sort_values(by='Neto', ascending=False), use_container_width=True, hide_index=True)

    # 3. REPORTE DETALLADO (CATEGORÍAS)
    with tabs[2]:
        st.write(f"### Categorías Resueltas en {mes}")
        df_cat = df_curr[df_curr['Estatus'] == 'RESUELTA'].copy()
        pivot_cat = df_cat.groupby(['Técnico', 'Categoría']).size().unstack(fill_value=0)
        st.dataframe(pivot_cat, use_container_width=True)

    # 4. PENALIZACIONES POR TÉCNICO (AUDITORÍA)
    with tabs[3]:
        df_penal_det = get_detailed_penalties(df_hist, scores)
        if not df_penal_det.empty:
            tecnicos = ["Todos"] + sorted(df_penal_det['Técnico'].unique().tolist())
            tec_sel = st.selectbox("Filtrar técnico:", tecnicos)
            df_view = df_penal_det if tec_sel == "Todos" else df_penal_det[df_penal_det['Técnico'] == tec_sel]
            
            cols_show = ['Fecha recepción', 'Folio', 'N.° de serie', 'Nombre comercial', 'Categoría', 'Puntos_R']
            exist_cols = [c for c in cols_show if c in df_view.columns]
            st.dataframe(df_view[exist_cols], use_container_width=True, hide_index=True)
        else:
            st.info("Sin penalizaciones en el rango configurado.")

    # 5. TOP FALLA (MODA N/S)
    with tabs[4]:
        st.write(f"### Equipos con más reportes en {mes}")
        top_ns = df_curr.groupby(['N.° de serie', 'Modelo', 'Nombre comercial']).size().reset_index(name='Frecuencia')
        st.table(top_ns.sort_values(by='Frecuencia', ascending=False).head(10))

    # 6. ASIGNACIÓN EXTRA
    with tabs[5]:
        with st.form("extra_form"):
            t_extra = st.selectbox("Técnico", df_raw['Técnico'].unique())
            m_extra = st.text_input("Motivo")
            p_extra = st.number_input("Puntos", -10.0, 10.0, 1.0)
            if st.form_submit_button("Asignar Puntos"):
                new_row = pd.DataFrame([{'Técnico': t_extra, 'Motivo': m_extra, 'Puntos': p_extra}])
                st.session_state.extra_points = pd.concat([st.session_state.extra_points, new_row], ignore_index=True)
        
        st.write("### Registro de Puntos Extra")
        st.dataframe(st.session_state.extra_points, use_container_width=True)

else:
    st.info("Sube el archivo Excel para procesar los indicadores.")
