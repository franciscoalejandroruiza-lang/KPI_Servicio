import streamlit as st
import pandas as pd

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SenAudit Pro - Auditoría Exhaustiva", layout="wide")

# --- SEGURIDAD ---
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

st.title("📊 SenAudit Pro - Análisis de Reincidencias Acumuladas")

# --- CONFIGURACIÓN ---
st.sidebar.header("⚙️ Parámetros de Auditoría")
archivo = st.sidebar.file_uploader("Cargar Reporte (Excel/CSV)", type=["xlsx", "csv"])
meses_atras = st.sidebar.slider("Meses de historial a considerar", 1, 12, 3)

if archivo:
    # 2. CARGA Y LIMPIEZA TOTAL
    df = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # Normalización de Nombres y Series
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    df['Serie'] = df['Serie'].astype(str).str.strip().str.lstrip('0')
    df['Técnico'] = df['Técnico'].astype(str).str.replace('CH ', '', regex=False).str.replace('CHI ', '', regex=False).str.strip().str.upper()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()

    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)
    
    # Ordenar por fecha para análisis cronológico
    df = df.sort_values('Fecha recepción')
    
    periodo_sel = st.sidebar.selectbox("📅 Mes a Evaluar (Puntaje):", df['Mes_Año'].unique()[::-1])

    # --- MOTOR DE AUDITORÍA: BARRIDO DE HISTORIAL ---
    df_mes_actual = df[df['Mes_Año'] == periodo_sel].copy()
    lista_penalizaciones = []

    # Analizamos cada registro del mes seleccionado
    for _, fila_actual in df_mes_actual.iterrows():
        # Definimos el límite de búsqueda hacia atrás
        limite_h = fila_actual['Fecha recepción'] - pd.DateOffset(months=meses_atras)
        
        # Buscamos TODO el historial de esa serie antes de la visita actual
        historial = df[
            (df['Serie'] == fila_actual['Serie']) & 
            (df['Fecha recepción'] < fila_actual['Fecha recepción']) &
            (df['Fecha recepción'] >= limite_h)
        ].sort_values('Fecha recepción', ascending=False)
        
        if not historial.empty:
            # Filtramos en el historial solo CORRECTIVOS y REINCIDENCIAS 
            # que ocurrieron antes de que el técnico actual fuera
            reincidencias_previas = historial[historial['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])]
            
            for _, fila_penalizada in reincidencias_previas.iterrows():
                # No se penaliza a sí mismo
                if fila_penalizada['Técnico'] != fila_actual['Técnico']:
                    lista_penalizaciones.append({
                        'Técnico Penalizado': fila_penalizada['Técnico'],
                        'Serie': fila_actual['Serie'],
                        'Folio de su Falla': fila_penalizada['Folio'],
                        'Fecha de su Falla': fila_penalizada['Fecha recepción'].strftime('%d/%m/%Y %H:%M'),
                        'Detonado por Folio': fila_actual['Folio'],
                        'Fecha del Detonante': fila_actual['Fecha recepción'].strftime('%d/%m/%Y %H:%M'),
                        'Puntos': 1.0
                    })

    df_pen = pd.DataFrame(lista_penalizaciones)

    # --- VISUALIZACIÓN ---
    tab_puntos, tab_auditoria = st.tabs(["📈 Puntaje Final", "📋 Auditoría Detallada"])

    with tab_puntos:
        # Puntos por servicios realizados en el mes
        resumen = df_mes_actual[df_mes_actual['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Visitas_Mes')
        resumen['Pts_Positivos'] = resumen['Visitas_Mes'] * 1.0
        
        if not df_pen.empty:
            # Agrupamos todas las penalizaciones encontradas por el barrido
            p_neg = df_pen.groupby('Técnico Penalizado')['Puntos'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen_final = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0
            resumen_final = resumen

        resumen_final['TOTAL'] = resumen_final['Pts_Ganados' if 'Pts_Ganados' in resumen_final else 'Pts_Positivos'] - resumen_final['Penalización']
        st.dataframe(resumen_final.sort_values('TOTAL', ascending=False), use_container_width=True)

    with tab_auditoria:
        st.subheader("Desglose Completo de Reincidencias (Toda la data)")
        if not df_pen.empty:
            # Eliminar duplicados exactos si el barrido repitió alguna relación
            df_pen = df_pen.drop_duplicates(subset=['Técnico Penalizado', 'Folio de su Falla', 'Detonado por Folio'])
            
            st.write(f"Se detectaron un total de {len(df_pen)} penalizaciones aplicando la lógica de barrido.")
            st.dataframe(df_pen, use_container_width=True)
        else:
            st.info("No se encontraron reincidencias con los criterios actuales.")
else:
    st.info("Sube el archivo para procesar la auditoría.")
