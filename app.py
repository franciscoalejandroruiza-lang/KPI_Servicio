import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SenAudit Pro - Reporte Agrupado", layout="wide")

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

# --- CARGA Y LIMPIEZA ---
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])

if archivo_subido:
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # Normalización para que IVAN CANO y Series coincidan
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    df['Serie'] = df['Serie'].astype(str).str.strip().str.lstrip('0')
    df['Técnico'] = df['Técnico'].astype(str).str.replace('CH ', '', regex=False).str.strip().str.upper()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()

    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)
    periodo_sel = st.sidebar.selectbox("📅 Periodo a Evaluar:", df['Mes_Año'].unique())

    # --- PESTAÑAS ---
    t_resumen, t_agrupado, t_config = st.tabs(["📈 Puntaje Final", "⚠️ Detalle por Técnico", "⚙️ Config"])

    with t_config:
        st.header("Configuración de Pesos")
        for cat in sorted(df['Categoría'].unique()):
            st.session_state.pesos_dict[cat] = st.slider(f"Puntos: {cat}", -5.0, 10.0, st.session_state.pesos_dict.get(cat, 1.0), 0.5)
        val_reinc = st.number_input("Descuento por reincidencia (-1)", 0.0, 5.0, 1.0)

    # --- LÓGICA DE PENALIZACIÓN ---
    df_actual = df[df['Mes_Año'] == periodo_sel].copy()
    lista_penalizaciones = []
    penalizados_por_serie = set()

    # Buscamos correctivos en el mes actual
    df_correctivos = df_actual[df_actual['Categoría'] == 'CORRECTIVO'].copy()

    for _, fila_actual in df_correctivos.iterrows():
        # Quién estuvo antes en esta serie (Historial completo)
        historial = df[(df['Serie'] == fila_actual['Serie']) & (df['Fecha recepción'] < fila_actual['Fecha recepción'])]
        
        if not historial.empty:
            tecnicos_previos = historial['Técnico'].unique()
            for tec_pasado in tecnicos_previos:
                # Si no es el mismo y no ha pagado por esta serie en este mes
                if tec_pasado != fila_actual['Técnico'] and (tec_pasado, fila_actual['Serie']) not in penalizados_por_serie:
                    lista_penalizaciones.append({
                        'Técnico': tec_pasado,
                        'Serie': fila_actual['Serie'],
                        'Folio Detonante': fila_actual['Folio'],
                        'Fecha Falla': fila_actual['Fecha recepción'].strftime('%Y-%m-%d'),
                        'Puntos Menos': val_reinc
                    })
                    penalizados_por_serie.add((tec_pasado, fila_actual['Serie']))

    df_pen = pd.DataFrame(lista_penalizaciones)

    # --- PESTAÑA: PUNTAJE FINAL ---
    with t_resumen:
        df_resueltas = df_actual[df_actual['Estatus'] == 'RESUELTA'].copy()
        df_resueltas['Pts_Ganados'] = df_resueltas['Categoría'].map(st.session_state.pesos_dict).fillna(0.0)
        
        resumen = df_resueltas.groupby('Técnico')['Pts_Ganados'].sum().reset_index()
        
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico')['Puntos Menos'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0

        resumen['TOTAL'] = resumen['Pts_Ganados'] - resumen['Penalización']
        
        st.subheader(f"Resultados de {periodo_sel}")
        st.dataframe(resumen.sort_values('TOTAL', ascending=False), use_container_width=True)
        st.plotly_chart(px.bar(resumen, x='TOTAL', y='Técnico', orientation='h', color='TOTAL', title="Productividad"))

    # --- PESTAÑA: DETALLE AGRUPADO ---
    with t_agrupado:
        st.header("Análisis de Reincidencias")
        if not df_pen.empty:
            # Agrupamos por técnico para crear los expanders
            tecnicos_con_falla = sorted(df_pen['Técnico'].unique())
            
            for tec in tecnicos_con_falla:
                detalle_tec = df_pen[df_pen['Técnico'] == tec]
                total_descuento = detalle_tec['Puntos Menos'].sum()
                
                with st.expander(f"👤 {tec} — Penalización Total: -{total_descuento}"):
                    st.write(f"El técnico **{tec}** fue penalizado porque las siguientes series fallaron después de su visita:")
                    st.table(detalle_tec[['Serie', 'Folio Detonante', 'Fecha Falla', 'Puntos Menos']])
        else:
            st.success("No hay penalizaciones para agrupar en este mes.")

else:
    st.info("Suba el reporte para generar la auditoría.")
