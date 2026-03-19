import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="SenAudit Pro - Ventana 3 Meses", layout="wide")

def main():
    st.title("🛡️ Auditoría SenAudit Pro")
    st.markdown("Análisis de Reincidencias: Mes seleccionado + 2 meses anteriores.")

    archivo = st.sidebar.file_uploader("Subir Reporte (.xlsx, .xlsb)", type=["xlsx", "xlsb"])

    if archivo:
        try:
            # 1. Carga de datos
            engine = 'openpyxl' if archivo.name.endswith('xlsx') else 'pyxlsb'
            df = pd.read_excel(archivo, engine=engine)
            df.columns = df.columns.str.strip()
            
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            
            # 2. Configuración de la Ventana (Febrero -> Ene, Dic)
            st.sidebar.header("Configuración de Ventana")
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = st.sidebar.selectbox("Mes de Corte", meses_nombres, index=datetime.now().month - 1)
            anio_sel = st.sidebar.number_input("Año", value=2026)
            
            # Calculamos el rango: Mes seleccionado y 2 atrás
            fecha_fin = datetime(anio_sel, meses_nombres.index(mes_sel) + 1, 1) + pd.offsets.MonthEnd(0)
            fecha_inicio = (fecha_fin - pd.DateOffset(months=2)).replace(day=1)
            
            st.sidebar.info(f"📅 Auditando desde: {fecha_inicio.strftime('%d/%m/%Y')} hasta: {fecha_fin.strftime('%d/%m/%Y')}")

            # 3. LÓGICA MATEMÁTICA DE VENTANA
            # Filtramos el DataFrame para que SOLO existan datos de esos 3 meses
            df_ventana = df[(df['Fecha_DT'] >= fecha_inicio) & (df['Fecha_DT'] <= fecha_fin)].copy()
            
            # Ordenamos por serie y fecha
            df_ventana = df_ventana.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # Identificamos el siguiente folio para calcular la reincidencia
            df_ventana['Fecha_Sig'] = df_ventana.groupby(col_serie)['Fecha_DT'].shift(-1)
            df_ventana['Folio_Sig'] = df_ventana.groupby(col_serie)['Folio'].shift(-1)
            df_ventana['Dias_Diff'] = (df_ventana['Fecha_Sig'] - df_ventana['Fecha_DT']).dt.days

            # Reglas de Penalización
            dias_garantia = 90 # Tu estándar de 3 meses
            es_correctivo = df_ventana['Categoría'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            es_resuelta = df_ventana['Estatus'].astype(str).str.upper().str.contains('RESUELTA', na=False)
            
            # Penaliza si hay un folio posterior dentro de los 90 días en este periodo de 3 meses
            df_ventana['Es_Penalizacion'] = (es_correctivo & es_resuelta & (df_ventana['Dias_Diff'] <= dias_garantia)).astype(int)

            # --- RESULTADOS TOTALES DE LA VENTANA ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader(f"Resumen Acumulado (3 meses)")
                resumen = df_ventana.groupby('Técnico').agg(
                    Folios_Totales=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                resumen['% Efectividad'] = ((resumen['Folios_Totales'] - resumen['Penalizaciones']) / resumen['Folios_Totales'] * 100).round(1)
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with c2:
                st.subheader("Auditor por Técnico")
                tec = st.text_input("Nombre del técnico (ej: ALEJANDRO RUIZ):").upper()
                if tec:
                    datos_tec = df_ventana[df_ventana['Técnico'].str.contains(tec, na=False)]
                    total_p = datos_tec['Es_Penalizacion'].sum()
                    st.metric(f"Penalizaciones totales en ventana", total_p)
                    
                    # Mostrar por mes para ver de dónde vienen los puntos
                    st.write("Desglose por mes:")
                    st.write(datos_tec.groupby(datos_tec['Fecha_DT'].dt.month_name())['Es_Penalizacion'].sum())

            st.divider()
            st.subheader("📋 Detalle de Reincidencias (Evidencia)")
            evidencia = df_ventana[df_ventana['Es_Penalizacion'] == 1]
            if not evidencia.empty:
                st.dataframe(evidencia[[col_serie, 'Folio', 'Técnico', 'Fecha_DT', 'Dias_Diff', 'Folio_Sig']], use_container_width=True)

        except Exception as e:
            st.error(f"Error en el proceso: {e}")
