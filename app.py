import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Analizador Técnico Pro", layout="wide")

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# ==========================================
# LÓGICA DE PROCESAMIENTO REFINADA
# ==========================================

def clean_data(df):
    df.columns = df.columns.str.strip()
    mapping = {
        'N.° de serie': 'serie',
        'Última visita': 'fecha',
        'Técnico': 'tecnico',
        'Categoría': 'categoria',
        'Estatus': 'estatus',
        'Problema reportado': 'problema'
    }
    df = df.rename(columns=mapping)
    
    # Conversión y limpieza
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df = df.dropna(subset=['serie', 'fecha'])
    
    # Normalización
    for col in ['tecnico', 'categoria', 'estatus']:
        df[col] = df[col].astype(str).str.upper().str.strip()
    
    return df

def procesar_penalizaciones_limpias(df, mes_sel, anio_sel, ventana):
    fecha_fin = datetime(anio_sel, mes_sel, 1) + pd.offsets.MonthEnd(1)
    fecha_inicio = datetime(anio_sel, mes_sel, 1) - pd.DateOffset(months=ventana)
    
    # Universo de datos para el análisis de historial
    universo = df[(df['fecha'] >= fecha_inicio) & (df['fecha'] <= fecha_fin)].copy()
    universo = universo.sort_values(by=['serie', 'fecha'])

    # LÓGICA DE "QUIÉN CORRIGIÓ"
    # 1. Encontrar la fecha de la última visita absoluta para cada serie en este periodo
    universo['ultima_fecha_serie'] = universo.groupby('serie')['fecha'].transform('max')
    
    # 2. Una visita es penalizable SI:
    #    - Es CATEGORIA CORRECTIVO
    #    - Su fecha es ANTERIOR a la última visita registrada para esa serie
    #    - (Esto asume que la última visita fue la que realmente solucionó el problema)
    universo['es_penalizacion'] = (
        (universo['categoria'] == 'CORRECTIVO') & 
        (universo['fecha'] < universo['ultima_fecha_serie'])
    )

    # Filtrar para mostrar solo los resultados del mes de interés
    reporte_mes = universo[universo['fecha'].dt.month == mes_sel].copy()
    return reporte_mes

# ==========================================
# INTERFAZ
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuración")
    uploaded_file = st.file_uploader("Subir archivo de Reporte", type=["csv", "xlsx"])
    
    mes_nombre = st.selectbox("Mes de Análisis", list(MESES_ES.values()), index=datetime.now().month - 1)
    mes_num = [k for k, v in MESES_ES.items() if v == mes_nombre][0]
    anio_num = st.number_input("Año", value=2025)
    ventana = st.slider("Ventana de historial (meses)", 1, 6, 2)

st.title(f"📊 Reporte de Productividad: {mes_nombre}")

if uploaded_file:
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    df_clean = clean_data(df_raw)
    
    if df_clean is not None:
        df_final = procesar_penalizaciones_limpias(df_clean, mes_num, anio_num, ventana)
        
        t1, t2, t3 = st.tabs(["🏆 Resumen", "📉 Detalle de Penalizaciones", "⚙️ Configuración"])
        
        with t1:
            # Agrupación por técnico
            resueltas = df_final[df_final['estatus'] == 'RESUELTA'].groupby('tecnico').size().rename('Resueltas')
            penalizaciones = df_final[df_final['es_penalizacion']].groupby('tecnico').size().rename('Penalizaciones')
            
            resumen = pd.concat([resueltas, penalizaciones], axis=1).fillna(0).astype(int)
            resumen['Puntos Netos'] = resumen['Resueltas'] - resumen['Penalizaciones']
            
            st.dataframe(resumen.sort_values("Puntos Netos", ascending=False), use_container_width=True)
            
            fig = px.bar(resumen.reset_index(), x='tecnico', y=['Resueltas', 'Penalizaciones'], 
                         barmode='group', title="Desempeño por Técnico",
                         color_discrete_map={'Resueltas': '#2ecc71', 'Penalizaciones': '#e74c3c'})
            st.plotly_chart(fig, use_container_width=True)

        with t2:
            st.subheader("Evidencia de Reincidencias")
            st.info("Nota: La última visita de cada serie NO se penaliza (se asume correctiva). Solo se penalizan las previas.")
            
            # Mostrar tabla detallada
            detalle = df_final[df_final['es_penalizacion']][['fecha', 'serie', 'tecnico', 'problema', 'categoria']]
            st.dataframe(detalle, use_container_width=True)

        with t3:
            st.write("Configuración de categorías detectadas:")
            st.write(df_final['categoria'].unique())
else:
    st.info("Sube el reporte para procesar las penalizaciones automáticamente.")
