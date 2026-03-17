import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Auditoría de Reincidencias Técnicas", layout="wide")

st.title("📊 Análisis de Penalizaciones por Reincidencia")
st.markdown("""
Esta herramienta identifica visitas **Correctivas** que no fueron la última intervención de un equipo, 
marcándolas como penalizaciones automáticas.
""")

# 1. Carga de Archivo
uploaded_file = st.sidebar.file_uploader("Cargar reporte técnico (Excel)", type=["xlsx"])

if uploaded_file:
    # Leer datos
    df = pd.read_excel(uploaded_file)
    
    # Limpieza y Conversión de Fechas
    df['Última visita'] = pd.to_datetime(df['Última visita'], errors='coerce')
    df = df.dropna(subset=['N.° de serie', 'Última visita'])
    
    # 2. Lógica de Procesamiento
    # Ordenar cronológicamente por equipo
    df = df.sort_values(by=['N.° de serie', 'Última visita'], ascending=True)
    
    # Identificar la última intervención (1 si es la más reciente, 0 si no)
    df['Es_ultima'] = 0
    df.loc[df.groupby('N.° de serie')['Última visita'].idxmax(), 'Es_ultima'] = 1
    
    # Aplicar Penalización: Solo si es CORRECTIVO y NO es la última visita
    df['Penaliza'] = ((df['Categoría'] == 'CORRECTIVO') & (df['Es_ultima'] == 0)).astype(int)

    # 3. Visualización de Indicadores (Métricas)
    total_penalizaciones = df['Penaliza'].sum()
    tecnico_mas_reincidente = df.groupby('Técnico')['Penaliza'].sum().idxmax()
    
    col1, col2 = st.columns(2)
    col1.metric("Total Penalizaciones", f"{total_penalizaciones}")
    col2.metric("Técnico con más reincidencias", tecnico_mas_reincidente)

    st.divider()

    # 4. Gráficas con Plotly
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Penalizaciones por Técnico")
        resumen_tecnico = df.groupby('Técnico')['Penaliza'].sum().reset_index().sort_values(by='Penaliza', ascending=False)
        fig_bar = px.bar(resumen_tecnico, x='Técnico', y='Penaliza', 
                         color='Penaliza', labels={'Penaliza': 'Cant. Penalizaciones'},
                         color_continuous_scale='Reds')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_chart2:
        st.subheader("Distribución por Categoría")
        # Mostramos cuántos registros son penalizables vs no penalizables
        fig_pie = px.pie(df, names='Categoría', values='Penaliza', hole=0.4,
                         title="Origen de Penalizaciones",
                         color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_pie, use_container_width=True)

    # 5. Tabla de Datos Interactiva
    st.subheader("Detalle de Registros Procesados")
    # Filtro para ver solo penalizados o todo
    ver_solo_penalizados = st.checkbox("Mostrar solo registros con penalización")
    
    df_mostrar = df if not ver_solo_penalizados else df[df['Penaliza'] == 1]
    
    st.dataframe(df_mostrar[['N.° de serie', 'Técnico', 'Última visita', 'Categoría', 'Es_ultima', 'Penaliza']], 
                 use_container_width=True)

    # Botón para descargar el resultado
    @st.cache_data
    def convert_df(df_to_download):
        return df_to_download.to_csv(index=False).encode('utf-8')

    csv = convert_df(df)
    st.download_button("📥 Descargar reporte procesado (CSV)", data=csv, file_name="auditoria_tecnica.csv", mime='text/csv')

else:
    st.info("Por favor, sube un archivo Excel en la barra lateral para comenzar el análisis.")
