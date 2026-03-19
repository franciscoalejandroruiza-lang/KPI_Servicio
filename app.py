import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Auditoría de Calidad", layout="wide")

def main():
    st.title("🛡️ Auditoría de Efectividad: SenAudit Pro")
    st.markdown("### ¿El técnico hizo bien el trabajo a la primera?")

    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio", type=["xlsx", "xlsb"])

    if archivo:
        try:
            # 1. Carga de datos
            engine = 'openpyxl' if archivo.name.endswith('xlsx') else 'pyxlsb'
            df = pd.read_excel(archivo, engine=engine)
            df.columns = df.columns.str.strip()
            
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Limpieza y Formato
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            df = df.dropna(subset=['Fecha_DT', col_serie])

            # 2. Configuración de la Interfaz
            st.sidebar.header("Parámetros de Auditoría")
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            
            mes_sel = st.sidebar.selectbox("Mes a evaluar", meses_nombres, index=1) # Default Febrero
            anio_eval = st.sidebar.number_input("Año", value=2026) # Aquí se define la variable
            mes_num = meses_nombres.index(mes_sel) + 1

            # --- LÓGICA DE AUDITORÍA MATEMÁTICA ---
            
            # Ordenamos todo el historial para detectar reincidencias correctamente
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # Miramos al futuro: ¿Cuándo fue la siguiente visita de esta máquina?
            df['Sig_Fecha'] = df.groupby(col_serie)['Fecha_DT'].shift(-1)
            df['Sig_Folio'] = df.groupby(col_serie)['Folio'].shift(-1)
            df['Sig_Cat'] = df.groupby(col_serie)['Categoría'].shift(-1)
            
            # Diferencia de días hasta la reincidencia
            df['Dias_Garantia'] = (df['Sig_Fecha'] - df['Fecha_DT']).dt.days

            # DEFINICIÓN DE TRABAJO FALLIDO (Penalización):
            # El folio actual fue RESUELTO pero hubo otro CORRECTIVO en menos de 90 días.
            es_correctivo = df['Categoría'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            es_resuelta = df['Estatus'].astype(str).str.upper().str.contains('RESUELTA', na=False)
            sig_es_correctivo = df['Sig_Cat'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            en_ventana = (df['Dias_Garantia'] >= 0) & (df['Dias_Garantia'] <= 90)

            df['Es_Penalizacion'] = (es_correctivo & es_resuelta & sig_es_correctivo & en_ventana).astype(int)

            # --- FILTRADO PARA LA VISTA FINAL ---
            # Solo mostramos los folios que se "entregaron" en el mes y año seleccionado
            df_mes = df[(df['Fecha_DT'].dt.month == mes_num) & (df['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- INTERFAZ DE RESULTADOS ---
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(f"📊 Reporte de Calidad: {mes_sel} {anio_eval}")
                resumen = df_mes.groupby('Técnico').agg(
                    Folios_Atendidos=('Folio', 'count'),
                    Reincidencias=('Es_Penalizacion', 'sum')
                ).reset_index()
                
                resumen['Trabajos_Exitosos'] = resumen['Folios_Atendidos'] - resumen['Reincidencias']
                resumen['% Efectividad'] = (resumen['Trabajos_Exitosos'] / resumen['Folios_Atendidos'] * 100).round(1)
                
                st.dataframe(resumen.sort_values('Reincidencias', ascending=False), use_container_width=True, hide_index=True)

            with col2:
                st.subheader("🔎 Análisis por Técnico")
                nombre = st.text_input("Nombre del técnico:").upper()
                if nombre:
                    tec_data = df_mes[df_mes['Técnico'].str.contains(nombre, na=False)]
                    reincidencias_tec = tec_data['Es_Penalizacion'].sum()
                    st.metric("Folios que reincidieron", int(reincidencias_tec))
                    st.write(f"De {len(tec_data)} folios totales en {mes_sel}.")

            st.divider()
            st.subheader(f"📋 Evidencia: Folios de {mes_sel} que fallaron antes de 90 días")
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            if not evidencia.empty:
                st.dataframe(
                    evidencia[[col_serie, 'Folio', 'Técnico', 'Fecha_DT', 'Dias_Garantia', 'Sig_Folio']].rename(
                        columns={
                            'Fecha_DT': 'Fecha Cierre', 
                            'Dias_Garantia': 'Días que duró', 
                            'Sig_Folio': 'Folio de Reincidencia'
                        }
                    ), use_container_width=True, hide_index=True
                )
            else:
                st.success(f"No se detectaron reincidencias para los folios cerrados en {mes_sel}.")

        except Exception as e:
            st.error(f"Error técnico: {e}")
    else:
        st.info("👈 Por favor, carga el archivo Excel para iniciar la auditoría.")

if __name__ == "__main__":
    main()
