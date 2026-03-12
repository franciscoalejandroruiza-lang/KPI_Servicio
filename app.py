import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SenAudit Pro - Auditoría Detallada", layout="wide")

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

# --- INICIALIZACIÓN ---
MESES_MAP = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}

st.title("📊 SenAudit Pro - Gestión de Manufactura")

# --- CARGA Y LIMPIEZA ---
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])

if archivo_subido:
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
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
    periodo_sel = st.sidebar.selectbox("📅 Periodo a Evaluar:", df['Mes_Año'].unique())

    # --- MOTOR DE CÁLCULO ---
    df_actual = df[df['Mes_Año'] == periodo_sel].copy()
    val_reinc = 1.0 # Valor por defecto
    
    lista_penalizaciones = []
    penalizados_por_serie = set()

    # Buscamos correctivos en el mes actual
    df_correctivos = df_actual[df_actual['Categoría'] == 'CORRECTIVO'].copy()

    for _, fila_actual in df_correctivos.iterrows():
        # Buscamos en el pasado quién vio esta serie
        historial = df[
            (df['Serie'] == fila_actual['Serie']) & 
            (df['Fecha recepción'] < fila_actual['Fecha recepción'])
        ].sort_values('Fecha recepción', ascending=False)
        
        if not historial.empty:
            # Iteramos sobre el historial para encontrar los folios previos de cada técnico
            for _, fila_pasada in historial.iterrows():
                tec_pasado = fila_pasada['Técnico']
                
                # Regla: No se penaliza a sí mismo y solo una penalización por serie en este mes
                if tec_pasado != fila_actual['Técnico'] and (tec_pasado, fila_actual['Serie']) not in penalizados_por_serie:
                    lista_penalizaciones.append({
                        'Técnico': tec_pasado,
                        'Serie': fila_actual['Serie'],
                        'Folio de Visita': fila_pasada['Folio'],      # El folio donde el técnico fue originalmente
                        'Fecha de Visita': fila_pasada['Fecha recepción'].strftime('%Y-%m-%d'),
                        'Folio Detonante': fila_actual['Folio'],      # El folio nuevo que falló
                        'Fecha de Falla': fila_actual['Fecha recepción'].strftime('%Y-%m-%d'),
                        'Puntos Menos': val_reinc
                    })
                    penalizados_por_serie.add((tec_pasado, fila_actual['Serie']))

    df_pen = pd.DataFrame(lista_penalizaciones)

    # --- PESTAÑAS ---
    t_resumen, t_agrupado = st.tabs(["📈 Puntaje Final", "⚠️ Detalle por Técnico"])

    with t_resumen:
        # Puntos ganados por visitas resueltas
        if 'Pts_Ganados' not in st.session_state: st.session_state.pts_std = 1.0
        df_resueltas = df_actual[df_actual['Estatus'] == 'RESUELTA'].copy()
        resumen = df_resueltas.groupby('Técnico').size().reset_index(name='Visitas')
        resumen['Pts_Positivos'] = resumen['Visitas'] * 1.0 # Asumiendo 1 pto por visita
        
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico')['Puntos Menos'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0

        resumen['TOTAL'] = resumen['Pts_Positivos'] - resumen['Penalización']
        st.dataframe(resumen.sort_values('TOTAL', ascending=False), use_container_width=True)

    with t_agrupado:
        st.header("Análisis de Folios: Visita vs Detonante")
        if not df_pen.empty:
            tecnicos = sorted(df_pen['Técnico'].unique())
            for tec in tecnicos:
                detalle = df_pen[df_pen['Técnico'] == tec]
                with st.expander(f"👤 {tec} (Total Penalizado: -{detalle['Puntos Menos'].sum()})"):
                    st.table(detalle[[
                        'Serie', 
                        'Folio de Visita', 
                        'Fecha de Visita', 
                        'Folio Detonante', 
                        'Fecha de Falla'
                    ]])
        else:
            st.success("No hay reincidencias registradas.")
else:
    st.info("Suba el reporte para comenzar.")
