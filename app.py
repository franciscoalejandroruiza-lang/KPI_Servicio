import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Versión Estable", layout="wide")

def main():
    st.title("🛡️ Auditoría SenAudit Pro (Estable)")
    
    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio (.xlsx)", type=["xlsx"])

    if archivo:
        try:
            df = pd.read_excel(archivo, engine='openpyxl')
            df.columns = df.columns.str.strip()
            
            # Identificación de columnas
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # --- LIMPIEZA DE FECHAS (Elimina el conflicto de zona horaria) ---
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            
            # Filtro de seguridad: Solo Correctivos Resueltos
            df_valido = df[
                (df['Categoría'].str.contains('CORRECTIVO', case=False, na=False)) & 
                (df['Estatus'].str.contains('RESUELTA', case=False, na=False))
            ].copy()

            if df_valido.empty:
                st.warning("No se encontraron registros 'CORRECTIVO' y 'RESUELTA'.")
                return

            # Configuración de Auditoría
            dias_garantia = st.sidebar.slider("Días de garantía", 1, 365, 30)
            fecha_corte = st.sidebar.date_input("Fecha de corte", datetime.now())
            # Convertimos fecha de corte a datetime sin zona horaria
            fecha_corte_dt = pd.to_datetime(fecha_corte).replace(tzinfo=None)

            # Orden cronológico
            df_valido = df_valido.sort_values([col_serie, 'Fecha_DT'], ascending=True)
            df_valido['Es_Penalizacion'] = 0

            # Solo auditamos lo que esté antes de la fecha de corte
            df_auditable = df_valido[df_valido['Fecha_DT'] <= fecha_corte_dt].copy()

            # --- LÓGICA DE PENALIZACIÓN ---
            for serie, grupo in df_auditable.groupby(col_serie):
                if len(grupo) > 1:
                    for i in range(len(grupo) - 1):
                        idx_actual = grupo.index[i]
                        idx_siguiente = grupo.index[i+1]
                        
                        # Calculamos diferencia de días
                        dif = (df_auditable.loc[idx_siguiente, 'Fecha_DT'] - df_auditable.loc[idx_actual, 'Fecha_DT']).days
                        
                        if 0 <= dif <= dias_garantia:
                            df_auditable.at[idx_actual, 'Es_Penalizacion'] = 1

            # --- VISUALIZACIÓN ---
            mes_eval = st.sidebar.selectbox("Mes", range(1, 13), index=datetime.now().month - 1)
            anio_eval = st.sidebar.number_input("Año", value=2026)

            df_mes = df_auditable[(df_auditable['Fecha_DT'].dt.month == mes_eval) & 
                                  (df_auditable['Fecha_DT'].dt.year == anio_eval)]

            c1, c2 = st.columns(2)
            with c1:
                resumen = df_mes.groupby('Técnico').agg(
                    Total=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                st.write(f"### Resumen Mes {mes_eval}")
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with c2:
                if not resumen.empty:
                    st.bar_chart(resumen.set_index('Técnico')['Penalizaciones'])

            st.divider()
            st.subheader("Evidencia de Penalizaciones")
            st.dataframe(df_mes[df_mes['Es_Penalizacion'] == 1][[col_serie, 'Folio', 'Técnico', 'Fecha_DT']], use_container_width=True)

        except Exception as e:
            st.error(f"Error detectado: {e}")
    else:
        st.info("Carga el archivo Excel para comenzar.")

if __name__ == "__main__":
    main()
