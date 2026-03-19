import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Control de Calidad", layout="wide")

def main():
    st.title("🛡️ Auditoría de Efectividad: SenAudit Pro")
    st.markdown("### Objetivo: ¿El técnico hizo bien el trabajo a la primera?")

    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio", type=["xlsx", "xlsb"])

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

            # 2. Configuración del Mes de Análisis
            st.sidebar.header("Filtro de Auditoría")
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = st.sidebar.selectbox("Mes a evaluar (Folios Resueltos)", meses_nombres, index=1)
            anio_sel = st.sidebar.number_input("Año", value=2026)
            mes_num = meses_nombres.index(mes_sel) + 1

            # --- LÓGICA DE AUDITORÍA ---
            
            # Ordenamos todo el historial para poder comparar
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # Identificamos el siguiente evento de cada máquina en todo el historial
            df['Sig_Fecha'] = df.groupby(col_serie)['Fecha_DT'].shift(-1)
            df['Sig_Folio'] = df.groupby(col_serie)['Folio'].shift(-1)
            df['Sig_Cat'] = df.groupby(col_serie)['Categoría'].shift(-1)
            
            # Calculamos días para la siguiente falla
            df['Dias_Garantia'] = (df['Sig_Fecha'] - df['Fecha_DT']).dt.days

            # DEFINICIÓN DE PENALIZACIÓN:
            # 1. El folio actual debe ser CORRECTIVO y RESUELTO.
            # 2. Debe existir un folio SIGUIENTE que sea CORRECTIVO.
            # 3. Esa reincidencia debe ocurrir en <= 90 días.
            es_correctivo = df['Categoría'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            es_resuelta = df['Estatus'].astype(str).str.upper().str.contains('RESUELTA', na=False)
            sig_es_correctivo = df['Sig_Cat'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            reincide_pronto = (df['Dias_Garantia'] >= 0) & (df['Dias_Garantia'] <= 90)

            df['Es_Penalizacion'] = (es_correctivo & es_resuelta & sig_es_correctivo & reincide_pronto).astype(int)

            # --- FILTRADO FINAL ---
            # Solo mostramos los folios que el técnico "entregó" en el mes seleccionado
            df_mes = df[(df['Fecha_DT'].dt.month == mes_num) & (df['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- INTERFAZ ---
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(f"Efectividad de Técnicos en {mes_sel}")
                resumen = df_mes.groupby('Técnico').agg(
                    Folios_Resueltos=('Folio', 'count'),
                    Reincidencias_90d=('Es_Penalizacion', 'sum')
                ).reset_index()
                
                resumen['Trabajos_Bien_Hechos'] = resumen['Folios_Resueltos'] - resumen['Reincidencias_90d']
                resumen['% Calidad'] = (resumen['Trabajos_Bien_Hechos'] / resumen['Folios_Resueltos'] * 100).round(1)
                
                st.dataframe(resumen.sort_values('Reincidencias_90d', ascending=False), use_container_width=True, hide_index=True)

            with col2:
                st.subheader("🔎 Auditoría Individual")
                nombre = st.text_input("Buscar Técnico:").upper()
                if nombre:
                    tec_data = df_mes[df_mes['Técnico'].str.contains(nombre, na=False)]
                    total_p = tec_data['Es_Penalizacion'].sum()
                    st.metric("Folios que 'rebotaron'", int(total_p))
                    st.progress(float(resumen[resumen['Técnico'].str.contains(nombre, na=False)]['% Calidad'].iloc[0] / 100))

            st.divider()
            st.subheader(f"📋 Evidencia de Fallas (Folios de {mes_sel} que no quedaron bien)")
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            if not evidencia.empty:
                st.dataframe(evidencia[[col_serie, 'Folio', 'Técnico', 'Fecha_DT', 'Dias_Garantia', 'Sig_Folio']].rename(
                    columns={'Fecha_DT': 'Fecha Cierre', 'Dias_Garantia': 'Días que duró la reparación', 'Sig_Folio': 'Folio de Reincidencia'}
                ), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("👈 Sube el reporte para auditar la calidad del servicio.")

if __name__ == "__main__":
    main()
