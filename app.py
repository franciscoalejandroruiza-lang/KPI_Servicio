import streamlit as st
import pandas as pd

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SenAudit Pro - Auditoría Agrupada", layout="wide")

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

st.title("📊 SenAudit Pro - Auditoría Agrupada por Técnico")

# --- CONFIGURACIÓN LATERAL ---
st.sidebar.header("⚙️ Configuración")
archivo = st.sidebar.file_uploader("Cargar Reporte (Excel/CSV)", type=["xlsx", "csv"])
meses_atras = st.sidebar.slider("Meses de historial a considerar", 1, 12, 3)

if archivo:
    # 2. CARGA Y NORMALIZACIÓN
    df = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
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

    # --- MOTOR DE AUDITORÍA: BARRIDO DE HISTORIAL ---
    df_mes_actual = df[df['Mes_Año'] == periodo_sel].copy()
    lista_penalizaciones = []

    for _, fila_actual in df_mes_actual.iterrows():
        limite_h = fila_actual['Fecha recepción'] - pd.DateOffset(months=meses_atras)
        
        historial = df[
            (df['Serie'] == fila_actual['Serie']) & 
            (df['Fecha recepción'] < fila_actual['Fecha recepción']) &
            (df['Fecha recepción'] >= limite_h)
        ].sort_values('Fecha recepción', ascending=False)
        
        if not historial.empty:
            # Barrido de todas las fallas previas (Correctivos y Reincidencias)
            reincidencias_previas = historial[historial['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])]
            
            for _, fila_penalizada in reincidencias_previas.iterrows():
                if fila_penalizada['Técnico'] != fila_actual['Técnico']:
                    lista_penalizaciones.append({
                        'Técnico Penalizado': fila_penalizada['Técnico'],
                        'Serie': fila_actual['Serie'],
                        'Folio de su Falla': fila_penalizada['Folio'],
                        'Fecha de su Falla': fila_penalizada['Fecha recepción'].strftime('%d/%m/%Y'),
                        'Detonado por Folio': fila_actual['Folio'],
                        'Fecha del Detonante': fila_actual['Fecha recepción'].strftime('%d/%m/%Y'),
                        'Puntos': 1.0
                    })

    df_pen = pd.DataFrame(lista_penalizaciones)
    if not df_pen.empty:
        df_pen = df_pen.drop_duplicates(subset=['Técnico Penalizado', 'Folio de su Falla', 'Detonado por Folio'])

    # --- PESTAÑAS ---
    tab_puntos, tab_auditoria = st.tabs(["📈 Puntaje Final", "📋 Auditoría Agrupada"])

    with tab_puntos:
        resumen = df_mes_actual[df_mes_actual['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Visitas_Mes')
        resumen['Pts_Positivos'] = resumen['Visitas_Mes'] * 1.0
        
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico Penalizado')['Puntos'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen_final = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0
            resumen_final = resumen

        resumen_final['TOTAL'] = resumen_final['Pts_Positivos'] - resumen_final['Penalización']
        st.dataframe(resumen_final.sort_values('TOTAL', ascending=False), use_container_width=True)

    with tab_auditoria:
        if not df_pen.empty:
            st.subheader(f"Desglose de Penalizaciones - {periodo_sel}")
            
            # Agrupamos por técnico para crear las secciones
            tecnicos_con_falla = sorted(df_pen['Técnico Penalizado'].unique())
            
            for tec in tecnicos_con_falla:
                datos_tec = df_pen[df_pen['Técnico Penalizado'] == tec]
                num_fallas = len(datos_tec)
                
                # Usamos un expander para cada técnico
                with st.expander(f"👤 {tec} — TOTAL: -{num_fallas} Puntos"):
                    st.write(f"A continuación se detallan los folios de {tec} que resultaron en reincidencia:")
                    # Mostramos la tabla específica de este técnico
                    st.table(datos_tec[['Serie', 'Folio de su Falla', 'Fecha de su Falla', 'Detonado por Folio', 'Fecha del Detonante']])
        else:
            st.success("No se detectaron reincidencias para agrupar.")

else:
    st.info("Sube el archivo para generar la auditoría agrupada.")
