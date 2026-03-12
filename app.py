import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SenAudit Pro - Reporte de Reincidencias", layout="wide")

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

st.title("📊 SenAudit Pro - Análisis de Series")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuración")
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])

# Configuración de meses atrás (Default 3: Ene, Dic, Nov si es Feb)
meses_atras = st.sidebar.slider("Meses de historial a rastrear", 1, 12, 3)

if archivo_subido:
    # CARGA Y LIMPIEZA
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # Normalización de Series (03008454 -> 3008454) y Técnicos (CH IVAN -> IVAN)
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    df['Serie'] = df['Serie'].astype(str).str.strip().str.lstrip('0')
    df['Técnico'] = df['Técnico'].astype(str).str.replace('CH ', '', regex=False).str.replace('CHI ', '', regex=False).str.strip().str.upper()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()

    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)
    periodo_sel = st.sidebar.selectbox("📅 Mes a Evaluar:", df['Mes_Año'].unique())

    # --- MOTOR DE PENALIZACIÓN DETALLADO ---
    df_actual = df[df['Mes_Año'] == periodo_sel].copy()
    inicio_mes = df_actual['Fecha recepción'].min()
    limite_hist = inicio_mes - pd.DateOffset(months=meses_atras)
    
    lista_detallada_penalizaciones = []
    series_penalizadas_por_tecnico = set() # Para el conteo de puntos final

    # Analizamos los CORRECTIVOS del mes
    df_detonantes = df_actual[df_actual['Categoría'] == 'CORRECTIVO'].copy()

    for _, fila_det in df_detonantes.iterrows():
        # Buscamos quién estuvo antes en esta serie dentro del rango configurado
        historial = df[
            (df['Serie'] == fila_det['Serie']) & 
            (df['Fecha recepción'] < fila_det['Fecha recepción']) &
            (df['Fecha recepción'] >= limite_hist)
        ].sort_values('Fecha recepción', ascending=False)
        
        if not historial.empty:
            # Encontramos a todos los técnicos previos
            tecnicos_previos = historial['Técnico'].unique()
            
            for tec_p in tecnicos_previos:
                if tec_p != fila_det['Técnico']:
                    # Buscamos el folio específico de la visita de ese técnico
                    visita_orig = historial[historial['Técnico'] == tec_p].iloc[0]
                    
                    # Decidimos si resta puntos (solo 1 vez por serie al mes)
                    llave_puntos = (tec_p, fila_det['Serie'])
                    punto_descontado = 0
                    if llave_puntos not in series_penalizadas_por_tecnico:
                        punto_descontado = 1.0
                        series_penalizadas_por_tecnico.add(llave_puntos)
                    
                    # AGREGAMOS A LA LISTA (Aquí sí veremos las 6 fallas si existen)
                    lista_detallada_penalizaciones.append({
                        'Técnico': tec_p,
                        'Serie': fila_det['Serie'],
                        'Folio Visita Original': visita_orig['Folio'],
                        'Fecha Visita': visita_orig['Fecha recepción'].strftime('%d/%m/%y'),
                        'Folio Detonante (Falla)': fila_det['Folio'],
                        'Fecha de Falla': fila_det['Fecha recepción'].strftime('%d/%m/%y'),
                        'Puntos Restados': punto_descontado
                    })

    df_pen = pd.DataFrame(lista_detallada_penalizaciones)

    # --- PESTAÑAS ---
    t_resumen, t_agrupado = st.tabs(["📈 Puntaje Final", "⚠️ Detalle por Técnico (Serie 3008454)"])

    with t_resumen:
        df_ok = df_actual[df_actual['Estatus'] == 'RESUELTA'].copy()
        # Asignamos 1 punto por cada servicio resuelto
        resumen = df_ok.groupby('Técnico').size().reset_index(name='Visitas_Mes')
        resumen['Pts_Ganados'] = resumen['Visitas_Mes'] * 1.0
        
        if not df_pen.empty:
            # Sumamos los puntos restados (que gracias al set() solo será 1 por serie)
            p_neg = df_pen.groupby('Técnico')['Puntos Restados'].sum().reset_index(name='Penalización')
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0

        resumen['TOTAL'] = resumen['Pts_Ganados'] - resumen['Penalización']
        st.dataframe(resumen.sort_values('TOTAL', ascending=False), use_container_width=True)

    with t_agrupado:
        st.header(f"Desglose de Reincidencias (Rastreo: {meses_atras} meses)")
        if not df_pen.empty:
            for tec in sorted(df_pen['Técnico'].unique()):
                datos_tec = df_pen[df_pen['Técnico'] == tec]
                total_puntos = datos_tec['Puntos Restados'].sum()
                
                with st.expander(f"👤 {tec} — Penalización Real: -{total_puntos}"):
                    st.write(f"Mostrando todas las fallas detectadas para este técnico:")
                    # Resaltamos las que sí restaron puntos y las que son informativas
                    st.table(datos_tec[['Serie', 'Folio Visita Original', 'Fecha Visita', 'Folio Detonante (Falla)', 'Fecha de Falla', 'Puntos Restados']])
        else:
            st.success("No se detectaron fallas con los parámetros actuales.")

else:
    st.info("Sube el archivo para iniciar.")
