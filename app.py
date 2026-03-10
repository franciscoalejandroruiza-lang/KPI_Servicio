import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="Confiabilidad Técnica | SenIntegral", layout="wide")

# Inicialización de estados
if 'lista_extras' not in st.session_state: st.session_state.lista_extras = []
if 'pesos_dict' not in st.session_state: st.session_state.pesos_dict = {}

MESES_MAP = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}

st.title("🛡️ Gestión de Confiabilidad Técnica - SenIntegral")

# --- BARRA LATERAL ---
st.sidebar.header("📁 Panel de Datos")
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])
meses_atras_reinc = st.sidebar.slider("Ventana de historial (Meses)", 1, 12, 3)

if archivo_subido:
    # Carga y limpieza
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    # Estandarización de nombres de columnas
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    cliente_col = "Nombre comercial" if "Nombre comercial" in df.columns else "Cliente"
    
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)

    periodos = df.sort_values('Fecha recepción', ascending=False)['Mes_Año'].unique()
    periodo_sel = st.sidebar.selectbox("📅 Seleccionar Mes a Evaluar:", periodos)

    # --- PESTAÑAS ---
    t_resumen, t_matriz, t_penalizaciones, t_top, t_adicionales, t_config = st.tabs([
        "📈 Puntaje Final", "📋 Matriz Operativa", "⚠️ Detalle Penalizaciones", "🔝 Top Fallas", "📝 Actividades Extras", "⚙️ Configuración"
    ])

    # --- LÓGICA DE PROCESAMIENTO ---
    df_actual = df[df['Mes_Año'] == periodo_sel].copy()
    fecha_inicio_mes = df_actual['Fecha recepción'].min()
    fecha_limite_hist = fecha_inicio_mes - pd.DateOffset(months=meses_atras_reinc)
    
    # Historial para buscar recurrencias
    historial = df[(df['Fecha recepción'] < fecha_inicio_mes) & (df['Fecha recepción'] >= fecha_limite_hist)]
    
    # Solo tomamos lo RESUELTO para el puntaje base
    df_res = df_actual[df_actual['Estatus'] == 'RESUELTA'].copy()

    with t_config:
        st.header("⚙️ Configuración de Calidad")
        for cat in sorted(df['Categoría'].unique()):
            st.session_state.pesos_dict[cat] = st.slider(f"Puntos por {cat}:", -5.0, 20.0, st.session_state.pesos_dict.get(cat, 1.0), 0.5)
        val_reinc = st.number_input("Descuento por cada reincidencia previa:", 0.0, 10.0, 2.0)

    # --- CÁLCULO DE PENALIZACIONES CON EXCLUSIÓN ---
    df_res['Pts_Base'] = df_res['Categoría'].map(st.session_state.pesos_dict).fillna(0.0)
    lista_penalizaciones = []

    # En la configuración, bajamos el valor por defecto a 1.0 para que no sea tan agresivo
    with t_config:
        st.header("⚙️ Configuración de Calidad")
        # ... (tus otros sliders de categorías)
        val_reinc = st.number_input("Descuento por cada reincidencia previa:", 0.0, 10.0, 1.0) # Ahora por defecto es 1.0

    for _, fila in df_res.iterrows():
        if fila['Categoría'] == 'CORRECTIVO':
            # Buscamos fallas previas de esta serie
            anteriores = historial[(historial['Serie'] == fila['Serie']) & (historial['Categoría'] == 'CORRECTIVO')]
            
            for _, ant in anteriores.iterrows():
                # REGLA 1: No penalizar al técnico que resolvió hoy
                # REGLA 2: No penalizar si el técnico anterior es "CHI SISTEMAS"
                tec_anterior = str(ant['Técnico']).upper().strip()
                
                if ant['Técnico'] != fila['Técnico'] and "CHI SISTEMAS" not in tec_anterior:
                    lista_penalizaciones.append({
                        'Técnico': ant['Técnico'],
                        'Serie': fila['Serie'],
                        'Cliente': fila[cliente_col],
                        'Folio Detonante': fila['Folio'],
                        'Fecha Falla Previa': ant['Fecha recepción'].strftime('%Y-%m-%d'),
                        'Puntos Negativos': val_reinc
                    })

    df_pen = pd.DataFrame(lista_penalizaciones)
    # --- PESTAÑA: PUNTAJE FINAL ---
    with t_resumen:
        # 1. Base
        res = df_res.groupby('Técnico')['Pts_Base'].sum().reset_index()
        
        # 2. Extras
        df_ex = pd.DataFrame(st.session_state.lista_extras)
        if not df_ex.empty:
            ex_sum = df_ex[df_ex['Periodo'] == periodo_sel].groupby('Técnico')['Puntos Extra'].sum().reset_index()
            res = pd.merge(res, ex_sum, on='Técnico', how='outer').fillna(0)
        else:
            res['Puntos Extra'] = 0.0

        # 3. Penalizaciones
        if not df_pen.empty:
            pen_sum = df_pen.groupby('Técnico')['Puntos Negativos'].sum().reset_index()
            res = pd.merge(res, pen_sum, on='Técnico', how='outer').fillna(0)
        else:
            res['Puntos Negativos'] = 0.0

        res['TOTAL NETO'] = (res['Pts_Base'] + res['Puntos Extra']) - res['Puntos Negativos']
        st.dataframe(res.sort_values('TOTAL NETO', ascending=False), use_container_width=True)

    # --- PESTAÑA: MATRIZ OPERATIVA ---
    with t_matriz:
        st.header("📋 Conteo de Folios Resueltos")
        st.dataframe(df_res.groupby(['Técnico', 'Categoría']).size().unstack(fill_value=0), use_container_width=True)

# --- PESTAÑA: DETALLE DE PENALIZACIONES (Agrupado por Técnico) ---
    with t_penalizaciones:
        st.header("⚠️ Auditoría de Reincidencias por Técnico")
        
        if not df_pen.empty:
            st.info("""
                **Nota de Transparencia:** Las penalizaciones se asignan a los técnicos que atendieron 
                el equipo anteriormente sin resolver la falla de raíz. El técnico que resolvió 
                el problema en el mes actual NO es penalizado.
            """)
            
            # Agrupamos por técnico para que cada uno vea su detalle
            tecnicos_penalizados = sorted(df_pen['Técnico'].unique())
            
            for tec in tecnicos_penalizados:
                with st.expander(f"👤 Detalles para: {tec}"):
                    df_tec_especifico = df_pen[df_pen['Técnico'] == tec].copy()
                    
                    # Renombramos para mayor claridad en la tabla del técnico
                    df_tec_view = df_tec_especifico[[
                        'Serie', 'Cliente', 'Fecha Falla Previa', 'Folio Detonante', 'Puntos Negativos'
                    ]].rename(columns={
                        'Fecha Falla Previa': 'Tu Visita Anterior',
                        'Folio Detonante': 'Folio que Reincidió',
                        'Puntos Negativos': 'Deducción'
                    })
                    
                    st.table(df_tec_view)
                    st.caption(f"Total de penalizaciones para {tec}: {len(df_tec_especifico)}")
        else:
            st.success("✅ No se detectaron fallas recurrentes en el historial analizado.")
    # --- PESTAÑA: TOP FALLAS ---
    with t_top:
        st.header(f"🔝 Equipos con más fallas (Ventana de {meses_atras_reinc} meses)")
        df_rango = pd.concat([historial, df_actual])
        top = df_rango[df_rango['Categoría'] == 'CORRECTIVO'].groupby(['Serie', cliente_col]).size().reset_index(name='Total Fallas')
        st.table(top.sort_values('Total Fallas', ascending=False).head(10))

    # --- PESTAÑA: ACTIVIDADES EXTRAS ---
    with t_adicionales:
        with st.form("extras"):
            c1, c2, c3 = st.columns(3)
            t_ex = c1.selectbox("Técnico", sorted(df['Técnico'].unique()))
            desc_ex = c2.text_input("Descripción")
            pts_ex = c3.number_input("Puntos", value=1.0)
            if st.form_submit_button("Registrar"):
                st.session_state.lista_extras.append({'Técnico': t_ex, 'Actividad': desc_ex, 'Puntos Extra': pts_ex, 'Periodo': periodo_sel})
                st.rerun()

else:
    st.info("Por favor, sube el archivo Excel para iniciar la auditoría de SenIntegral.")
