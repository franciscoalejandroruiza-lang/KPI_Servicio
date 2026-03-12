import streamlit as st
import pandas as pd

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SenAudit Pro - Auditoría de Reincidencias Múltiples", layout="wide")

# --- BLOQUE DE SEGURIDAD ---
if "legal_accepted" not in st.session_state:
    @st.dialog("Aviso de Confidencialidad")
    def aviso():
        st.warning("⚠️ ACCESO RESTRINGIDO")
        st.write("Propiedad Intelectual Privada de Alejandro Ruiz.")
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

st.title("📊 SenAudit Pro - Reporte de Cadena de Fallas")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuración")
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])
meses_atras_config = st.sidebar.slider("Meses de historial a rastrear", 1, 12, 3)

if archivo_subido:
    # CARGA Y LIMPIEZA
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # NORMALIZACIÓN
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    df['Serie'] = df['Serie'].astype(str).str.strip().str.lstrip('0')
    df['Técnico'] = df['Técnico'].astype(str).str.replace('CH ', '', regex=False).str.replace('CHI ', '', regex=False).str.strip().str.upper()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()

    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)
    periodo_sel = st.sidebar.selectbox("📅 Seleccionar Mes a Evaluar:", df['Mes_Año'].unique())

    # --- MOTOR DE PENALIZACIÓN POR CADENA ---
    # Evaluamos todo el historial para no perder registros
    df_evaluado = df[df['Mes_Año'] == periodo_sel].copy()
    
    lista_penalizaciones = []
    series_ya_castigadas_por_tecnico = set() # (Técnico, Serie) para el puntaje neto

    # Filtramos por los que reportan falla: CORRECTIVO y REINCIDENCIA
    detonantes = df_evaluado[df_evaluado['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])].sort_values('Fecha recepción')

    for _, fila_det in detonantes.iterrows():
        # Límite de tiempo dinámico según slider
        limite_hist = fila_det['Fecha recepción'] - pd.DateOffset(months=meses_atras_config)
        
        # Buscamos quién estuvo antes de ESTE folio específico
        historial = df[
            (df['Serie'] == fila_det['Serie']) & 
            (df['Fecha recepción'] < fila_det['Fecha recepción']) & 
            (df['Fecha recepción'] >= limite_hist)
        ].sort_values('Fecha recepción', ascending=False)
        
        if not historial.empty:
            # Tomamos al técnico inmediato anterior
            ultima_visita = historial.iloc[0]
            tec_previo = ultima_visita['Técnico']
            
            if tec_previo != fila_det['Técnico']:
                # Lógica de puntos: Solo descontamos 1 vez por serie al mes para el TOTAL
                descontar = 0
                if (tec_previo, fila_det['Serie']) not in series_ya_castigadas_por_tecnico:
                    descontar = 1.0
                    series_ya_castigadas_por_tecnico.add((tec_previo, fila_det['Serie']))
                
                lista_penalizaciones.append({
                    'Técnico Penalizado': tec_previo,
                    'Serie': fila_det['Serie'],
                    'Folio Su Visita': ultima_visita['Folio'],
                    'Fecha Su Visita': ultima_visita['Fecha recepción'].strftime('%d/%m/%y %H:%M'),
                    'Folio Detonante (Falla)': fila_det['Folio'],
                    'Fecha de Falla': fila_det['Fecha recepción'].strftime('%d/%m/%y %H:%M'),
                    'Categoría Falla': fila_det['Categoría'],
                    'Resta Punto': descontar
                })

    df_pen = pd.DataFrame(lista_penalizaciones)

    # --- PESTAÑAS ---
    t_resumen, t_auditoria = st.tabs(["📈 Resumen de Puntos", "📋 Auditoría de Cadena"])

    with t_resumen:
        df_resueltas = df_evaluado[df_evaluado['Estatus'] == 'RESUELTA'].copy()
        resumen = df_resueltas.groupby('Técnico').size().reset_index(name='Visitas')
        resumen['Pts_Positivos'] = resumen['Visitas'] * 1.0
        
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico Penalizado')['Resta Punto'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0

        resumen['TOTAL'] = resumen['Pts_Positivos'] - resumen['Penalización']
        st.dataframe(resumen.sort_values('TOTAL', ascending=False), use_container_width=True)

    with t_auditoria:
        st.header(f"Desglose Completo de Reincidencias - {periodo_sel}")
        if not df_pen.empty:
            for tec in sorted(df_pen['Técnico Penalizado'].unique()):
                datos = df_pen[df_pen['Técnico Penalizado'] == tec]
                with st.expander(f"👤 {tec} — Penalizaciones Totales Aplicadas: -{datos['Resta Punto'].sum()}"):
                    st.table(datos)
        else:
            st.success("No se detectaron reincidencias.")
else:
    st.info("Suba el reporte para iniciar.")
