import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# ==========================================
# CONFIGURACIÓN Y ESTILO
# ==========================================
st.set_page_config(page_title="Analizador Técnico Pro", layout="wide")

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# ==========================================
# LÓGICA DE PROCESAMIENTO (REGLA DE ÚLTIMO TÉCNICO)
# ==========================================

def clean_data(df):
    """Limpieza de columnas reales y normalización."""
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
    
    # Validar columnas esenciales
    cols_necesarias = ['serie', 'fecha', 'tecnico', 'categoria', 'estatus']
    if not all(col in df.columns for col in cols_necesarias):
        st.error("⚠️ Estructura de archivo no válida. Verifique los nombres de las columnas.")
        return None

    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    df = df.dropna(subset=['serie', 'fecha'])
    
    # Estandarizar nombres de técnicos y categorías
    for col in ['tecnico', 'categoria', 'estatus']:
        df[col] = df[col].astype(str).str.upper().str.strip()
    
    return df

def procesar_rendimiento(df, mes_sel, anio_sel, ventana):
    """Lógica: Penaliza intervenciones correctivas que NO fueron las últimas."""
    fecha_fin = datetime(anio_sel, mes_sel, 1) + pd.offsets.MonthEnd(0)
    fecha_inicio = datetime(anio_sel, mes_sel, 1) - pd.DateOffset(months=ventana)
    
    # Filtro de ventana de tiempo
    mask = (df['fecha'] >= fecha_inicio) & (df['fecha'] <= fecha_fin)
    universo = df.loc[mask].sort_values(by=['serie', 'fecha'])

    # Identificar la última visita absoluta de cada equipo
    universo['ultima_fecha_equipo'] = universo.groupby('serie')['fecha'].transform('max')
    
    # REGLA CRÍTICA: 
    # Es penalización si la categoría es CORRECTIVO Y la fecha es MENOR a la última visita.
    # Esto libera de culpa al técnico que cerró el ciclo.
    universo['es_penalizacion'] = (
        (universo['categoria'] == 'CORRECTIVO') & 
        (universo['fecha'] < universo['ultima_fecha_equipo'])
    )

    # Filtrar solo el mes solicitado para el reporte final
    reporte_mes = universo[universo['fecha'].dt.month == mes_sel].copy()
    return reporte_mes

# ==========================================
# INTERFAZ DE USUARIO
# ==========================================
with st.sidebar:
    st.header("📂 Datos de Entrada")
    uploaded_file = st.file_uploader("Subir Reporte (Excel o CSV)", type=["xlsx", "csv"])
    
    st.divider()
    mes_nombre = st.selectbox("Mes a evaluar", list(MESES_ES.values()), index=datetime.now().month - 1)
    mes_num = [k for k, v in MESES_ES.items() if v == mes_nombre][0]
    anio_num = st.number_input("Año", value=2025)
    
    st.divider()
    st.subheader("⚙️ Parámetros")
    ventana = st.slider("Meses de historial para reincidencias", 1, 6, 2)
    
    st.info("💡 La app penalizará a todo técnico cuya visita correctiva no haya sido la definitiva para el equipo.")

# ==========================================
# DASHBOARD
# ==========================================
st.title(f"📈 Análisis de Desempeño: {mes_nombre} {anio_num}")

if uploaded_file:
    # Carga de datos
    if uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)
        
    df_clean = clean_data(df_raw)
    
    if df_clean is not None:
        df_final = procesar_rendimiento(df_clean, mes_num, anio_num, ventana)
        
        tab1, tab2, tab3, tab4 = st.tabs(["🏆 Resultados", "📉 Penalizaciones", "🔍 Top Fallas", "⚙️ Configuración"])

        with tab1:
            # Cálculos agrupados
            resueltas = df_final[df_final['estatus'] == 'RESUELTA'].groupby('tecnico').size().rename('Resueltas')
            pens = df_final[df_final['es_penalizacion']].groupby('tecnico').size().rename('Penalizaciones')
            
            resumen = pd.concat([resueltas, pens], axis=1).fillna(0).astype(int)
            resumen['TOTAL PUNTOS'] = resumen['Resueltas'] - resumen['Penalizaciones']
            resumen = resumen.sort_values(by='TOTAL PUNTOS', ascending=False)
            
            st.subheader("Resumen de Puntaje")
            st.dataframe(resumen, use_container_width=True)
            
            # Gráfica
            fig = px.bar(resumen.reset_index(), x='tecnico', y=['Resueltas', 'Penalizaciones'],
                         barmode='group', title="Productividad vs Reincidencias",
                         color_discrete_map={'Resueltas': '#28a745', 'Penalizaciones': '#dc3545'})
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("Detalle de Intervenciones Penalizadas")
            df_pen = df_final[df_final['es_penalizacion']].copy()
            
            if not df_pen.empty:
                st.write("Estas visitas fueron seguidas por otra intervención, indicando que la falla persistió:")
                st.dataframe(df_pen[['fecha', 'serie', 'tecnico', 'problema', 'categoria']], use_container_width=True)
                
                # Exportar Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_pen.to_excel(writer, index=False, sheet_name='Penalizaciones')
                st.download_button(
                    label="📥 Descargar Reporte de Penalizaciones (Excel)",
                    data=output.getvalue(),
                    file_name=f"penalizaciones_{mes_nombre}_{anio_num}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.success("No se detectaron penalizaciones en este periodo.")

        with tab3:
            st.subheader("Análisis de Fallas más Comunes")
            fallas = df_final['problema'].value_counts().reset_index()
            fallas.columns = ['Problema', 'Frecuencia']
            st.bar_chart(fallas.head(10), x='Problema', y='Frecuencia')

        with tab4:
            st.subheader("Configuración de Categorías")
            st.write("Categorías encontradas en el archivo:")
            st.write(list(df_final['categoria'].unique()))
            st.info("Solo las categorías marcadas como 'CORRECTIVO' son sujetas a penalización por reincidencia.")

else:
    st.info("👋 Por favor, carga el archivo de reporte técnico para iniciar el análisis automático.")
