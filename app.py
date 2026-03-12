import streamlit as st
import pandas as pd

# 1. CONFIGURACIÓN
st.set_page_config(page_title="SenAudit Pro - Auditoría 3008454 Final", layout="wide")

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

st.title("📊 SenAudit Pro - Reporte de Reincidencias (7 Goles)")

# --- CONFIGURACIÓN LATERAL ---
st.sidebar.header("⚙️ Ajustes de Auditoría")
archivo_subido = st.sidebar.file_uploader("Subir reporte Excel/CSV", type=["xlsx", "csv"])
meses_rastreo = st.sidebar.slider("Rastreo hacia atrás (Meses)", 1, 12, 4)

if archivo_subido:
    # CARGA Y NORMALIZACIÓN
    df = pd.read_excel(archivo_subido) if archivo_subido.name.endswith('.xlsx') else pd.read_csv(archivo_subido, encoding='latin-1')
    df.columns = df.columns.str.strip()
    
    df.rename(columns={col: "Serie" for col in df.columns if "serie" in col.lower()}, inplace=True)
    df['Serie'] = df['Serie'].astype(str).str.strip().str.lstrip('0')
    df['Técnico'] = df['Técnico'].astype(str).str.replace('CH ', '', regex=False).str.replace('CHI ', '', regex=False).str.strip().str.upper()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    df = df.dropna(subset=['Fecha recepción', 'Técnico', 'Serie'])
    
    if 'Categoría' in df.columns:
        df['Categoría'] = df['Categoría'].astype(str).str.upper().str.strip()

    df['Mes_Año'] = df['Fecha recepción'].dt.month_name().map(MESES_MAP) + " " + df['Fecha recepción'].dt.year.astype(str)
    periodo_sel = st.sidebar.selectbox("📅 Seleccionar Mes para Reporte Final:", df['Mes_Año'].unique())

    # --- MOTOR DE PENALIZACIÓN INDIVIDUAL POR FOLIO ---
    # Ordenamos cronológicamente para no perder la cadena
    df_global = df.sort_values('Fecha recepción')
    lista_penalizaciones = []

    # Analizamos todos los eventos que son fallas reportadas
    detonantes = df_global[df_global['Categoría'].isin(['CORRECTIVO', 'REINCIDENCIA'])]

    for _, fila_falla in detonantes.iterrows():
        # Límite temporal
        limite_h = fila_falla['Fecha recepción'] - pd.DateOffset(months=meses_rastreo)
        
        # Buscamos quién fue el ÚLTIMO en ver esta serie antes de ESTE folio
        historial = df[
            (df['Serie'] == fila_falla['Serie']) & 
            (df['Fecha recepción'] < fila_falla['Fecha recepción']) &
            (df['Fecha recepción'] >= limite_h)
        ].sort_values('Fecha recepción', ascending=False)
        
        if not historial.empty:
            visita_previa = historial.iloc[0]
            tec_previo = visita_previa['Técnico']
            
            # Si el técnico previo no es el mismo que reporta
            if tec_previo != fila_falla['Técnico']:
                lista_penalizaciones.append({
                    'Técnico Penalizado': tec_previo,
                    'Serie': fila_falla['Serie'],
                    'Folio Su Visita': visita_previa['Folio'],
                    'Fecha Visita': visita_previa['Fecha recepción'].strftime('%d/%m/%y %H:%M'),
                    'Folio Detonante (Falla)': fila_falla['Folio'],
                    'Fecha Falla': fila_falla['Fecha recepción'].strftime('%d/%m/%y %H:%M'),
                    'Mes de la Falla': fila_falla['Mes_Año'],
                    'Puntos': 1.0
                })

    df_pen_total = pd.DataFrame(lista_penalizaciones)

    # --- PESTAÑAS ---
    t_puntos, t_serie_critica = st.tabs(["📈 Resumen Mensual", "📋 Detalle Serie 3008454"])

    with t_puntos:
        # Puntos positivos de febrero (Iván y Pedro)
        df_mes = df[df['Mes_Año'] == periodo_sel].copy()
        resumen = df_mes[df_mes['Estatus'] == 'RESUELTA'].groupby('Técnico').size().reset_index(name='Visitas')
        resumen['Pts_Ganados'] = resumen['Visitas'] * 1.0
        
        # Penalizaciones detonadas en el mes seleccionado
        if not df_pen_total.empty:
            p_mes = df_pen_total[df_pen_total['Mes de la Falla'] == periodo_sel].groupby('Técnico Penalizado')['Puntos'].sum().reset_index()
            p_mes.columns = ['Técnico', 'Penalización']
            resumen = pd.merge(resumen, p_mes, on='Técnico', how='left').fillna(0)
        else:
            resumen['Penalización'] = 0.0

        resumen['TOTAL'] = resumen['Pts_Ganados'] - resumen['Penalización']
        st.table(resumen.sort_values('TOTAL', ascending=False))

    with t_serie_critica:
        st.header("Análisis de los 7 Eventos de la Serie 3008454")
        df_3008454 = df_pen_total[df_pen_total['Serie'] == '3008454']
        
        if not df_3008454.empty:
            st.write("Esta tabla muestra la cadena completa de responsabilidades:")
            st.table(df_3008454[['Técnico Penalizado', 'Folio Su Visita', 'Fecha Visita', 'Folio Detonante (Falla)', 'Fecha Falla']])
            
            st.divider()
            st.subheader("Resumen de Penalizaciones Aplicadas:")
            resumen_serie = df_3008454.groupby('Técnico Penalizado').size().reset_index(name='Puntos Menos')
            st.dataframe(resumen_serie)
        else:
            st.info("Ajusta el slider de meses para incluir el historial de diciembre.")
else:
    st.info("Sube el archivo para generar la auditoría.")
