import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Reporte Mensual", layout="wide")

def main():
    st.title("🛡️ Auditoría SenAudit Pro")
    st.markdown("Análisis de **Correctivos Resueltos** con historial de reincidencia.")

    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio (.xlsx)", type=["xlsx"])

    if archivo:
        try:
            # Carga de datos
            df = pd.read_excel(archivo, engine='openpyxl')
            df.columns = df.columns.str.strip()
            
            # Identificación de columnas
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Limpieza de fechas (tz-naive para evitar conflictos)
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            
            # Filtro: Solo Correctivos y Resueltas
            df_valido = df[
                (df['Categoría'].str.contains('CORRECTIVO', case=False, na=False)) & 
                (df['Estatus'].str.contains('RESUELTA', case=False, na=False))
            ].copy()

            if df_valido.empty:
                st.warning("No hay registros que coincidan con 'CORRECTIVO' y 'RESUELTA'.")
                return

            # --- CONFIGURACIÓN EN BARRA LATERAL ---
            st.sidebar.header("Configuración")
            dias_garantia = st.sidebar.slider("Días de garantía para reincidencia", 1, 365, 30)
            
            # Listado de meses por nombre
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            
            mes_nombre_sel = st.sidebar.selectbox("Selecciona el Mes a consultar", meses_nombres, 
                                                  index=datetime.now().month - 1)
            mes_num_sel = meses_nombres.index(mes_nombre_sel) + 1
            anio_eval = st.sidebar.number_input("Año", value=2026)

            # --- LÓGICA DE PENALIZACIÓN ---
            # Ordenamos por serie y fecha
            df_valido = df_valido.sort_values([col_serie, 'Fecha_DT'], ascending=True)
            df_valido['Es_Penalizacion'] = 0
            df_valido['Dias_Diff'] = 0

            for serie, grupo in df_valido.groupby(col_serie):
                if len(grupo) > 1:
                    for i in range(len(grupo) - 1):
                        idx_actual = grupo.index[i]
                        idx_siguiente = grupo.index[i+1]
                        
                        dif = (df_valido.loc[idx_siguiente, 'Fecha_DT'] - df_valido.loc[idx_actual, 'Fecha_DT']).days
                        
                        if 0 <= dif <= dias_garantia:
                            df_valido.at[idx_actual, 'Es_Penalizacion'] = 1
                            df_valido.at[idx_actual, 'Dias_Diff'] = dif

            # --- FILTRADO PARA EL REPORTE ---
            df_mes = df_valido[(df_valido['Fecha_DT'].dt.month == mes_num_sel) & 
                               (df_valido['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- INTERFAZ DE RESULTADOS ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader(f"Resumen de Técnicos: {mes_nombre_sel}")
                resumen = df_mes.groupby('Técnico').agg(
                    Correctivos_Totales=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                resumen['Efectividad %'] = ((resumen['Correctivos_Totales'] - resumen['Penalizaciones']) / resumen['Correctivos_Totales'] * 100).round(1)
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with c2:
                st.subheader("Gráfico de Penalizaciones")
                if not resumen.empty:
                    st.bar_chart(resumen.set_index('Técnico')['Penalizaciones'])

            st.divider()
            st.subheader(f"🔍 Detalle de Reincidencias en {mes_nombre_sel}")
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            
            if not evidencia.empty:
                cols_finales = ['Folio', 'Técnico', col_serie, 'Fecha_DT', 'Dias_Diff']
                st.dataframe(evidencia[cols_finales].rename(columns={'Dias_Diff': 'Días p/ reincidir'}), use_container_width=True)
            else:
                st.success(f"Excelente: No se detectaron reincidencias en el mes de {mes_nombre_sel}.")

        except Exception as e:
            st.error(f"Error al procesar el Excel: {e}")
    else:
        st.info("👈 Por favor, carga el reporte en Excel para generar la auditoría mensual.")

if __name__ == "__main__":
    main()
