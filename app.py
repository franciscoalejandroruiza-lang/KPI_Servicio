import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración profesional
st.set_page_config(page_title="Gestión de Confiabilidad Técnica | SenIntegral", layout="wide")

if 'lista_extras' not in st.session_state: st.session_state.lista_extras = []
if 'pesos_dict' not in st.session_state: st.session_state.pesos_dict = {}

MESES_MAP = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}

st.title("🛡️ SenAudit Pro - SenIntegral")

# --- BARRA LATERAL ---
st.sidebar.header("📁 Carga de Reportes")
archivo_subido = st.sidebar.file_uploader("Subir archivo de servicio", type=["xlsx", "csv"])
meses_atras_reinc = st.sidebar.slider("Ventana de análisis de reincidencias (Meses)", 1, 12, 3)

if archivo_subido:
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # Estandarización de columnas según tu archivo
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    cliente_col = "Nombre comercial" if "Nombre comercial" in df.columns else "Cliente"
    
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)

    periodos = df.sort_values('Fecha recepción', ascending=False)['Mes_Año'].unique()
    periodo_sel = st.sidebar.selectbox("📅 Mes a evaluar:", periodos)

    t_resumen, t_matriz, t_penalizaciones, t_top, t_adicionales, t_config = st.tabs([
        "📈 Puntaje Final", "📋 Matriz Operativa", "⚠️ Detalle de Penalizaciones", "🔝 Top Fallas Recurrentes", "📝 Actividades Extras", "⚙️ Configuración"
    ])

    # --- LÓGICA TÉCNICA SIN AMBIGÜEDAD ---
    df_actual = df[df['Mes_Año'] == periodo_sel].copy()
    fecha_inicio_mes = df_actual['Fecha recepción'].min()
    fecha_limite_hist = fecha_inicio_mes - pd.DateOffset(months=meses_atras_reinc)
    
    # Historial de referencia (solo correctivos para penalizar)
    historial = df[(df['Fecha recepción'] < fecha_inicio_mes) & (df['Fecha recepción'] >= fecha_limite_hist)]
    
    # 1. Reportes que el técnico CAMBIÓ A RESUELTO (Puntaje Base)
    df_res = df_actual[df_actual['Estatus'] == 'RESUELTA'].copy()

    with t_config:
        st.header("⚙️ Valores de Calidad")
        for cat in sorted(df['Categoría'].unique()):
            st.session_state.pesos_dict[cat] = st.slider(f"Puntos por {cat}:", -5.0, 20.0, st.session_state.pesos_dict.get(cat, 1.0), 0.5)
        val_reinc = st.number_input("Descuento por cada falla recurrente detectada:", 0.0, 10.0, 2.0)

    # --- CÁLCULO DE PENALIZACIONES ACUMULATIVAS ---
    lista_penalizaciones = []
    for _, fila in df_res.iterrows():
        if fila['Categoría'] == 'CORRECTIVO':
            # Buscamos cuantas veces falló esta serie ANTES de este reporte
            reincidencias = historial[(historial['Serie'] == fila['Serie']) & (historial['Categoría'] == 'CORRECTIVO')]
            
            for _, falla_ant in reincidencias.iterrows():
                # REGLA: Penalizar al técnico anterior, NO al que lo está resolviendo hoy
                if falla_ant['Técnico'] != fila['Técnico']:
                    lista_penalizaciones.append({
                        'Técnico Penalizado': falla_ant['Técnico'],
                        'Cliente': fila[cliente_col],
                        'Serie': fila['Serie'],
                        'Folio que falló': falla_ant.get('Folio', 'N/A'),
                        'Resuelto hoy por': fila['Técnico'],
                        'Descuento': val_reinc
                    })

    df_pen = pd.DataFrame(lista_penalizaciones)

    # --- PESTAÑA: PUNTAJE FINAL ---
    with t_resumen:
        resumen = df_res.groupby('Técnico')['Pts_Base'].sum().reset_index()
        resumen.rename(columns={'Pts_Base': 'Puntos Base'}, inplace=True)
        
        # Sumar Extras
        df_ex = pd.DataFrame(st.session_state.lista_extras)
        if not df_ex.empty:
            ex_sum = df_ex[df_ex['Periodo'] == periodo_sel].groupby('Técnico')['Puntos Extra'].sum().reset_index()
            resumen = pd.merge(resumen, ex_sum, on='Técnico', how='outer').fillna(0)
        else:
            resumen['Puntos Extra'] = 0.0

        # Restar Penalizaciones Acumuladas
        if not df_pen.empty:
            p_neg = df_pen.groupby('Técnico Penalizado')['Descuento'].sum().reset_index()
            p_neg.columns = ['Técnico', 'Penalizaciones']
            resumen = pd.merge(resumen, p_neg, on='Técnico', how='outer').fillna(0)
        else:
            resumen['Penalizaciones'] = 0.0

        resumen['PUNTUACIÓN NETA'] = (resumen['Puntos Base'] + resumen['Puntos Extra']) - resumen['Penalizaciones']
        st.dataframe(resumen.sort_values('PUNTUACIÓN NETA', ascending=False), use_container_width=True)

    # --- PESTAÑA: MATRIZ OPERATIVA (Conteo real de folios resueltos) ---
    with t_matriz:
        st.header("📋 Folios Resueltos por Categoría")
        matriz = df_res.groupby(['Técnico', 'Categoría']).size().unstack(fill_value=0)
        st.dataframe(matriz, use_container_width=True)

    # --- PESTAÑA: TOP FALLAS (Basado en el rango de meses configurado) ---
    with t_top:
        st.header(f"🔝 Series con mayor recurrencia (Últimos {meses_atras_reinc} meses)")
        df_total_rango = pd.concat([historial, df_actual])
        top_fallas = df_total_rango[df_total_rango['Categoría'] == 'CORRECTIVO'].groupby(['Serie', cliente_col]).size().reset_index(name='Veces Falló')
        st.table(top_fallas.sort_values('Veces Falló', ascending=False).head(10))

    # (Las demás pestañas de Extras y Detalle de Penalizaciones se mantienen con la lógica de visualización previa)
