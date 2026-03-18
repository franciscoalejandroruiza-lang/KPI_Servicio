import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro - Auditoría Dominó", layout="wide")

def main():
    st.title("🛡️ Auditoría: Penalizaciones por Antecedentes")
    
    st.sidebar.header("Configuración")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:
        # 1. Carga de datos
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo, engine='openpyxl')
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        df = df.dropna(subset=['Fecha_DT', 'Folio', 'N.° de serie'])

        # 2. Selectores
        meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                      7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        col1, col2 = st.sidebar.columns(2)
        mes_eval = col1.selectbox("Mes a evaluar", options=range(1, 13), format_func=lambda x: meses_dict[x], index=datetime.now().month - 1)
        anio_eval = col2.number_input("Año", value=2026)
        meses_atras = st.sidebar.slider("Meses de historial (retroactivo)", 1, 12, 3)

        # 3. Definición de Rangos
        fecha_fin_eval = datetime(anio_eval, mes_eval, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio_historial = datetime(anio_eval, mes_eval, 1) - relativedelta(months=meses_atras)

        # 4. LÓGICA DE PENALIZACIÓN DOMINÓ
        # Filtramos todo el rango para el análisis
        mask_rango = (df['Fecha_DT'] >= pd.Timestamp(fecha_inicio_historial)) & (df['Fecha_DT'] <= pd.Timestamp(fecha_fin_eval))
        df_analisis = df.loc[mask_rango].copy().sort_values(['N.° de serie', 'Fecha_DT'], ascending=True)

        df_analisis['Es_Penalizacion'] = 0

        for serie, grupo in df_analisis.groupby('N.° de serie'):
            if len(grupo) > 1:
                # El último folio de la serie (el más reciente en el tiempo)
                ultimo_idx = grupo.index[-1]
                
                # Todos los folios anteriores al último
                anteriores_indices = grupo.index[:-1]
                
                for idx in anteriores_indices:
                    # REGLA: Si el anterior es CORRECTIVO, se penaliza
                    if str(df_analisis.loc[idx, 'Categoría']).upper() == 'CORRECTIVO':
                        df_analisis.loc[idx, 'Es_Penalizacion'] = 1

        # 5. Filtrado para mostrar resultados del mes seleccionado
        # Nota: Mostramos penalizaciones que OCURRIERON en el mes evaluado o historial según prefieras.
        # Siguiendo tu lógica, penalizamos a todos los que fallaron antes del último.
        df_mes_actual = df_analisis[(df_analisis['Fecha_DT'].dt.month == mes_eval) & (df_analisis['Fecha_DT'].dt.year == anio_eval)]

        # --- INTERFAZ ---
        tab1, tab2 = st.tabs(["📊 Resumen de Productividad", "⚠️ Tabla de Penalizaciones"])

        with tab1:
            st.subheader(f"Reportes Totales - {meses_dict[mes_eval]}")
            prod = df_mes_actual.groupby('Técnico').size().reset_index(name='reportes_resueltos')
            st.dataframe(prod.sort_values('reportes_resueltos', ascending=False), use_container_width=True, hide_index=True)

        with tab2:
            st.subheader(f"Penalizaciones Acumuladas (Antecesores)")
            # Aquí sumamos las penalizaciones detectadas en todo el rango analizado (Historial + Mes)
            # para que aparezcan los de meses anteriores como Alejandro o Carlos
            resumen_penal = df_analisis[df_analisis['Es_Penalizacion'] == 1].groupby('Técnico').size().reset_index(name='penalizaciones')
            
            st.table(resumen_penal.sort_values('penalizaciones', ascending=False))

    else:
        st.info("Carga el archivo para ver el efecto dominó de las penalizaciones.")

if __name__ == "__main__":
    main()
