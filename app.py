import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración profesional
st.set_page_config(page_title="SenAudit Pro - Control de Reincidencias", layout="wide")

def main():
    st.title("🛠️ Sistema de Auditoría de Servicio Técnico")
    st.markdown("---")

    # --- SIDEBAR ---
    st.sidebar.header("Panel de Control")
    uploaded_file = st.sidebar.file_uploader("Cargar Reporte de Órdenes de Servicio", type=["xlsx", "csv"])
    
    # Parámetro crítico: ¿Cuántos días atrás buscamos fallos previos?
    ventana_reincidencia = st.sidebar.slider("Ventana de reincidencia (Días)", 1, 30, 7)
    
    if uploaded_file:
        # Carga de datos (maneja CSV o Excel)
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file, engine='openpyxl')

        # 1. Limpieza y Normalización
        df = preparar_datos(df)

        # 2. Lógica de Reincidencias y Penalizaciones
        # El folio más reciente es el actual, los anteriores en la ventana se penalizan
        df_analizado = analizar_penalizaciones(df, ventana_reincidencia)

        # --- DASHBOARD ---
        total_folios = len(df_analizado)
        total_penalizados = df_analizado["Es_Reincidente"].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Folios Totales", total_folios)
        col2.metric("Reportes Penalizados", int(total_penalizados), delta="Reincidencias", delta_color="inverse")
        col3.metric("% Efectividad", f"{((total_folios - total_penalizados) / total_folios * 100):.1f}%")

        # --- GRÁFICOS ---
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Penalizaciones por Técnico")
            penalizaciones_tec = df_analizado[df_analizado["Es_Reincidente"]].groupby("Técnico").size().reset_index(name="Total")
            fig = px.bar(penalizaciones_tec, x="Técnico", y="Total", color="Total", color_continuous_scale="Reds")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Top 5 Series con más Fallos")
            top_series = df_analizado.groupby("Serie").size().nlargest(5).reset_index(name="Fallas")
            fig2 = px.pie(top_series, names="Serie", values="Fallas", hole=0.3)
            st.plotly_chart(fig2, use_container_width=True)

        # --- TABLA DE DETALLE ---
        st.subheader("📋 Detalle de Folios y Penalizaciones")
        # Estilo para resaltar las penalizaciones en rojo
        st.dataframe(
            df_analizado.style.apply(lambda x: ['background-color: #ffcccc' if x.Es_Reincidente else '' for _ in x], axis=1),
            use_container_width=True
        )

def preparar_datos(df):
    """Mapeo de columnas según el archivo real del usuario"""
    mapa = {
        'N.° de serie': 'Serie',
        'Última visita': 'Fecha',
        'Folio': 'Folio',
        'Técnico': 'Técnico',
        'Estatus': 'Estatus'
    }
    df = df.rename(columns=mapa)
    
    # Convertir fecha y ordenar por serie y fecha (fundamental para la lógica)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    # Ordenamos por Folio de forma descendente para que el más nuevo esté arriba
    df = df.sort_values(by=['Serie', 'Fecha'], ascending=[True, False])
    return df

def analizar_penalizaciones(df, dias):
    """
    Lógica: Para cada serie, el folio más reciente (primero en el tiempo) es el que cuenta.
    Si existen folios previos de la misma serie dentro de 'N' días, esos se marcan como penalizados.
    """
    df['Es_Reincidente'] = False
    
    for serie, grupo in df.groupby('Serie'):
        if len(grupo) > 1:
            # Iteramos por cada registro para comparar con el anterior cronológico
            # Nota: Al estar ordenados desc, comparamos la fila actual con la siguiente (que es la anterior en el tiempo)
            indices = grupo.index
            for i in range(len(indices) - 1):
                fecha_actual = df.loc[indices[i], 'Fecha']
                fecha_anterior = df.loc[indices[i+1], 'Fecha']
                
                diferencia = (fecha_actual - fecha_anterior).days
                
                # Si la visita anterior ocurrió hace menos de 'X' días, se penaliza
                if diferencia <= dias:
                    df.loc[indices[i+1], 'Es_Reincidente'] = True
                    
    return df

if __name__ == "__main__":
    main()
