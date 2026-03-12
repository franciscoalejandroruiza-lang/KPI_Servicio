import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SenAudit Pro - Auditoría Avanzada", layout="wide")

# --- SEGURIDAD ---
if "legal_accepted" not in st.session_state:
    @st.dialog("Aviso de Confidencialidad")
    def aviso():
        st.warning("⚠️ ACCESO RESTRINGIDO")
        st.write("Propiedad Intelectual Privada de Alejandro Ruiz. El uso de este software es para personal autorizado.")
        if st.button("Acepto los Términos"):
            st.session_state.legal_accepted = True
            st.rerun()
    aviso()
    st.stop()

# --- CONSTANTES ---
MESES_MAP = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}

st.title("📊 SenAudit Pro - Gestión de Manufactura")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuración de Análisis")
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])

# Configuración dinámica del rango de búsqueda
meses_historial = st.sidebar.slider(
    "Meses de historial para reincidencia", 
    min_value=1, 
    max_value=12, 
    value=3,
    help="Define cuántos meses atrás buscaremos al técnico responsable original."
)

if archivo_subido:
    # CARGA Y LIMPIEZA PROFUNDA
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # 1. Normalización de Series (eliminar ceros iniciales para match perfecto)
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    df['Serie'] = df['Serie'].astype(str).str.strip().str.lstrip('0')
    
    # 2. Normalización de Nombres (limpiar CH, CHI y espacios)
    df['Técnico'] = df['Técnico'].astype(str).str.replace('CH ', '', regex=False).str.replace('CHI ', '', regex=False).str.strip().str.upper()
    
    # 3. Fechas y Categorías
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()

    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)
    periodos = df.sort_values('Fecha recepción', ascending=False)['Mes_Año'].unique()
    periodo_sel = st.sidebar.selectbox("📅 Mes a Evaluar:", periodos)

    # --- MOTOR DE CÁLCULO DINÁMICO ---
    df_actual = df[df['Mes_Año'] == periodo_sel].copy()
    
    # Definimos la ventana de tiempo basada en la configuración del slider
    inicio_mes_evaluado = df_actual['Fecha recepción'].min()
    limite_historial = inicio_mes_evaluado - pd.DateOffset(months=meses_historial)
    
    lista_penalizaciones = []
    penalizados_por_serie = set() # (Técnico, Serie) para evitar duplicados en el mismo mes

    # Analizamos solo los CORRECTIVOS del mes seleccionado
    df_detonantes = df_actual[df_actual['Categoría'] == 'CORRECTIVO'].copy()

    for _, fila_det in df_detonantes.iterrows():
        # Buscamos en el historial global pero limitado por el slider de meses
        historial_busqueda = df[
            (df['Serie'] == fila_det['Serie']) & 
            (df['Fecha recepción'] < fila_det['Fecha recepción']) &
            (df['Fecha recepción'] >= limite_historial)
        ].sort_values('Fecha recepción', ascending=False)
        
        if not historial_busqueda.empty:
            for _, fila_visita in historial_busqueda.iterrows():
                tec_pasado = fila_visita['Técnico']
                
                # Regla: No se penaliza a sí mismo y solo un -1 por equipo al mes
                if tec_pasado != fila_det['Técnico'] and (tec_pasado, fila_det['Serie']) not in penalizados_por_serie:
                    lista_penalizaciones.append({
                        'Técnico': tec_pasado,
                        'Serie': fila_det['Serie'],
                        'Folio Visita Original': fila_visita['Folio'],
                        'Fecha Visita': fila_visita['Fecha recepción'].strftime('%d/%m/%y'),
                        'Folio Detonante (Falla)': fila_det['Folio'],
                        'Fecha de Falla': fila_det['Fecha recepción'].strftime('%d/%m/%y'),
                        'Puntos': 1.0
                    })
                    penalizados_por_serie.add((tec_pasado, fila_det['Serie']))

    df_pen = pd.DataFrame(lista_penalizaciones)

    # --- PESTAÑAS DE VISUALIZACIÓN ---
    t_resumen, t_agrupado, t_config = st.tabs(["📈 Puntaje Final", "⚠️ Detalle por Técnico", "⚙️ Pesos"])

    with t_config:
        st.header("Configuración de Puntuación")
        if 'pesos_dict' not in st.session_state: st.session_state.pesos_dict = {}
        for cat in sorted(df['Categoría'].unique()):
            st.session_state.pesos_dict[cat] = st.slider(f"Valor: {cat}", -2.0, 5.0, 1.0, 0.5)

    with t_resumen:
        # Puntos por servicios resueltos
        df_ok = df_actual[df_actual['Estatus'] == 'RESUELTA'].copy()
        df_ok['Pts'] = df_ok['Categoría'].map(st.session_state.pesos_dict).fillna(0.0)
        resumen = df_ok.groupby('Técnico')['Pts'].sum().reset_index(name='Pts_Ganados')
        
        # Restar penalizaciones
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico')['Puntos'].sum().reset_index(name='Penalización')
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0

        resumen['TOTAL'] = resumen['Pts_Ganados'] - resumen['Penalización']
        st.subheader(f"Clasificación Final - {periodo_sel}")
        st.dataframe(resumen.sort_values('TOTAL', ascending=False), use_container_width=True)

    with t_agrupado:
        st.header(f"Análisis de Reincidencias (Ventana: {meses_historial} meses)")
        if not df_pen.empty:
            for tec in sorted(df_pen['Técnico'].unique()):
                datos_tec = df_pen[df_pen['Técnico'] == tec]
                with st.expander(f"👤 {tec} — Total Penalizaciones: -{datos_tec['Puntos'].sum()}"):
                    st.table(datos_tec[['Serie', 'Folio Visita Original', 'Fecha Visita', 'Folio Detonante (Falla)', 'Fecha de Falla']])
        else:
            st.success(f"No hay reincidencias detectadas en los últimos {meses_historial} meses para este periodo.")

else:
    st.info("Sube el archivo para procesar la auditoría.")
