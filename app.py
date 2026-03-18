import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro - Excel Auditor", layout="wide")

def main():
    st.title("🛡️ Auditoría de Servicios (Solo Excel)")
    st.markdown("Analiza reincidencias y penalizaciones cargando el archivo maestro de Excel.")

    # 1. Carga de Archivo configurada solo para Excel
    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio (.xlsx)", type=["xlsx"])

    if archivo:
        try:
            # Lectura de Excel
            df = pd.read_excel(archivo, engine='openpyxl')
            
            # Limpieza básica de nombres de columnas
            df.columns = df.columns.str.strip()
            
            # Identificar columnas clave (ajusta según tu archivo si cambian los nombres)
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Validación de columnas necesarias
            required_cols = [col_fecha, col_serie, 'Técnico', 'Folio', 'Categoría']
            if not all(c in df.columns for c in required_cols):
                st.error(f"El Excel no tiene las columnas necesarias: {required_cols}")
                return

            # Estandarización de tipos de datos
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce')
            df = df.dropna(subset=['Fecha_DT', col_serie, 'Técnico'])
            
            # 2. Configuración de Filtros
            st.sidebar.header("Parámetros de Auditoría")
            meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                             7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            
            mes_eval = st.sidebar.selectbox("Mes a evaluar", list(meses_nombres.keys()), 
                                            format_func=lambda x: meses_nombres[x], index=datetime.now().month - 1)
            anio_eval = st.sidebar.number_input("Año", value=2026)
            dias_garantia = st.sidebar.slider("Días de garantía (Reincidencia)", 1, 60, 30)

            # 3. Lógica de Reincidencia (Efecto Dominó)
            # Ordenamos cronológicamente
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)
            df['Es_Penalizacion'] = 0
            df['Motivo_Reincidencia'] = ""

            for serie, grupo in df.groupby(col_serie):
                if len(grupo) > 1:
                    for i in range(1, len(grupo)):
                        idx_actual = grupo.index[i]
                        idx_previo = grupo.index[i-1]
                        
                        # Diferencia de días entre este folio y el anterior
                        dif = (df.loc[idx_actual, 'Fecha_DT'] - df.loc[idx_previo, 'Fecha_DT']).days
                        
                        # Si es CORRECTIVO y falló antes del tiempo de garantía
                        # Se penaliza al técnico del folio PREVIO por no resolverlo bien
                        if "CORRECT" in str(df.loc[idx_previo, 'Categoría']).upper() and dif <= dias_garantia:
                            df.at[idx_previo, 'Es_Penalizacion'] = 1
                            folio_causa = df.loc[idx_actual, 'Folio']
                            df.at[idx_previo, 'Motivo_Reincidencia'] = f"Reabierto por Folio {folio_causa} a los {dif} días"

            # 4. Filtrado del mes seleccionado para mostrar resultados
            df_mes = df[(df['Fecha_DT'].dt.month == mes_eval) & (df['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- INTERFAZ DE RESULTADOS ---
            m1, m2 = st.columns(2)
            
            with m1:
                st.subheader(f"Resumen de Técnicos - {meses_nombres[mes_eval]}")
                resumen = df_mes.groupby('Técnico').agg(
                    Total_Servicios=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                resumen['Efectividad %'] = ((resumen['Total_Servicios'] - resumen['Penalizaciones']) / resumen['Total_Servicios'] * 100).round(1)
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with m2:
                st.subheader("Gráfico de Reincidencias")
                st.bar_chart(resumen.set_index('Técnico')['Penalizaciones'])

            # Detalle para auditoría manual
            st.divider()
            st.subheader("🔍 Listado de Folios Penalizados (Evidencia)")
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            
            if not evidencia.empty:
                cols_mostrar = ['Folio', 'Técnico', col_serie, 'Fecha_DT', 'Categoría', 'Motivo_Reincidencia']
                st.dataframe(evidencia[cols_mostrar], use_container_width=True)
            else:
                st.success("🎉 No hay penalizaciones registradas en este mes.")

        except Exception as e:
            st.error(f"Error al procesar el Excel: {e}")
            st.info("Asegúrate de que el archivo no esté protegido con contraseña y tenga las columnas estándar.")

    else:
        st.info("☝️ Por favor, carga el archivo Excel (.xlsx) en el panel izquierdo.")

if __name__ == "__main__":
    main()
