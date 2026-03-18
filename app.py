import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Auditor Oficial", layout="wide")

def main():
    st.title("🛡️ Auditoría SenAudit Pro")
    st.markdown("Filtros: **Correctivos Resueltos** | Rango: **1-365 días** | **Barrido de Historial**")

    # 1. Carga de Archivo Excel
    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio (.xlsx)", type=["xlsx"])

    if archivo:
        try:
            df = pd.read_excel(archivo, engine='openpyxl')
            df.columns = df.columns.str.strip()
            
            # Identificación de columnas clave
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # --- CONFIGURACIÓN DE AUDITORÍA ---
            st.sidebar.header("Configuración")
            
            # Selector de días de garantía (como lo tenías, de 1 a 365)
            dias_garantia = st.sidebar.slider("Días de garantía para reincidencia", 1, 365, 30)
            
            # Fecha de corte para la validez de los folios
            fecha_corte = st.sidebar.date_input("Fecha de corte de auditoría", datetime.now())
            fecha_corte_dt = pd.to_datetime(fecha_corte)

            # Limpieza y conversión de fechas
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce')
            
            # FILTRO CRÍTICO: Solo Correctivos y Resueltas
            df_valido = df[
                (df['Categoría'].str.contains('CORRECTIVO', case=False, na=False)) & 
                (df['Estatus'].str.contains('RESUELTA', case=False, na=False))
            ].copy()

            if df_valido.empty:
                st.warning("No se encontraron registros que sean 'CORRECTIVO' y 'RESUELTA'.")
                return

            # Ordenamos cronológicamente
            df_valido = df_valido.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # 2. Lógica de Penalización (Barrido con límite de días)
            df_valido['Es_Penalizacion'] = 0
            df_valido['Dias_Diff'] = 0

            # Solo analizamos lo que ocurrió hasta la fecha de corte
            df_auditable = df_valido[df_valido['Fecha_DT'] <= fecha_corte_dt].copy()

            for serie, grupo in df_auditable.groupby(col_serie):
                if len(grupo) > 1:
                    # Comparamos cada folio con el siguiente para ver si entra en el rango de días
                    for i in range(len(grupo) - 1):
                        idx_actual = grupo.index[i]
                        idx_siguiente = grupo.index[i+1]
                        
                        dif = (df_auditable.loc[idx_siguiente, 'Fecha_DT'] - df_auditable.loc[idx_actual, 'Fecha_DT']).days
                        
                        # Si la siguiente visita ocurrió dentro del rango de días marcado (1-365)
                        if dif <= dias_garantia:
                            df_auditable.at[idx_actual, 'Es_Penalizacion'] = 1
                            df_auditable.at[idx_actual, 'Dias_Diff'] = dif

            # 3. Reporte del Mes Seleccionado
            st.sidebar.divider()
            meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                             7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            
            mes_eval = st.sidebar.selectbox("Mes a visualizar", list(meses_nombres.keys()), 
                                            format_func=lambda x: meses_nombres[x], index=datetime.now().month - 1)
            anio_eval = st.sidebar.number_input("Año", value=2026)

            df_mes = df_auditable[(df_auditable['Fecha_DT'].dt.month == mes_eval) & 
                                  (df_auditable['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- INTERFAZ ---
            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"Resumen Técnicos - {meses_nombres[mes_eval]}")
                resumen = df_mes.groupby('Técnico').agg(
                    Total_Correctivos=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with col2:
                st.subheader("Gráfico de Penalizaciones")
                st.bar_chart(resumen.set_index('Técnico')['Penalizaciones'])

            st.divider()
            st.subheader(f"🔍 Detalle de Reincidencias (Corte: {fecha_corte} | Rango: {dias_garantia} días)")
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            
            if not evidencia.empty:
                # Columnas finales para revisión
                cols = ['Folio', 'Técnico', col_serie, 'Fecha_DT', 'Dias_Diff', 'Categoría']
                st.dataframe(evidencia[cols].rename(columns={'Dias_Diff': 'Días p/ reincidir'}), use_container_width=True)
            else:
                st.success("Sin penalizaciones detectadas con los filtros actuales.")

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
    else:
        st.info("👈 Sube tu archivo Excel para iniciar la auditoría.")

if __name__ == "__main__":
    main()
