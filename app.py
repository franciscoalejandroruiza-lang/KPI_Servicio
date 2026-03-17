import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro - Análisis Histórico", layout="wide")

def main():
    st.title("📊 Auditoría Técnica: Análisis por Ventana Mensual")
    st.markdown("---")

    st.sidebar.header("📅 Configuración del Periodo")
    uploaded_file = st.sidebar.file_uploader("Cargar Reporte Excel/CSV", type=["xlsx", "csv"])
    
    if uploaded_file:
        df = cargar_y_limpiar(uploaded_file)
        
        # --- FILTROS DE TIEMPO DINÁMICOS ---
        meses_nombres = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        
        mes_base = st.sidebar.selectbox("Mes de corte (Base)", options=range(1, 13), format_func=lambda x: meses_nombres[x], index=datetime.now().month - 1)
        anio_base = st.sidebar.number_input("Año", min_value=2020, max_value=2030, value=2025)
        meses_atras = st.sidebar.slider("Meses previos a incluir", 0, 6, 3)
        
        # Calcular rango de fechas
        fecha_fin = datetime(anio_base, mes_base, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio = datetime(anio_base, mes_base, 1) - relativedelta(months=meses_atras)
        
        st.sidebar.info(f"Analizando desde: **{fecha_inicio.strftime('%d/%m/%Y')}** hasta **{fecha_fin.strftime('%d/%m/%Y')}**")

        # Filtrar DF por el rango seleccionado
        mask = (df['Fecha'] >= pd.Timestamp(fecha_inicio)) & (df['Fecha'] <= pd.Timestamp(fecha_fin))
        df_filtrado = df.loc[mask].copy()

        if not df_filtrado.empty:
            # --- LÓGICA DE PENALIZACIONES ---
            # Identificar reincidencias (ventana de 15 días por defecto entre reportes)
            df_final = calcular_penalizaciones_avanzado(df_filtrado)

            # --- MÉTRICAS ---
            c1, c2, c3 = st.columns(3)
            c1.metric("Folios en Periodo", len(df_final))
            c2.metric("Penalizados (Anteriores)", df_final["Es_Reincidente"].sum())
            c3.metric("Meses Analizados", meses_atras + 1)

            # --- GRÁFICOS ---
            st.subheader(f"Desempeño de Técnicos: {meses_nombres[mes_base]}")
            fig = px.bar(df_final.groupby(["Técnico", "Es_Reincidente"]).size().reset_index(name="Cant"), 
                         x="Técnico", y="Cant", color="Es_Reincidente",
                         title="Relación de Folios Resueltos vs Penalizados",
                         color_discrete_map={True: "#EF553B", False: "#636EFA"},
                         labels={"Es_Reincidente": "Es Penalizado"})
            st.plotly_chart(fig, use_container_width=True)

            # --- TABLA ---
            st.subheader("📋 Detalle de Órdenes de Servicio")
            st.dataframe(df_final.style.apply(lambda x: ['background-color: #ffcccc' if x.Es_Reincidente else '' for _ in x], axis=1), use_container_width=True)
        else:
            st.warning("No hay datos para el rango de fechas seleccionado.")

def cargar_y_limpiar(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, engine='openpyxl')
    
    mapa = {'N.° de serie': 'Serie', 'Última visita': 'Fecha', 'Folio': 'Folio', 'Técnico': 'Técnico'}
    df = df.rename(columns=mapa)
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha', 'Serie'])
    # Ordenar: más reciente primero para cada serie
    df = df.sort_values(by=['Serie', 'Fecha'], ascending=[True, False])
    return df

def calcular_penalizaciones_avanzado(df):
    """
    Marca como reincidente cualquier folio que NO sea el más reciente 
    dentro de un historial de fallas cercano para la misma serie.
    """
    df['Es_Reincidente'] = False
    dias_ventana = 15 # Si falló en menos de 15 días, el anterior se penaliza
    
    for serie, grupo in df.groupby('Serie'):
        if len(grupo) > 1:
            indices = grupo.index
            for i in range(len(indices) - 1):
                # Comparamos el folio i (más nuevo) con el i+1 (más viejo)
                diff = (df.loc[indices[i], 'Fecha'] - df.loc[indices[i+1], 'Fecha']).days
                if diff <= dias_ventana:
                    # El folio anterior (i+1) es el que se penaliza porque no quedó bien
                    df.loc[indices[i+1], 'Es_Reincidente'] = True
    return df

if __name__ == "__main__":
    main()
