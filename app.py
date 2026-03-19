import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Auditoría Real", layout="wide")

def main():
    st.title("🛡️ Auditoría SenAudit Pro")
    st.markdown("Cálculo de penalizaciones por reincidencia (Garantía Móvil).")

    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio (.xlsx)", type=["xlsx"])

    if archivo:
        try:
            # 1. Carga y limpieza de datos
            df = pd.read_excel(archivo, engine='openpyxl')
            df.columns = df.columns.str.strip()
            
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Normalización de fechas y textos
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            
            # 2. Configuración de Filtros (Lo que pediste)
            st.sidebar.header("Parámetros de Auditoría")
            dias_garantia = st.sidebar.slider("Días de garantía (Reincidencia)", 1, 365, 90)
            
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = st.sidebar.selectbox("Mes a calcular", meses_nombres, index=datetime.now().month - 1)
            mes_num = meses_nombres.index(mes_sel) + 1
            anio_eval = st.sidebar.number_input("Año", value=2026)

            # 3. Lógica de Penalización (Barrido por Historial Completo)
            # Ordenamos para comparar visitas cronológicamente
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)
            df['Es_Penalizacion'] = 0
            df['Dias_Reincidencia'] = 0
            df['Folio_Que_Lo_Penaliza'] = ""

            for serie, grupo in df.groupby(col_serie):
                if len(grupo) > 1:
                    # Analizamos cada folio excepto el último de la cadena
                    for i in range(len(grupo) - 1):
                        idx_actual = grupo.index[i]
                        idx_siguiente = grupo.index[i+1]
                        
                        # FILTROS CRÍTICOS:
                        # Solo penalizamos si el folio actual es CORRECTIVO y RESUELTO
                        es_correctivo = "CORRECTIVO" in str(df.loc[idx_actual, 'Categoría']).upper()
                        es_resuelta = "RESUELTA" in str(df.loc[idx_actual, 'Estatus']).upper()
                        
                        # Calculamos diferencia de días
                        dif = (df.loc[idx_siguiente, 'Fecha_DT'] - df.loc[idx_actual, 'Fecha_DT']).days
                        
                        if es_correctivo and es_resuelta and (0 <= dif <= dias_garantia):
                            df.at[idx_actual, 'Es_Penalizacion'] = 1
                            df.at[idx_actual, 'Dias_Reincidencia'] = dif
                            df.at[idx_actual, 'Folio_Que_Lo_Penaliza'] = df.loc[idx_sig, 'Folio']
                        
                        # El último folio de 'grupo' (i = len-1) nunca entra al 'if' de arriba,
                        # por lo tanto se queda con Es_Penalizacion = 0 automáticamente.

            # 4. Filtrado Final por el Mes seleccionado por el usuario
            df_mes = df[(df['Fecha_DT'].dt.month == mes_num) & (df['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- VISUALIZACIÓN ---
            c1, c2 = st.columns([1, 1])
            with c1:
                st.subheader(f"Resumen de Eficiencia: {mes_sel}")
                resumen = df_mes.groupby('Técnico').agg(
                    Total_Correctivos=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                resumen['% Efectividad'] = ((resumen['Total_Correctivos'] - resumen['Penalizaciones']) / resumen['Total_Correctivos'] * 100).round(1)
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with c2:
                st.subheader("Auditor de Folios")
                tec_auditar = st.text_input("Buscar técnico (ej. ALEJANDRO RUIZ):").upper()
                if tec_auditar:
                    total_p = df_mes[df_mes['Técnico'].str.contains(tec_auditar, na=False)]['Es_Penalizacion'].sum()
                    st.metric(f"Penalizaciones de {tec_auditar} en {mes_sel}", total_p)

            st.divider()
            st.subheader(f"📋 Evidencia Detallada de {mes_sel}")
            st.write(f"Mostrando folios marcados como reincidentes dentro de los {dias_garantia} días.")
            
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            if not evidencia.empty:
                cols_ver = ['Folio', 'Técnico', col_serie, 'Fecha_DT', 'Dias_Reincidencia', 'Categoría']
                st.dataframe(evidencia[cols_ver], use_container_width=True)
            else:
                st.success("No se encontraron penalizaciones en este mes con el rango de garantía actual.")

        except Exception as e:
            st.error(f"Hubo un problema al procesar los datos: {e}")
    else:
        st.info("👈 Por favor, carga el archivo Excel para iniciar el cálculo.")

if __name__ == "__main__":
    main()
