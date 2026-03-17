import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTILO
# ==========================================
st.set_page_config(page_title="Analizador Técnico Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# FUNCIONES DE PROCESAMIENTO (LÓGICA)
# ==========================================

def clean_data(df):
    """Normalización de columnas y limpieza de tipos de datos."""
    # 1. Normalizar nombres de columnas (strip, lower, quitar puntos/acentos básicos)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('.', '', regex=False).str.replace('°', '')
    
    # 2. Mapeo de columnas críticas
    mapping = {
        'n_de_serie': 'serie',
        'ultima_visita': 'fecha',
        'tecnico': 'tecnico',
        'categoria': 'categoria',
        'estatus': 'estatus',
        'problema_reportado': 'problema'
    }
    df = df.rename(columns=mapping)
    
    # Validar columnas mínimas requeridas
    required = ['serie', 'fecha', 'tecnico', 'categoria', 'estatus']
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Faltan columnas críticas en el archivo: {missing}")
        return None

    # 3. Limpieza de tipos
    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df = df.dropna(subset=['serie', 'fecha'])
    
    # 4. Estandarizar texto
    df['tecnico'] = df['tecnico'].astype(str).str.upper().str.strip()
    df['categoria'] = df['categoria'].astype(str).str.upper().str.strip()
    df['estatus'] = df['estatus'].astype(str).str.upper().str.strip()
    df['problema'] = df['problema'].astype(str).str.upper().fill_na("SIN REPORTE")
    
    return df

def apply_filters(df, selected_date, lookback_months):
    """Aplica ventana temporal dinámica."""
    end_date = pd.to_datetime(selected_date) + pd.offsets.MonthEnd(0)
    start_date = pd.to_datetime(selected_date) - pd.DateOffset(months=lookback_months)
    
    mask = (df['fecha'] >= start_date) & (df['fecha'] <= end_date)
    return df.loc[mask].sort_values(by=['serie', 'fecha'])

def calculate_penalties(df):
    """Lógica de reincidencias: Solo penaliza historial previo en CORRECTIVO."""
    df = df.sort_values(['serie', 'fecha'])
    # Identificar la última visita por serie
    df['es_ultima'] = df.groupby('serie')['fecha'].transform('max') == df['fecha']
    
    # Penalización: Si es CORRECTIVO y NO es la última intervención de ese equipo en el periodo
    df['penalizable'] = (df['categoria'] == 'CORRECTIVO') & (~df['es_ultima'])
    return df

# ==========================================
# SIDEBAR / CONFIGURACIÓN
# ==========================================
with st.sidebar:
    st.title("⚙️ Panel de Control")
    uploaded_file = st.file_uploader("Cargar Reporte (Excel)", type=["xlsx", "xls"])
    
    st.divider()
    
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        mes = st.selectbox("Mes de Análisis", range(1, 13), index=datetime.now().month - 1)
    with col_date2:
        anio = st.number_input("Año", value=2024)
    
    lookback = st.slider("Meses de historial (reincidencias)", 1, 12, 3)
    
    st.subheader("💰 Valores por Categoría")
    config_data = pd.DataFrame({
        "Categoria": ["CORRECTIVO", "PREVENTIVO", "INSTALACION", "OTROS"],
        "Valor_Puntos": [1.0, 1.5, 2.0, 0.5]
    })
    editable_config = st.data_editor(config_data, num_rows="dynamic", use_container_width=True)

# ==========================================
# CUERPO PRINCIPAL
# ==========================================
st.title("📊 Dashboard de Rendimiento Técnico")

if uploaded_file:
    try:
        raw_df = pd.read_excel(uploaded_file)
        df = clean_data(raw_df)
        
        if df is not None:
            # Procesamiento
            selected_period = datetime(anio, mes, 1)
            df_filtered = apply_filters(df, selected_period, lookback)
            df_processed = calculate_penalties(df_filtered)
            
            # Pestañas
            t1, t2, t3, t4, t5 = st.tabs([
                "🏆 Resultados Finales", 
                "⚠️ Top Fallas", 
                "📉 Penalizaciones", 
                "📋 Asignaciones", 
                "⚙️ Config"
            ])

            # --- PESTAÑA 1: RESULTADOS ---
            with t1:
                st.subheader(f"Resumen de Desempeño - {selected_period.strftime('%B %Y')}")
                
                # Agrupación por técnico
                resueltas = df_processed[df_processed['estatus'] == 'RESUELTA'].groupby('tecnico').size().rename('resueltas')
                penalizaciones = df_processed[df_processed['penalizable']].groupby('tecnico').size().rename('penalizaciones')
                
                resumen = pd.merge(resueltas, penalizaciones, on='tecnico', how='left').fillna(0)
                
                # Unir con valores de configuración para el Score Total
                # (Simplificado: Resueltas * 1 - Penalizaciones * Factor)
                resumen['Total_Score'] = resumen['resueltas'] - resumen['penalizaciones']
                
                st.dataframe(resumen.sort_values(by='Total_Score', ascending=False), use_container_width=True)
                
                fig_res = px.bar(resumen.reset_index(), x='tecnico', y=['resueltas', 'penalizaciones'], 
                                 title="Actividad vs Penalizaciones", barmode='group')
                st.plotly_chart(fig_res, use_container_width=True)

            # --- PESTAÑA 2: TOP FALLAS ---
            with t2:
                st.subheader("Análisis de Fallas Recurrentes")
                top_fallas = df_processed['problema'].value_counts().reset_index()
                top_fallas.columns = ['Problema', 'Frecuencia']
                
                col_f1, col_f2 = st.columns([1, 2])
                with col_f1:
                    st.dataframe(top_fallas, use_container_width=True)
                with col_f2:
                    fig_fallas = px.pie(top_fallas.head(10), values='Frecuencia', names='Problema', hole=0.4)
                    st.plotly_chart(fig_fallas, use_container_width=True)

            # --- PESTAÑA 3: PENALIZACIONES ---
            with t3:
                st.subheader("Detalle de Reincidencias (Correctivos)")
                df_pen = df_processed[df_processed['penalizable']]
                st.write("Se consideran penalizaciones las visitas a equipos 'CORRECTIVOS' que ya habían sido visitados en el periodo de ventana.")
                st.dataframe(df_pen[['tecnico', 'serie', 'fecha', 'problema']], use_container_width=True)
                
                if not df_pen.empty:
                    csv = df_pen.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Descargar Reporte Penalizaciones", csv, "penalizaciones.csv", "text/csv")

            # --- PESTAÑA 4: ASIGNACIONES ESPECIALES ---
            with t4:
                st.subheader("Actividades No Correctivas")
                especiales = df_processed[df_processed['categoria'] != 'CORRECTIVO']
                st.table(especiales[['tecnico', 'categoria', 'fecha', 'estatus']].head(20))

            # --- PESTAÑA 5: CONFIGURACIÓN ---
            with t5:
                st.info("La configuración de pesos afecta el cálculo de la pestaña 'Resultados Finales'.")
                st.write("Categorías detectadas en el archivo:")
                st.write(df['categoria'].unique())

    except Exception as e:
        st.error(f"Error procesando el archivo: {str(e)}")
else:
    st.info("👋 Por favor, carga un archivo Excel en la barra lateral para comenzar.")
    st.markdown("""
    ### Requisitos del Formato:
    - **N.° de serie**: Identificador del equipo.
    - **Última visita**: Fecha (DD/MM/YYYY).
    - **Técnico**: Nombre del responsable.
    - **Categoría**: (Ej: CORRECTIVO, PREVENTIVO).
    - **Estatus**: (Ej: RESUELTA, PENDIENTE).
    """)

# Conclusión del flujo
if uploaded_file:
    st.divider()
    st.caption(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
