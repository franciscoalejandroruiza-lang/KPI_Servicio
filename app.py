import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Configuración de la interfaz
st.set_page_config(page_title="SenAudit Pro - Historial Completo", layout="wide")

def main():
    st.title("📊 Análisis de Productividad (Basado en Historial)")
    
    st.sidebar.header("Configuración de Auditoría")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:
        # 1. Carga de datos
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo, engine='openpyxl')
        
        # Limpieza y conversión de fechas
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        df = df.dropna(subset=['Fecha_DT', 'Folio', 'N.° de serie'])

        # 2. Configuración de Rango
        meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                      7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        col1, col2 = st.sidebar.columns(2)
        mes_eval = col1.selectbox("Mes a evaluar", options=range(1, 13), format_func=lambda x: meses_dict[x], index=1)
        anio_eval = col2.number_input("Año", value=2026)
        
        # Ahora solo dependemos de los meses de historial
        meses_atras = st.sidebar.slider("Meses de historial (retroactivo)", 1, 6, 3)

        # 3. Cálculo de Fechas
        fecha_fin = datetime(anio_eval, mes_eval, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio = datetime(anio_eval, mes_eval, 1) - relativedelta(months=meses_atras)

        # 4. Procesamiento de Reincidencias (Cualquier correctivo previo en el historial)
        mask_rango = (df['Fecha_DT'] >= pd.Timestamp(fecha_inicio)) & (df['Fecha_DT'] <= pd.Timestamp(fecha_fin))
        df_rango = df.loc[mask_rango].copy().drop_duplicates(subset=['Folio'])

        # Ordenamos: Serie (A-Z) y Fecha (Más reciente arriba)
        df_rango = df_rango.sort_values(['N.° de serie', 'Fecha_DT'], ascending=[True, False])

        df_rango['Es_Reincidente'] = False

        for serie, grupo in df_rango.groupby('N.° de serie'):
            if len(grupo) > 1:
                indices = grupo.index
                # Como están ordenados por fecha desc, el i es más nuevo que i+1
                for i in range(len(indices) - 1):
                    # REGLA: Si existe un folio anterior en el historial y fue CORRECTIVO, se penaliza
                    if str(df_rango.loc[indices[i+1], 'Categoría']).upper() == 'CORRECTIVO':
                        df_rango.loc[indices[i+1], 'Es_Reincidente'] = True

        # 5. Filtrar para el reporte del mes seleccionado
        mask_mes_eval = (df_rango['Fecha_DT'].dt.month == mes_eval) & (df_rango['Fecha_DT'].dt.year == anio_eval)
        df_reporte = df_rango.loc[mask_mes_eval]

        # --- MÉTRICAS ---
        resueltos_totales = len(df_reporte)
        penalizados_totales = int(df_reporte['Es_Reincidente'].sum())
        efectividad = ((resueltos_totales - penalizados_totales) / resueltos_totales * 100) if resueltos_totales > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Reportes Resueltos", resueltos_totales)
        m2.metric("Penalizaciones (Historial)", penalizados_totales, delta_color="inverse")
        m3.metric("Efectividad Real", f"{efectividad:.1f}%")

        st.markdown("---")

        # --- RELACIÓN POR TÉCNICO ---
        st.subheader(f"📊 Relación por Técnico - {meses_dict[mes_eval]} (Historial: {meses_atras} meses)")
        
        resumen = df_reporte.groupby('Técnico').agg(
            Resueltos=('Folio', 'count'),
            Penalizados=('Es_Reincidente', 'sum')
        ).reset_index()
        
        resumen['Efectividad %'] = ((resumen['Resueltos'] - resumen['Penalizados']) / resumen['Resueltos'] * 100).round(1)
        resumen = resumen.sort_values('Resueltos', ascending=False)
        
        st.dataframe(
            resumen.style.background_gradient(subset=['Efectividad %'], cmap='RdYlGn'),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("👋 Carga el archivo Excel para analizar el historial.")

if __name__ == "__main__":
    main()
