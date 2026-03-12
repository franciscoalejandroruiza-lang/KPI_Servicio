import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN DE SEGURIDAD Y PÁGINA
st.set_page_config(
    page_title="SenIntegral - Auditoría Técnica Pro", 
    layout="wide",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Propiedad Intelectual de Alejandro Ruiz. Prohibida su reproducción."
    }
)

# --- BLOQUE DE PROPIEDAD INTELECTUAL ---
@st.dialog("Aviso de Confidencialidad")
def mostrar_aviso_legal():
    st.warning("⚠️ ACCESO RESTRINGIDO")
    st.write("""
        Este software es **Propiedad Intelectual Privada**. 
        El uso de esta herramienta está limitado al personal autorizado.
    """)
    if st.button("Acepto los Términos y Condiciones"):
        st.session_state.legal_accepted = True
        st.rerun()

if "legal_accepted" not in st.session_state:
    mostrar_aviso_legal()
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
st.sidebar.markdown("© 2026 Propiedad Privada")

# --- BARRA LATERAL ---
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])

if archivo_subido:
    # CARGA Y LIMPIEZA CRÍTICA
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # 1. Normalizar Series (Quitar ceros a la izquierda y espacios)
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    df['Serie'] = df['Serie'].astype(str).str.strip().str.lstrip('0')
    
    # 2. Normalizar Técnicos (Quitar "CH " para que Iván Cano sea reconocido siempre)
    df['Técnico'] = df['Técnico'].astype(str).str.replace('CH ', '', regex=False).str.strip().str.upper()
    
    # 3. Normalizar Fechas y Categorías
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()

    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)
    periodos = df.sort_values('Fecha recepción', ascending=False)['Mes_Año'].unique()
    periodo_sel = st.sidebar.selectbox("📅 Periodo a Evaluar:", periodos)

    # PESTAÑAS
    t_resumen, t_matriz, t_penalizaciones, t_adicionales, t_config = st.tabs([
        "📈 Puntaje Final", "📋 Matriz Operativa", "⚠️ Penalizaciones", "📝 Extras", "⚙️ Config"
    ])

    with t_config:
        st.header("⚙️ Configuración de Pesos")
        for cat in sorted(df['Categoría'].unique()):
            st.session_state.pesos_dict[cat] = st.slider(f"Puntos: {cat}", -5.0, 20.0, st.session_state.pesos_dict.get(cat, 1.0), 0.5)
        val_reinc = st.number_input("Descuento por reincidencia (-1)", 0.0, 10.0, 1.0)

    # --- MOTOR DE CÁLCULO (POR FECHA EXACTA) ---
    df_actual = df[df['Mes_Año'] == periodo_sel].copy()
    df_actual['Pts_Base'] = df_actual['Categoría'].map(st.session_state.pesos_dict).fillna(0.0)
    
    lista_penalizaciones = []
    penalizados_por_serie = set() # Evita que alguien pague doble por la misma serie

    # Solo penalizamos si el registro actual es un CORRECTIVO
    df_correctivos = df_actual[df_actual['Categoría'] == 'CORRECTIVO'].copy()

    for _, fila_actual in df_correctivos.iterrows():
        # Buscamos quién estuvo en esta serie ANTES de este folio (en todo el historial disponible)
        historial = df[
            (df['Serie'] == fila_actual['Serie']) & 
            (df['Fecha recepción'] < fila_actual['Fecha recepción'])
        ].sort_values('Fecha recepción', ascending=False)

        if not historial.empty:
            tecnicos_previos = historial['Técnico'].unique()
            for tec_pasado in tecnicos_previos:
                # Si no es el mismo técnico y no ha pagado por esta serie aún
                if tec_pasado != fila_actual['Técnico'] and (tec_pasado, fila_actual['Serie']) not in penalizados_por_serie:
                    lista_penalizaciones.append({
                        'Técnico': tec_pasado,
                        'Serie': fila_actual['Serie'],
                        'Folio Detonante': fila_actual['Folio'],
                        'Fecha Detonante': fila_actual['Fecha recepción'],
                        'Descuento': val_reinc
                    })
                    penalizados_por_serie.add((tec_pasado, fila_actual['Serie']))

    df_pen = pd.DataFrame(lista_penalizaciones)

    # --- PESTAÑA RESUMEN ---
    with t_resumen:
        # Sumamos puntos del mes (solo de lo RESUELTO para no inflar)
        df_resueltas = df_actual[df_actual['Estatus'] == 'RESUELTA'].copy()
        resumen = df_resueltas.groupby('Técnico')['Pts_Base'].sum().reset_index()

        # Unimos Penalizaciones
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico')['Descuento'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0

        # Unimos Extras
        if st.session_state.lista_extras:
            df_ex = pd.DataFrame(st.session_state.lista_extras)
            ex_sum = df_ex[df_ex['Periodo'] == periodo_sel].groupby('Técnico')['Puntos Extra'].sum().reset_index()
            resumen = pd.merge(resumen, ex_sum, on='Técnico', how='left').fillna(0)
        else:
            resumen['Puntos Extra'] = 0.0

        resumen['TOTAL NETO'] = resumen['Pts_Base'] + resumen['Puntos Extra'] - resumen['Penalización']
        
        st.dataframe(resumen.sort_values('TOTAL NETO', ascending=False), use_container_width=True)
        st.plotly_chart(px.bar(resumen, x='TOTAL NETO', y='Técnico', orientation='h', title="Productividad Final"))

    # --- PESTAÑA DETALLE PENALIZACIONES ---
    with t_penalizaciones:
        if not df_pen.empty:
            st.write("### Quién penalizó a quién (Basado en historial)")
            st.dataframe(df_pen, use_container_width=True)
        else:
            st.success("No hay penalizaciones registradas.")

    with t_matriz:
        st.dataframe(df_actual.groupby(['Técnico', 'Categoría']).size().unstack(fill_value=0))

    with t_adicionales:
        with st.form("extras"):
            c1, c2, c3 = st.columns(3)
            t_ad = c1.selectbox("Técnico", sorted(df['Técnico'].unique()))
            desc_ad = c2.text_input("Motivo")
            pts_ad = c3.number_input("Puntos", value=1.0)
            if st.form_submit_button("Guardar Extra"):
                st.session_state.lista_extras.append({'Técnico': t_ad, 'Periodo': periodo_sel, 'Puntos Extra': pts_ad})
                st.rerun()
else:
    st.info("Sube el archivo Excel para procesar.")
