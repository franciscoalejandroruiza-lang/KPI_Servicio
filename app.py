import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="SenIntegral - Auditoría Técnica Pro", layout="wide")

# Inicialización de estados para persistencia de datos
if 'lista_extras' not in st.session_state: st.session_state.lista_extras = []
if 'pesos_dict' not in st.session_state: st.session_state.pesos_dict = {}

# Mapeo de meses para orden y visualización
MESES_MAP = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}

st.title("📊 Control de Ingeniería y Productividad - SenIntegral")

# --- BARRA LATERAL ---
st.sidebar.header("📁 Panel de Control")
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])
meses_atras_reinc = st.sidebar.slider("Meses para rastrear responsables anteriores", 1, 12, 3)

if archivo_subido:
    # Carga de datos
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # Estandarización de columnas clave
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    cliente_col = "Nombre comercial" if "Nombre comercial" in df.columns else ("Nombre legal" if "Nombre legal" in df.columns else "Cliente")
    
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()
    
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico'])
    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)

    periodos = df.sort_values('Fecha recepción', ascending=False)['Mes_Año'].unique()
    periodo_sel = st.sidebar.selectbox("📅 Periodo a Evaluar:", periodos)

    # --- PESTAÑAS (Notas eliminada) ---
    t_resumen, t_matriz, t_penalizaciones, t_top, t_adicionales, t_config = st.tabs([
        "📈 Puntaje Final", "📋 Matriz Operativa", "⚠️ Penalizaciones por Técnico", "🔝 Top Fallas", "📝 Actividades Adicionales", "⚙️ Configuración"
    ])

    # --- LÓGICA DE CÁLCULO ---
    df_actual = df[df['Mes_Año'] == periodo_sel].copy()
    fecha_inicio_mes = df_actual['Fecha recepción'].min()
    fecha_limite_hist = fecha_inicio_mes - pd.DateOffset(months=meses_atras_reinc)
    
    # Rastrear responsables pasados para reincidencias
    historial = df[(df['Fecha recepción'] < fecha_inicio_mes) & (df['Fecha recepción'] >= fecha_limite_hist)]
    historial_corr = historial[historial['Categoría'] == 'CORRECTIVO']
    dict_reinc = historial_corr.groupby('Serie')['Técnico'].apply(set).to_dict()

    df_res = df_actual[df_actual['Estatus'] == 'RESUELTA'].copy()

    with t_config:
        st.header("⚙️ Configuración de Pesos")
        for cat in [c for c in df['Categoría'].dropna().unique() if str(c) != 'NAN']:
            st.session_state.pesos_dict[cat] = st.slider(f"Puntos: {cat}", -5.0, 20.0, st.session_state.pesos_dict.get(cat, 1.0), 0.5)
        val_reinc = st.number_input("Descuento por reincidencia", 0.0, 10.0, 1.0)

    # Procesamiento de Puntos y Penalizaciones detalladas
    df_res['Pts_Base'] = df_res['Categoría'].map(st.session_state.pesos_dict).fillna(0.0)
    lista_penalizaciones = []
    for _, fila in df_res.iterrows():
        if fila['Categoría'] == 'CORRECTIVO' and fila['Serie'] in dict_reinc:
            for tec_pasado in dict_reinc[fila['Serie']]:
                lista_penalizaciones.append({
                    'Técnico Penalizado': tec_pasado, 'Cliente': fila[cliente_col],
                    'Serie': fila['Serie'], 'Folio Detonante': fila['Folio'], 'Descuento': val_reinc
                })
    df_pen = pd.DataFrame(lista_penalizaciones)

    # --- PESTAÑA: PUNTAJE FINAL ---
    with t_resumen:
        st.header(f"Resumen de Puntuación: {periodo_sel}")
        
        # 1. Puntos Base (Trabajo del mes)
        resumen = df_res.groupby('Técnico')['Pts_Base'].sum().reset_index()
        
        # 2. Sumar Actividades Adicionales
        if st.session_state.lista_extras:
            df_ex = pd.DataFrame(st.session_state.lista_extras)
            ex_sum = df_ex[df_ex['Periodo'] == periodo_sel].groupby('Técnico')['Puntos Extra'].sum().reset_index()
            resumen = pd.merge(resumen, ex_sum, on='Técnico', how='outer').fillna(0)
            resumen['Subtotal'] = resumen['Pts_Base'] + resumen['Puntos Extra']
        else:
            resumen['Puntos Extra'] = 0.0
            resumen['Subtotal'] = resumen['Pts_Base']

        # 3. Restar Penalizaciones
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico Penalizado')['Descuento'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalización']
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='outer').fillna(0)
            resumen['TOTAL NETO'] = resumen['Subtotal'] - resumen['Penalización']
        else:
            resumen['Penalización'] = 0.0
            resumen['TOTAL NETO'] = resumen['Subtotal']
        
        # Tabla Principal
        columnas_view = ['Técnico', 'Pts_Base', 'Puntos Extra', 'Penalización', 'TOTAL NETO']
        st.dataframe(resumen[columnas_view].sort_values('TOTAL NETO', ascending=False), use_container_width=True)
        
        # Gráfica de barras horizontal
        st.plotly_chart(px.bar(resumen, x='TOTAL NETO', y='Técnico', orientation='h', 
                               title="Ranking de Productividad", color='TOTAL NETO', 
                               color_continuous_scale='Blues'))

    # --- PESTAÑA: PENALIZACIONES POR TÉCNICO ---
    with t_penalizaciones:
        st.header("⚠️ Detalle de Descuentos por Reincidencia")
        if not df_pen.empty:
            for tec in sorted(df_pen['Técnico Penalizado'].unique()):
                with st.expander(f"🔴 Técnico: {tec}"):
                    df_tec_pen = df_pen[df_pen['Técnico Penalizado'] == tec]
                    st.table(df_tec_pen[['Cliente', 'Serie', 'Folio Detonante', 'Descuento']])
        else:
            st.success("No se detectaron reincidencias en este periodo.")

    # --- PESTAÑA: ACTIVIDADES ADICIONALES ---
    with t_adicionales:
        st.header("📝 Registro de Actividades Extraordinarias")
        with st.form("form_extras"):
            c1, c2, c3 = st.columns(3)
            tec_ad = c1.selectbox("Seleccionar Técnico", sorted(df['Técnico'].unique()))
            nom_ad = c2.text_input("Nombre de la Actividad")
            val_ad = c3.number_input("Puntos", value=1.0, step=0.5)
            if st.form_submit_button("Añadir Actividad"):
                st.session_state.lista_extras.append({
                    'Técnico': tec_ad, 'Actividad': nom_ad.upper(), 
                    'Puntos Extra': val_ad, 'Periodo': periodo_sel
                })
                st.rerun()
        
        if st.session_state.lista_extras:
            st.subheader("Historial registrado para este periodo")
            df_extras_v = pd.DataFrame(st.session_state.lista_extras)
            st.table(df_extras_v[df_extras_v['Periodo'] == periodo_sel])

    # --- PESTAÑA: TOP FALLAS ---
    with t_top:
        st.header(f"🔝 Top 10 Equipos con Fallas Correctivas")
        df_t_mes = df_actual[(df_actual['Categoría'] == 'CORRECTIVO') & (df_actual['Estatus'] == 'RESUELTA')]
        if not df_t_mes.empty:
            top_mes = df_t_mes.groupby(['Serie', cliente_col]).size().reset_index(name='Fallas')
            top_mes = top_mes.sort_values('Fallas', ascending=False).head(10)
            st.table(top_mes)
            st.plotly_chart(px.bar(top_mes, x='Fallas', y='Serie', orientation='h', hover_data=[cliente_col]))

    # --- PESTAÑA: MATRIZ OPERATIVA ---
    with t_matriz:
        st.header("📋 Conteo por Tipo de Actividad")
        st.dataframe(df_res.groupby(['Técnico', 'Categoría']).size().unstack(fill_value=0), use_container_width=True)

else:
    st.info("Suba el reporte Excel para activar el tablero de SenIntegral.")