import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Auditoría Pro", layout="wide")

def main():
    st.title("🛡️ Auditoría de Reincidencias: Control de Corte")
    st.markdown("Lógica: Se penalizan folios previos a la fecha de corte, filtrando solo por **Correctivos Resueltos**.")

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
            st.sidebar.header("Parámetros de Corte")
            
            # Punto 1: Fecha que considera para las penalizaciones
            fecha_corte = st.sidebar.date_input("Fecha de corte para auditoría", datetime.now())
            fecha_corte_dt = pd.to_datetime(fecha_corte)

            # Limpieza y conversión
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce')
            
            # Punto 2: Solo aplican en RESUELTA y CORRECTIVOS
            # Filtramos el dataframe original para que la lógica de reincidencia solo vea estos casos
            df_filtrado = df[
                (df['Categoría'].str.contains('CORRECTIVO', case=False, na=False)) & 
                (df['Estatus'].str.contains('RESUELTA', case=False, na=False))
            ].copy()

            if df_filtrado.empty:
                st.warning("No se encontraron folios que coincidan con 'CORRECTIVO' y 'RESUELTA'.")
                return

            # Ordenamos por equipo y por fecha
            df_filtrado = df_filtrado.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # 2. Lógica de Penalización (Barrido hasta fecha de corte)
            df_filtrado['Es_Penalizacion'] = 0
            
            # Solo analizamos folios hasta la fecha de corte seleccionada
            df_auditable = df_filtrado[df_filtrado['Fecha_DT'] <= fecha_corte_dt].copy()

            for serie, grupo in df_auditable.groupby(col_serie):
                if len(grupo) > 1:
                    # El folio más reciente de este equipo (antes de la fecha de corte) es el "válido"
                    # Todos los anteriores de ese mismo equipo se penalizan
                    indices_previos = grupo.index[:-1]
                    df_auditable.loc[indices_previos, 'Es_Penalizacion'] = 1

            # 3. Filtro para el Reporte Mensual (Visualización)
            st.sidebar.header("Mes a Reportar")
            meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                             7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            
            mes_eval = st.sidebar.selectbox("Mes", list(meses_nombres.keys()), 
                                            format_func=lambda x: meses_nombres[x], index=datetime.now().month - 1)
            anio_eval = st.sidebar.number_input("Año", value=2026)

            # Filtramos la tabla final para mostrar solo los folios del mes de interés
            df_mes = df_auditable[(df_auditable['Fecha_DT'].dt.month == mes_eval) & 
                                  (df_auditable['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- DASHBOARD ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader(f"Penalizaciones - {meses_nombres[mes_eval]}")
                resumen = df_mes.groupby('Técnico').agg(
                    Correctivos_Resueltos=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with c2:
                st.subheader("Análisis de Fallas por Técnico")
                if not resumen.empty:
                    st.bar_chart(resumen.set_index('Técnico')['Penalizaciones'])

            # 4. Detalle de Evidencia
            st.divider()
            st.subheader(f"🔍 Evidencia de Folios Penalizados (Corte al {fecha_corte})")
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            
            if not evidencia.empty:
                st.dataframe(evidencia[[col_serie, 'Folio', 'Técnico', 'Fecha_DT', 'Categoría', 'Estatus']], use_container_width=True)
            else:
                st.success("No se encontraron penalizaciones con los filtros actuales.")

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")
    else:
        st.info("👈 Carga el archivo Excel para procesar las penalizaciones de correctivos resueltos.")

if __name__ == "__main__":
    main()
