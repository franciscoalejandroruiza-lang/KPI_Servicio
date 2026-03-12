import streamlit as st
import pandas as pd
from datetime import timedelta

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SenAudit Pro - Historial Dinámico", layout="wide")

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

st.title("📊 SenAudit Pro - Reporte con Historial desde el Mes de Revisión")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuración")
archivo = st.sidebar.file_uploader("Cargar Reporte (Excel/CSV)", type=["xlsx", "csv"])
# El slider ahora controla el bloque de 90 días/3 meses
meses_atras = st.sidebar.slider("Meses de historial a considerar", 1, 6, 3)

if archivo:
    # 2. CARGA Y LIMPIEZA DE DATOS
    df = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # Normalización de Series y Técnicos
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    df['Serie'] = df['Serie'].astype(str).str.strip().str.lstrip('0')
    df['Técnico'] = df['Técnico'].astype(str).str.replace('CH ', '', regex=False).str.replace('CHI ', '', regex=False).str.strip().str.upper()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()

    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)
    df = df.sort_values('Fecha recepción')
    
    periodos = df['Mes_Año'].unique()[::-1]
    periodo_sel = st.sidebar.selectbox("📅 Mes a Evaluar:", periodos)

    # --- LÓGICA DE TIEMPO AJUSTADA ---
    # 1. Determinamos el inicio del mes que se está revisando
    df_mes_actual = df[df['Mes_Año'] == periodo_sel].copy()
    fecha_inicio_revision = df_mes_actual['Fecha recepción'].min().replace(day=1)
    
    # 2. Calculamos la fecha límite (ej. 90 días antes del inicio del mes)
    fecha_limite_historial = fecha_inicio_revision - timedelta(days=meses_atras * 30)

    # --- MOTOR DE PENALIZACIÓN ---
    lista_penalizaciones = []

    for _, fila_actual in df_mes_actual.iterrows():
        # Buscamos historial de la serie desde la fecha límite hasta el momento justo antes de esta visita
        historial_previo = df[
            (df['Serie'] == fila_actual['Serie']) & 
            (df['Fecha recepción'] < fila_actual['Fecha recepción']) &
            (df['Fecha recepción'] >= fecha_limite_historial)
        ].sort_values('Fecha recepción', ascending=False)
        
        if not historial_previo.empty:
            # Filtramos folios penalizables (Correctivos/Reincidencias)
            reincidencias = historial_previo[historial_previo['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])]
            
            for _, fila_pen in reincidencias.iterrows():
                # No penalizar si el técnico es el mismo
                if fila_pen['Técnico'] != fila_actual['Técnico']:
                    lista_penalizaciones.append({
                        'Técnico Penalizado': fila_pen['Técnico'],
                        'Serie': fila_actual['Serie'],
                        'Folio su Falla': fila_pen['Folio'],
                        'Fecha su Falla': fila_pen['Fecha recepción'].strftime('%d/%m/%Y'),
                        'Detonado por': fila_actual['Folio'],
                        'Fecha Detonante': fila_actual['Fecha recepción'].strftime('%d/%m/%Y'),
                        'Puntos': 1.0
                    })

    df_pen = pd.DataFrame(lista_penalizaciones)
    if not df_pen.empty:
        df_pen = df_pen.drop_duplicates(subset=['Técnico Penalizado', 'Folio su Falla', 'Detonado por'])

    # --- INTERFAZ DE RESULTADOS ---
    tab1, tab2 = st.tabs(["📈 Resumen de Puntos", "📋 Detalle por Técnico"])

    with tab1:
        st.info(f"📅 Auditoría activa desde: **{fecha_limite_historial.strftime('%d/%B/%Y')}** hasta el cierre de **{periodo_sel}**")
        
        # Conteo de servicios positivos
        resumen = df_mes_actual[df_mes_actual['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Servicios')
        resumen['Pts_Positivos'] = resumen['Servicios'] * 1.0
        
        # Integración de penalizaciones
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico Penalizado')['Puntos'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen_final = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0
            resumen_final = resumen

        resumen_final['TOTAL'] = resumen_final['Pts_Positivos'] - resumen_final['Penalización']
        st.dataframe(resumen_final.sort_values('TOTAL', ascending=False), use_container_width=True)

    with tab2:
        if not df_pen.empty:
            tecnicos_con_falla = sorted(df_pen['Técnico Penalizado'].unique())
            for tec in tecnicos_con_falla:
                datos_tec = df_pen[df_pen['Técnico Penalizado'] == tec]
                with st.expander(f"👤 {tec} — Total Goles: -{len(datos_tec)}"):
                    st.table(datos_tec[['Serie', 'Folio su Falla', 'Fecha su Falla', 'Detonado por', 'Fecha Detonante']])
        else:
            st.success("No se encontraron reincidencias en el periodo de 90 días configurado.")

else:
    st.info("Sube el reporte de servicios para iniciar el análisis.")
