import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# ==========================================
# CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Analizador Técnico Pro", layout="wide")

# Mapeo de meses para la interfaz
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# ==========================================
# LÓGICA DE PROCESAMIENTO
# ==========================================

def clean_data(df):
    """Limpieza adaptada a la estructura real del archivo."""
    # Eliminar espacios en nombres de columnas
    df.columns = df.columns.str.strip()
    
    # Mapeo específico según el archivo subido
    mapping = {
        'N.° de serie': 'serie',
        'Última visita': 'fecha',
        'Técnico': 'tecnico',
        'Categoría': 'categoria',
        'Estatus': 'estatus',
        'Problema reportado': 'problema'
    }
    df = df.rename(columns=mapping)
    
    # Validar que existan las columnas necesarias
    cols_necesarias = ['serie', 'fecha', 'tecnico', 'categoria', 'estatus']
    for col in cols_necesarias:
        if col not in df.columns:
            st.error(f"⚠️ No se encontró la columna crítica: '{col}'")
            return None

    # Limpieza de fechas: manejar errores y eliminar vacíos
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df = df.dropna(subset=['serie', 'fecha'])
    
    # Normalización de texto para comparaciones objetivas
    df['tecnico'] = df['tecnico'].astype(str).str.upper().str.strip()
    df['categoria'] = df['categoria'].astype(str).str.upper().str.strip()
    df['estatus'] = df['estatus'].astype(str).str.upper().str.strip()
    df['problema'] = df['problema'].astype(str).str.upper().fillna("SIN REPORTE")
    
    return df

def process_metrics(df, mes_num, anio, ventana):
    """Aplica filtros y calcula reincidencias."""
    fecha_fin = datetime(anio, mes_num, 1) + pd.offsets.MonthEnd(1)
    fecha_inicio = datetime(anio, mes_num, 1) - pd.DateOffset(months=ventana)
    
    # Filtrar ventana temporal
    df_v = df[(df['fecha'] >= fecha_inicio) & (df['fecha'] <= fecha_fin)].copy()
    df_v = df_v.sort_values(['serie', 'fecha'])
    
    # Identificar última visita por equipo (Serie)
    df_v['es_ultima'] = df_v.groupby('serie')['fecha'].transform('max') == df_v['fecha']
    
    # Penalización: Es CORRECTIVO y NO es la última visita registrada
    df_v['penalizable'] = (df_v['categoria'] == 'CORRECTIVO') & (~df_v['es_ultima'])
    
    return df_v

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.header("📂 Carga y Filtros")
    uploaded_file = st.file_uploader("Subir archivo Excel/CSV", type=["xlsx", "csv"])
    
    st.divider()
    
    # Selector de Mes en Español
    mes_nombre = st.selectbox("Mes a analizar", list(MESES_ES.values()), 
                              index=datetime.now().month - 1)
    # Obtener el número del mes a partir del nombre
    mes_sel = [k for k, v in MESES_ES.items() if v == mes_nombre][0]
    
    anio_sel = st.number_input("Año", value=2025)
    ventana_meses = st.slider("Meses previos para reincidencia", 1, 6, 3)
    
    st.divider()
    st.subheader("⚙️ Configuración de Pesos")
    config_df = pd.DataFrame({
        "Categoría": ["CORRECTIVO", "PREVENTIVO", "INSTALACION", "CONFIGURACION"],
        "Puntos": [1.0, 1.2, 2.0, 1.0]
    })
    conf_editada = st.data_editor(config_df, use_container_width=True, hide_index=True)

# ==========================================
# CUERPO PRINCIPAL
# ==========================================
st.title("🚀 Sistema de Análisis Técnico")

if uploaded_file:
    # Leer archivo según extensión
    if uploaded_file.name.endswith('.csv'):
        raw_df = pd.read_csv(uploaded_file)
    else:
        raw_df = pd.read_excel(uploaded_file)
        
    df_clean = clean_data(raw_df)
    
    if df_clean is not None:
        df_final = process_metrics(df_clean, mes_sel, anio_sel, ventana_meses)
        
        # Filtrar solo el mes actual para el resumen de resultados
        df_mes_actual = df_final[df_final['fecha'].dt.month == mes_sel]

        tab1, tab2, tab3, tab4 = st.tabs(["🏆 Resultados", "📉 Penalizaciones", "🔍 Top Fallas", "📋 Data Cruda"])

        with tab1:
            st.subheader(f"Desempeño Técnico: {mes_nombre} {anio_sel}")
            
            # Cálculos por técnico
            resueltas = df_mes_actual[df_mes_actual['estatus'] == 'RESUELTA'].groupby('tecnico').size().rename('Resueltas')
            pens = df_mes_actual[df_mes_actual['penalizable']].groupby('tecnico').size().rename('Penalizaciones')
            
            resumen = pd.concat([resueltas, pens], axis=1).fillna(0).astype(int)
            resumen['Score Final'] = resumen['Resueltas'] - resumen['Penalizaciones']
            
            # Métricas rápidas
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Resueltas", resumen['Resueltas'].sum())
            c2.metric("Total Penalizaciones", resumen['Penalizaciones'].sum(), delta_color="inverse")
            c3.metric("Eficiencia Promedio", f"{round(resumen['Score Final'].mean(), 2)} pts")

            st.dataframe(resumen.sort_values("Score Final", ascending=False), use_container_width=True)
            
            fig = px.bar(resumen.reset_index(), x='tecnico', y=['Resueltas', 'Penalizaciones'], 
                         title="Comparativa por Técnico", barmode="group", color_discrete_sequence=["#2ecc71", "#e74c3c"])
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("Detalle de Reincidencias")
            st.info("Se listan los equipos que requirieron más de una intervención correctiva en el periodo.")
            detalle_pen = df_mes_actual[df_mes_actual['penalizable']]
            st.table(detalle_pen[['fecha', 'serie', 'tecnico', 'problema']])

        with tab3:
            st.subheader("Análisis de Problemas Reportados")
            fallas = df_mes_actual['problema'].value_counts().reset_index()
            fallas.columns = ['Falla', 'Cantidad']
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.dataframe(fallas.head(15), use_container_width=True)
            with col_b:
                fig_pie = px.pie(fallas.head(10), values='Cantidad', names='Falla', hole=0.3)
                st.plotly_chart(fig_pie, use_container_width=True)

        with tab4:
            st.subheader("Visualización de datos procesados")
            st.dataframe(df_final, use_container_width=True)
else:
    st.warning("👈 Por favor, carga el archivo 'año reporte.xlsx' en el panel de la izquierda.")
