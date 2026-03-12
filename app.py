import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SenAudit Pro - Auditoría Dinámica", layout="wide")

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

# --- INICIALIZACIÓN ---
if 'lista_extras' not in st.session_state: st.session_state.lista_extras = []
if 'pesos_dict' not in st.session_state: st.session_state.pesos_dict = {}

MESES_MAP = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}

st.title("📊 SenAudit Pro - Gestión de Manufactura")

# --- BARRA LATERAL (CONFIGURACIÓN DE REINCIDENCIA) ---
st.sidebar.header("⚙️ Parámetros de Análisis")
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])

# Slider para configurar meses atrás (Default: 3)
meses_atras = st.sidebar.slider(
    "Meses de rastreo de reincidencia", 
    min_value=1, 
    max_value=12, 
    value=3,
    help="Define qué tan atrás en el tiempo buscaremos al técnico responsable de una serie."
)

if archivo_subido:
    # CARGA Y LIMPIEZA
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # Normalización de Nombres (CH IVAN CANO NUNEZ -> IVAN CANO NUNEZ)
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    df['Serie'] = df['Serie'].astype(str).str.strip().str.lstrip('0')
    df['Técnico'] = df['Técnico'].astype(str).str.replace('CH ', '', regex=False).str.replace('CHI ', '', regex=False).str.strip().str.upper()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()

    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)
    periodos = df.sort_values('Fecha recepción', ascending=False)['Mes_Año'].unique()
    periodo_sel = st.sidebar.selectbox("📅 Periodo a Evaluar:", periodos)

    # --- MOTOR DE PENALIZACIÓN ---
    df_actual = df[df['Mes_Año'] == periodo_sel].copy()
    
    # Definir el límite temporal basado en el slider
    fecha_inicio_periodo = df_actual['Fecha recepción'].min()
    fecha_limite_historial = fecha_inicio_periodo - pd.DateOffset(months=meses_atras)
    
    lista_penalizaciones = []
    penalizados_por_serie = set()

    # Filtramos correctivos detonantes
    df_detonantes = df_actual[df_actual['Categoría'] == 'CORRECTIVO'].copy()

    for _, fila_det in df_detonantes.iterrows():
        # Buscamos en el historial (según los meses configurados)
        historial = df[
            (df['Serie'] == fila_det['Serie']) & 
            (df['Fecha recepción'] < fila_det['Fecha recepción']) &
            (df['Fecha recepción'] >= fecha_limite_historial)
        ].sort_values('Fecha recepción', ascending=False)
        
        if not historial.empty:
            for _, fila_visita in historial.iterrows():
                tec_culpable = fila_visita['Técnico']
                
                # Regla: No se penaliza a sí mismo y solo una vez por serie
                if tec_culpable != fila_det['Técnico'] and (tec_culpable, fila_det['Serie']) not in penalizados_por_serie:
                    lista_penalizaciones.append({
                        'Técnico': tec_culpable,
                        'Serie': fila_det['Serie'],
                        'Folio de Visita': fila_visita['Folio'],
                        'Fecha de Visita': fila_visita['Fecha recepción'].strftime('%Y-%m-%d'),
                        'Folio Detonante': fila_det['Folio'],
                        'Fecha de Falla': fila_det['Fecha recepción'].strftime('%Y-%m-%d'),
                        'Descuento': 1.0
                    })
                    penalizados_por_serie.add((tec_culpable, fila_det['Serie']))

    df_pen = pd.DataFrame(lista_penalizaciones)

    # --- PESTAÑAS ---
    t_resumen, t_detallado, t_config = st.tabs(["📈 Puntaje Final", "⚠️ Detalle por Técnico", "⚙️ Pesos"])

    with t_config:
        st.header("Pesos de Categoría")
        for cat in sorted(df['Categoría'].unique()):
            st.session_state.pesos_dict[cat] = st.slider(f"Puntos: {cat}", -5.0, 10.0, st.session_state.pesos_dict.get(cat, 1.0), 0.5)

    with t_resumen:
        df_resueltas = df_actual[df_actual['Estatus'] == 'RESUELTA'].copy()
        df_resueltas['Pts_Ganados'] = df_resueltas['Categoría'].map(st.session_state.pesos_dict).fillna(0.0)
        resumen = df_resueltas.groupby('Técnico')['Pts_Ganados'].sum().reset_index()
        
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico')['Descuento'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0

        resumen['TOTAL'] = resumen['Pts_Ganados'] - resumen['Penalización']
        st.dataframe(resumen.sort_values('TOTAL', ascending=False), use_container_width=True)

    with t_detallado:
        st.header(f"Desglose de Reincidencias (Rastreo: {meses_atras} meses)")
        if not df_pen.empty:
            for tec in sorted(df_pen['Técnico'].unique()):
                detalle = df_pen[df_pen['Técnico'] == tec]
                with st.expander(f"👤 {tec} (Descuento: -{detalle['Descuento'].sum()})"):
                    st.table(detalle[['Serie', 'Folio de Visita', 'Fecha de Visita', 'Folio Detonante', 'Fecha de Falla']])
        else:
            st.success("No se encontraron reincidencias con los parámetros actuales.")

else:
    st.info("Sube el reporte para iniciar el análisis.")
