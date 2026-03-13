import streamlit as st
import pandas as pd
import plotly.express as px
from logic import get_data_universe, calculate_penalties, get_detailed_penalties

st.set_page_config(page_title="Auditoría de Servicio Técnico", layout="wide")

# ... (Misma carga de datos y configuración que el anterior) ...

if uploaded_file:
    # (Lógica de carga y pestañas iniciales...)
    
    # --- PESTAÑA: PENALIZACIÓN POR TÉCNICO (ANÁLISIS DE MEJORA) ---
    with t4:
        st.header("🔍 Auditoría de Reincidencias y Eventos")
        df_penal_det = get_detailed_penalties(df_history, scores)
        
        if not df_penal_det.empty:
            # 1. Dashboard de Tendencias
            c1, c2 = st.columns(2)
            with c1:
                # ¿Quién tiene más reincidencias?
                fig_tec = px.bar(df_penal_det.groupby('Técnico').size().reset_index(name='Casos'), 
                                 x='Técnico', y='Casos', title="Frecuencia de Reincidencias por Técnico",
                                 color_discrete_sequence=['#EF553B'])
                st.plotly_chart(fig_tec, use_container_width=True)
            
            with c2:
                # ¿Qué modelos fallan más después de ser atendidos?
                fig_mod = px.pie(df_penal_det, names='Modelo', title="Modelos con Mayor Tasa de Retorno")
                st.plotly_chart(fig_mod, use_container_width=True)

            st.divider()

            # 2. Tabla de Análisis Agrupada
            st.subheader("Análisis de Eventos por Técnico")
            # Agrupamos para ver el impacto económico/productivo
            agrupado = df_penal_det.groupby('Técnico').agg({
                'Puntos': 'sum',
                'N.° de serie': 'nunique',
                'Categoría': lambda x: x.mode()[0] if not x.empty else "N/A"
            }).rename(columns={
                'Puntos': 'Puntos Restados',
                'N.° de serie': 'Equipos Únicos',
                'Categoría': 'Falla más común'
            }).reset_index()
            
            st.dataframe(agrupado.sort_values(by='Puntos Restados', ascending=False), use_container_width=True, hide_index=True)

            # 3. Listado Detallado para Feedback Directo
            with st.expander("Ver desglose individual para retroalimentación"):
                st.info("Esta lista muestra los servicios específicos donde el técnico intervino pero el equipo volvió a fallar en el historial.")
                cols_finales = [c for c in ['Fecha recepción', 'Técnico', 'N.° de serie', 'Modelo', 'Categoría', 'Puntos'] if c in df_penal_det.columns]
                st.dataframe(df_penal_det[cols_finales], use_container_width=True, hide_index=True)
        else:
            st.success("Excelente: No se detectaron tendencias de reincidencia en este periodo.")

# ... (Resto de pestañas) ...
