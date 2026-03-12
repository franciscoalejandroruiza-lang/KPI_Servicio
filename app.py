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

# --- BLOQUE DE PROPIEDAD INTELECTUAL (MODAL) ---
@st.dialog("Aviso de Confidencialidad")
def mostrar_aviso_legal():
    st.warning("⚠️ ACCESO RESTRINGIDO")
    st.write("""
        Este software es **Propiedad Intelectual Privada**. 
        El uso de esta herramienta está limitado al personal autorizado de la planta.
        Al continuar, usted acepta que no intentará copiar, distribuir ni realizar 
        ingeniería inversa sobre este código.
    """)
    if st.button("Acepto los Términos y Condiciones"):
        st.session_state.legal_accepted = True
        st.rerun()

if "legal_accepted" not in st.session_state:
    mostrar_aviso_legal()
    st.stop()

# --- INICIALIZACIÓN DE ESTADOS ---
if 'lista_extras' not in st.session_state: st.session_state.lista_extras = []
if 'pesos_dict' not in st.session_state: st.session_state.pesos_dict = {}

MESES_MAP = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}

st.title("📊 SenAudit Pro - Gestión de Manufactura ptm")
st.sidebar.markdown("© 2026 Propiedad Privada")

# --- BARRA LATERAL ---
st.sidebar.header("📁 Panel de Control")
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])
meses_atras_reinc = st.sidebar.slider("Meses para rastrear responsables anteriores", 1, 12, 3)

if archivo_subido:
    # Carga de datos
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # Estandarización de columnas
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    cliente_col = "Nombre comercial" if "Nombre comercial" in df.columns else ("Nombre legal" if "Nombre legal" in df.columns else "Cliente")
    
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()
    
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico'])
    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)

    periodos = df.sort_values('Fecha recepción', ascending=False)['Mes_Año'].unique()
    periodo_sel = st.sidebar.selectbox("📅 Periodo a Evaluar:", periodos)

    # --- PESTAÑAS ---
    t_resumen, t_matriz, t_penalizaciones, t_top, t_adicionales, t_config = st.tabs([
        "📈 Puntaje Final", "📋 Matriz Operativa", "⚠️ Penalizaciones", "🔝 Top Fallas", "📝 Extras", "⚙️ Config"
    ])

    # --- LÓGICA DE CÁLCULO ---
    df_actual = df[df['Mes_Año'] == periodo_sel].copy()
    fecha_inicio_mes = df_actual['Fecha recepción'].min()
    fecha_limite_hist = fecha_inicio_mes - pd.DateOffset(months=meses_atras_reinc)
    
    # Historial para reincidencias
    historial = df[(df['Fecha recepción'] < fecha_inicio_mes) & (df['Fecha recepción'] >= fecha_limite_hist)]
    historial_corr = historial[historial['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])].copy()
    
    # Mapeo de técnicos previos por serie
    dict_reinc_colectiva = historial_corr.groupby('Serie')['Técnico'].apply(set).to_dict()

    df_res = df_actual[df_actual['Estatus'] == 'RESUELTA'].copy()

    with t_config:
        st.header("⚙️ Configuración de Pesos")
        for cat in [c for c in df['Categoría'].dropna().unique() if str(c) != 'NAN']:
            st.session_state.pesos_dict[cat] = st.slider(f"Puntos: {cat}", -5.0, 20.0, st.session_state.pesos_dict.get(cat, 1.0), 0.5)
        val_reinc = st.number_input("Descuento por cada técnico reincidente (-1)", 0.0, 10.0, 1.0)

    # Procesamiento de Puntos y Penalizaciones ÚNICAS
    df_res['Pts_Base'] = df_res['Categoría'].map(st.session_state.pesos_dict).fillna(0.0)
    
    lista_penalizaciones = []
    penalizaciones_registradas = set() # Para evitar duplicados (Técnico, Serie)

    for _, fila in df_res.iterrows():
        # Si es correctivo y alguien más lo vio antes en el historial
        if fila['Categoría'] == 'CORRECTIVO' and fila['Serie'] in dict_reinc_colectiva:
            for tec_pasado in dict_reinc_colectiva[fila['Serie']]:
                
                # Regla: No se penaliza a sí mismo y solo se penaliza una vez por serie
                id_penalizacion = (tec_pasado, fila['Serie'])
                
                if tec_pasado != fila['Técnico'] and id_penalizacion not in penalizaciones_registradas:
                    lista_penalizaciones.append({
                        'Técnico': tec_pasado, 
                        'Cliente': fila[cliente_col],
                        'Serie': fila['Serie'], 
                        'Folio Detonante': fila['Folio'], 
                        'Descuento': val_reinc
                    })
                    penalizaciones_registradas.add(id_penalizacion)
    
    df_pen = pd.DataFrame(lista_penalizaciones)

    # --- PESTAÑA: PUNTAJE FINAL ---
    with t_resumen:
        st.header(f"Resumen de Puntuación: {periodo_sel}")
        resumen = df_res.groupby('Técnico')['Pts_Base'].sum().reset_index()
        
        # Agregar Extras
        if st.session_state.lista_extras:
            df_ex = pd.DataFrame(st.session_state.lista_extras)
            ex_sum = df_ex[df_ex['Periodo'] == periodo_sel].groupby('Técnico')['Puntos Extra'].sum().reset_index()
            resumen = pd.merge(resumen, ex_sum, on='Técnico', how='outer').fillna(0)
            resumen['Subtotal'] = resumen['Pts_Base'] + resumen['Puntos Extra']
        else:
            resumen['Puntos Extra'], resumen['Subtotal'] = 0.0, resumen['Pts_Base']

        # Agregar Penalizaciones (Merge corregido por columna 'Técnico')
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico')['Descuento'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='left').fillna(0)
            resumen['TOTAL NETO'] = resumen['Subtotal'] - resumen['Penalización']
        else:
            resumen['Penalización'], resumen['TOTAL NETO'] = 0.0, resumen['Subtotal']
        
        st.dataframe(resumen[['Técnico', 'Pts_Base', 'Puntos Extra', 'Penalización', 'TOTAL NETO']].sort_values('TOTAL NETO', ascending=False), use_container_width=True)
        st.plotly_chart(px.bar(resumen, x='TOTAL NETO', y='Técnico', orientation='h', title="Ranking de Productividad", color='TOTAL NETO', color_continuous_scale='Blues'))

    # --- PESTAÑA: DETALLE PENALIZACIONES ---
    with t_penalizaciones:
        st.header("⚠️ Detalle de Responsabilidad Colectiva (Penalización Única)")
        if not df_pen.empty:
            for tec in sorted(df_pen['Técnico'].unique()):
                with st.expander(f"🔴 Penalizaciones para: {tec}"):
                    df_tec_pen = df_pen[df_pen['Técnico'] == tec]
                    st.table(df_tec_pen[['Cliente', 'Serie', 'Folio Detonante', 'Descuento']])
        else:
            st.success("No se detectaron reincidencias en este periodo.")

    # --- PESTAÑA: MATRIZ ---
    with t_matriz:
        st.header("📋 Conteo por Actividad")
        st.dataframe(df_res.groupby(['Técnico', 'Categoría']).size().unstack(fill_value=0), use_container_width=True)

    # --- PESTAÑA: ADICIONALES ---
    with t_adicionales:
        with st.form("form_extras"):
            c1, c2, c3 = st.columns(3)
            tec_ad = c1.selectbox("Técnico", sorted(df['Técnico'].unique()))
            nom_ad = c2.text_input("Actividad")
            val_ad = c3.number_input("Puntos", value=1.0, step=0.5)
            if st.form_submit_button("Añadir"):
                st.session_state.lista_extras.append({'Técnico': tec_ad, 'Actividad': nom_ad.upper(), 'Puntos Extra': val_ad, 'Periodo': periodo_sel})
                st.rerun()
else:
    st.info("Suba el reporte Excel para comenzar.")
