import streamlit as st
import pandas as pd
from datetime import timedelta

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SenAudit Pro - Auditoría Dinámica", layout="wide")

# --- BLOQUE DE SEGURIDAD ---
if "legal_accepted" not in st.session_state:
    @st.dialog("Aviso de Privacidad")
    def aviso():
        st.warning("⚠️ ACCESO RESTRINGIDO")
        st.write("Propiedad de Alejandro Ruiz. Análisis de KPIs y Reincidencias.")
        if st.button("Acepto los Términos"):
            st.session_state.legal_accepted = True
            st.rerun()
    aviso()
    st.stop()

# --- MAPEO DE MESES ---
MESES_MAP = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}

st.title("📊 SenAudit Pro - Control de Historial Activo")

# --- CONFIGURACIÓN LATERAL (UI solicitada) ---
st.sidebar.header("⚙️ Configuración")
archivo = st.sidebar.file_uploader("Cargar Reporte (Excel/CSV)", type=["xlsx", "csv"])

# Slider funcional: Define qué tan atrás buscamos "goles" o fallas
meses_h = st.sidebar.slider("Meses de historial a considerar", 1, 12, 3)

if archivo:
    # 2. CARGA Y LIMPIEZA
    df = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # Normalización
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    df['Serie'] = df['Serie'].astype(str).str.strip().str.lstrip('0')
    df['Técnico'] = df['Técnico'].astype(str).str.replace('CH ', '', regex=False).str.replace('CHI ', '', regex=False).str.strip().str.upper()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()

    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)
    df = df.sort_values('Fecha recepción')
    
    periodo_sel = st.sidebar.selectbox("📅 Mes a Evaluar:", df['Mes_Año'].unique()[::-1])

    # --- MOTOR DE AUDITORÍA CON HISTORIAL DINÁMICO ---
    df_mes_actual = df[df['Mes_Año'] == periodo_sel].copy()
    lista_penalizaciones = []

    for _, fila_actual in df_mes_actual.iterrows():
        # LÓGICA DEL SLIDER: Calculamos la fecha límite restando meses
        # Usamos 30 días por mes para una aproximación precisa del historial
        fecha_limite = fila_actual['Fecha recepción'] - timedelta(days=meses_h * 30)
        
        # Buscamos historial de la serie en ese rango
        historial = df[
            (df['Serie'] == fila_actual['Serie']) & 
            (df['Fecha recepción'] < fila_actual['Fecha recepción']) &
            (df['Fecha recepción'] >= fecha_limite)
        ].sort_values('Fecha recepción', ascending=False)
        
        if not historial.empty:
            # Barrido: Todas las fallas previas (CORRECTIVO/REINCIDENCIA) son penalizables
            reincidencias = historial[historial['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])]
            
            for _, fila_pen in reincidencias.iterrows():
                if fila_pen['Técnico'] != fila_actual['Técnico']:
                    lista_penalizaciones.append({
                        'Técnico Penalizado': fila_pen['Técnico'],
                        'Serie': fila_actual['Serie'],
                        'Folio de su Falla': fila_pen['Folio'],
                        'Fecha de su Falla': fila_pen['Fecha recepción'].strftime('%d/%m/%Y'),
                        'Detonado por Folio': fila_actual['Folio'],
                        'Fecha del Detonante': fila_actual['Fecha recepción'].strftime('%d/%m/%Y'),
                        'Puntos': 1.0
                    })

    df_pen = pd.DataFrame(lista_penalizaciones)
    if not df_pen.empty:
        df_pen = df_pen.drop_duplicates(subset=['Técnico Penalizado', 'Folio de su Falla', 'Detonado por Folio'])

    # --- VISUALIZACIÓN ---
    tab_resumen, tab_auditoria = st.tabs(["📈 Puntaje Final", "📋 Auditoría Agrupada"])

    with tab_resumen:
        # Puntos positivos
        resumen = df_mes_actual[df_mes_actual['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Servicios')
        resumen['Pts_Ganados'] = resumen['Servicios'] * 1.0
        
        # Restar penalizaciones
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico Penalizado')['Puntos'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0

        resumen['TOTAL'] = resumen['Pts_Ganados'] - resumen['Penalización']
        st.dataframe(resumen.sort_values('TOTAL', ascending=False), use_container_width=True)

    with tab_auditoria:
        if not df_pen.empty:
            tecnicos = sorted(df_pen['Técnico Penalizado'].unique())
            for tec in tecnicos:
                datos_tec = df_pen[df_pen['Técnico Penalizado'] == tec]
                with st.expander(f"👤 {tec} — Penalizaciones Totales: -{len(datos_tec)}"):
                    st.table(datos_tec[['Serie', 'Folio de su Falla', 'Fecha de su Falla', 'Detonado por Folio']])
        else:
            st.info(f"No hay reincidencias en los últimos {meses_h} meses para este periodo.")

else:
    st.info("Sube el archivo para activar el análisis de historial.")
