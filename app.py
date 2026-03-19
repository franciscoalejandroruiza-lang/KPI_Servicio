import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Auditoría Real", layout="wide")

def main():
    st.title("🛡️ Auditoría SenAudit Pro")
    st.markdown("Cálculo de penalizaciones por reincidencia (Garantía Móvil).")

    # Selector de tipo de archivo para mayor flexibilidad
    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio", type=["xlsx", "xlsb"])

    if archivo:
        try:
            # 1. Carga de datos (Soporta Excel y XLSB)
            engine = 'openpyxl' if archivo.name.endswith('xlsx') else 'pyxlsb'
            df = pd.read_excel(archivo, engine=engine)
            df.columns = df.columns.str.strip()
            
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Normalización
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            
            # 2. Parámetros de la interfaz
            st.sidebar.header("Parámetros de Auditoría")
            dias_garantia = st.sidebar.slider("Días de garantía (Reincidencia)", 1, 365, 90)
            
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = st.sidebar.selectbox("Mes a visualizar", meses_nombres, index=datetime.now().month - 1)
            mes_num = meses_nombres.index(mes_sel) + 1
            anio_eval = st.sidebar.number_input("Año", value=2026)

            # --- LÓGICA MATEMÁTICA CON PANDAS ---
            
            # Ordenamos todo el historial cronológicamente por serie
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # "Shift" para traer la fecha del siguiente folio de la misma serie
            df['Fecha_Siguiente'] = df.groupby(col_serie)['Fecha_DT'].shift(-1)
            df['Folio_Siguiente'] = df.groupby(col_serie)['Folio'].shift(-1)
            
            # Cálculo de la diferencia de días (Delta T)
            df['Dias_Reincidencia'] = (df['Fecha_Siguiente'] - df['Fecha_DT']).dt.days

            # Definición de condiciones de penalización
            # El último folio de cada serie tendrá Dias_Reincidencia como NaN, 
            # por lo que automáticamente NO será penalizado (es el "Intocable").
            es_correctivo = df['Categoría'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            es_resuelta = df['Estatus'].astype(str).str.upper().str.contains('RESUELTA', na=False)
            dentro_garantia = (df['Dias_Reincidencia'] >= 0) & (df['Dias_Reincidencia'] <= dias_garantia)

            df['Es_Penalizacion'] = (es_correctivo & es_resuelta & dentro_garantia).astype(int)

            # --- FILTRADO POR MES SELECCIONADO ---
            # Ahora que ya calculamos sobre TODO el historial, filtramos solo lo que el usuario quiere ver
            mask_mes = (df['Fecha_DT'].dt.month == mes_num) & (df['Fecha_DT'].dt.year == anio_eval)
            df_mes = df[mask_mes].copy()

            # --- INTERFAZ DE RESULTADOS ---
            c1, c2 = st.columns([1, 1])
            with c1:
                st.subheader(f"📊 Eficiencia: {mes_sel} {anio_eval}")
                resumen = df_mes.groupby('Técnico').agg(
                    Total_Correctivos=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                
                resumen['% Efectividad'] = 100.0
                mask_total = resumen['Total_Correctivos'] > 0
                resumen.loc[mask_total, '% Efectividad'] = (
                    (resumen['Total_Correctivos'] - resumen['Penalizaciones']) / resumen['Total_Correctivos'] * 100
                ).round(1)
                
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with c2:
                st.subheader("🔍 Buscador de Evidencia")
                tec_auditar = st.text_input("Nombre del técnico:").upper()
                if tec_auditar:
                    filtro_tec = df_mes[df_mes['Técnico'].str.contains(tec_auditar, na=False)]
                    st.metric(f"Penalizaciones en {mes_sel}", filtro_tec['Es_Penalizacion'].sum())

            st.divider()
            st.subheader(f"📋 Listado de Reincidencias Detectadas ({mes_sel})")
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            
            if not evidencia.empty:
                cols_final = ['Folio', 'Técnico', col_serie, 'Fecha_DT', 'Dias_Reincidencia', 'Folio_Siguiente']
                st.dataframe(
                    evidencia[cols_final].rename(columns={
                        'Fecha_DT': 'Fecha Original',
                        'Dias_Reincidencia': 'Días p/ Fallar',
                        'Folio_Siguiente': 'Folio Reincidente'
                    }), 
                    use_container_width=True, hide_index=True
                )
            else:
                st.success(f"Excelente: No hay reincidencias en {mes_sel} con garantía de {dias_garantia} días.")

        except Exception as e:
            st.error(f"Se produjo un error al procesar el archivo: {e}")
    else:
        st.info("👈 Por favor, carga tu archivo para iniciar el análisis.")

if __name__ == "__main__":
    main()
