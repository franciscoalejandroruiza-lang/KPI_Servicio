import streamlit as st
import pandas as pd
from datetime import datetime
import calendar

st.set_page_config(page_title="SenAudit Pro - Ventana Deslizante", layout="wide")

def main():
    # --- INTERFAZ: ENCABEZADO ---
    st.title("🛡️ Auditoría SenAudit Pro")
    st.markdown("### Análisis de Reincidencias (Ventana de 3 Meses)")
    st.info("Al seleccionar un mes, el sistema analizará ese mes y los dos anteriores para detectar reincidencias.")

    # --- INTERFAZ: BARRA LATERAL (FILTROS) ---
    st.sidebar.header("📂 Carga y Configuración")
    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio", type=["xlsx", "xlsb", "csv"])

    if archivo:
        try:
            # Determinación del motor de lectura
            if archivo.name.endswith('xlsb'):
                df = pd.read_excel(archivo, engine='pyxlsb')
            elif archivo.name.endswith('csv'):
                df = pd.read_csv(archivo)
            else:
                df = pd.read_excel(archivo, engine='openpyxl')

            df.columns = df.columns.str.strip()
            
            # Identificación de columnas críticas
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Normalización de datos
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            df = df.dropna(subset=['Fecha_DT', col_serie])

            # --- SELECTORES DE TIEMPO ---
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            
            mes_corte_nom = st.sidebar.selectbox("Mes de Corte (Final)", meses_nombres, index=1) # Default Febrero
            anio_corte = st.sidebar.number_input("Año", value=2026)
            
            # Cálculo matemático de la ventana de 3 meses
            mes_final_num = meses_nombres.index(mes_corte_nom) + 1
            fecha_fin = datetime(anio_corte, mes_final_num, 1) + pd.offsets.MonthEnd(0)
            fecha_inicio = (fecha_fin - pd.DateOffset(months=2)).replace(day=1)

            st.sidebar.success(f"Auditando: {fecha_inicio.strftime('%b %Y')} a {fecha_fin.strftime('%b %Y')}")

            # --- LÓGICA DE PROCESAMIENTO ---
            # 1. Filtrar solo los datos de la ventana de 3 meses
            df_ventana = df[(df['Fecha_DT'] >= fecha_inicio) & (df['Fecha_DT'] <= fecha_fin)].copy()
            df_ventana = df_ventana.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # 2. Calcular reincidencia (Mirar al siguiente folio de la misma serie)
            df_ventana['Fecha_Sig'] = df_ventana.groupby(col_serie)['Fecha_DT'].shift(-1)
            df_ventana['Folio_Sig'] = df_ventana.groupby(col_serie)['Folio'].shift(-1)
            df_ventana['Dias_Diff'] = (df_ventana['Fecha_Sig'] - df_ventana['Fecha_DT']).dt.days

            # 3. Marcar penalizaciones (Correctivo + Resuelta + <= 90 días)
            es_correctivo = df_ventana['Categoría'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            es_resuelta = df_ventana['Estatus'].astype(str).str.upper().str.contains('RESUELTA', na=False)
            df_ventana['Es_Penalizacion'] = (es_correctivo & es_resuelta & (df_ventana['Dias_Diff'] <= 90)).astype(int)

            # --- INTERFAZ: VISUALIZACIÓN DE RESULTADOS ---
            tab1, tab2 = st.tabs(["📈 Resumen de Técnicos", "📋 Detalle de Folios"])

            with tab1:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader(f"Penalizaciones Acumuladas ({mes_corte_nom} + 2 meses atrás)")
                    resumen = df_ventana.groupby('Técnico').agg(
                        Folios_Totales=('Folio', 'count'),
                        Penalizaciones=('Es_Penalizacion', 'sum')
                    ).reset_index()
                    
                    resumen['% Efectividad'] = ((resumen['Folios_Totales'] - resumen['Penalizaciones']) / resumen['Folios_Totales'] * 100).round(1)
                    st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

                with col2:
                    st.subheader("🔍 Filtro Rápido")
                    tec_buscado = st.text_input("Buscar técnico específico:").upper()
                    if tec_buscado:
                        puntos = df_ventana[df_ventana['Técnico'].str.contains(tec_buscado, na=False)]['Es_Penalizacion'].sum()
                        st.metric(label=f"Total Penalizaciones", value=int(puntos))
                        st.caption(f"Resultado para {tec_buscado} en el periodo seleccionado.")

            with tab2:
                st.subheader("Evidencia de Reincidencias")
                evidencia = df_ventana[df_ventana['Es_Penalizacion'] == 1]
                if not evidencia.empty:
                    st.write("Estos son los folios que el sistema marcó como fallidos:")
                    st.dataframe(
                        evidencia[[col_serie, 'Folio', 'Técnico', 'Fecha_DT', 'Dias_Diff', 'Folio_Sig']].rename(
                            columns={'Fecha_DT': 'Fecha Visita', 'Dias_Diff': 'Días p/ reincidir', 'Folio_Sig': 'Folio de Reincidencia'}
                        ), use_container_width=True, hide_index=True
                    )
                else:
                    st.success("No se encontraron reincidencias en este periodo.")

        except Exception as e:
            st.error(f"Error al procesar: {e}")
    else:
        st.warning("👈 Sube el archivo Excel o CSV en la barra lateral para comenzar.")

if __name__ == "__main__":
    main()
    
