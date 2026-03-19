import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SenAudit Pro - Configuración de Auditoría", layout="wide")

def main():
    st.title("🛡️ SenAudit Pro: Auditoría Personalizada")
    
    # --- BARRA LATERAL ---
    st.sidebar.header("📂 Carga de Datos")
    archivo = st.sidebar.file_uploader("Subir Reporte (XLSB o XLSX)", type=["xlsx", "xlsb"])

    if archivo:
        try:
            # 1. Carga y Normalización
            engine = 'openpyxl' if archivo.name.endswith('xlsx') else 'pyxlsb'
            df = pd.read_excel(archivo, engine=engine)
            df.columns = df.columns.str.strip()
            
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            df = df.dropna(subset=['Fecha_DT', col_serie])

            # --- SELECTOR DE MES CONFIGURABLE ---
            st.sidebar.header("⚙️ Configuración de Vista")
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            
            # El usuario elige qué mes quiere auditar
            mes_sel = st.sidebar.selectbox("Selecciona el Mes a Auditar:", meses_nombres, index=1)
            anio_sel = st.sidebar.number_input("Año:", value=2026)
            mes_num = meses_nombres.index(mes_sel) + 1

            # --- LÓGICA DE GARANTÍA (3 MESES) ---
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # Identificar quién estuvo antes en la máquina (Garantía)
            df['Tecnico_Ant'] = df.groupby(col_serie)['Técnico'].shift(1)
            df['Fecha_Ant'] = df.groupby(col_serie)['Fecha_DT'].shift(1)
            df['Folio_Ant'] = df.groupby(col_serie)['Folio'].shift(1)
            df['Estatus_Ant'] = df.groupby(col_serie)['Estatus'].shift(1)
            df['Dias_Garantia'] = (df['Fecha_DT'] - df['Fecha_Ant']).dt.days

            # Regla: Penaliza al anterior si hoy es Correctivo y pasaron <= 90 días
            es_falla_hoy = df['Categoría'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            fue_resuelta_ant = df['Estatus_Ant'].astype(str).str.upper().str.contains('RESUELTA', na=False)
            penalizacion = (es_falla_hoy & fue_resuelta_ant & (df['Dias_Garantia'] <= 90)).astype(int)
            df['Es_Penalizacion'] = penalizacion

            # --- PESTAÑAS ---
            tab_general, tab_auditoria = st.tabs(["📊 Resumen Mensual", "🔍 Auditoría de Reincidencias"])

            with tab_general:
                # Filtrar solo resueltos del año para la matriz
                df_res = df[(df['Estatus'].str.contains('RESUELTA', case=False)) & (df['Fecha_DT'].dt.year == anio_sel)]
                matriz = df_res.pivot_table(index='Técnico', columns=df_res['Fecha_DT'].dt.month, values='Folio', aggfunc='count', fill_value=0)
                matriz = matriz.rename(columns={i+1: meses_nombres[i][:3] for i in range(12)})
                st.subheader(f"Productividad Histórica {anio_sel}")
                st.dataframe(matriz.style.background_gradient(cmap='Blues', axis=None), use_container_width=True)

            with tab_auditoria:
                st.subheader(f"Análisis de Fallas en {mes_sel} {anio_sel}")
                
                # Solo folios que fallaron en el mes seleccionado por el usuario
                df_mes_audit = df[(df['Fecha_DT'].dt.month == mes_num) & (df['Fecha_DT'].dt.year == anio_sel)].copy()
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown("#### Técnicos con Garantías Incumplidas")
                    # Agrupamos por el que hizo el trabajo mal (el anterior)
                    ranking = df_mes_audit.groupby('Tecnico_Ant').agg(
                        Casos_Reincidentes=('Es_Penalizacion', 'sum')
                    ).reset_index().rename(columns={'Tecnico_Ant': 'Técnico Responsable'})
                    
                    st.dataframe(ranking.sort_values('Casos_Reincidentes', ascending=False), use_container_width=True, hide_index=True)

                with col2:
                    st.markdown("#### Buscador de Evidencia")
                    nombre = st.text_input("Nombre del Técnico:").upper()
                    if nombre:
                        evid = df_mes_audit[(df_mes_audit['Tecnico_Ant'].str.contains(nombre, na=False)) & (df_mes_audit['Es_Penalizacion'] == 1)]
                        st.metric("Penalizaciones Detectadas", len(evid))

                st.divider()
                st.markdown(f"#### Detalle de Folios que 'rebotaron' en {mes_sel}")
                evidencia_total = df_mes_audit[df_mes_audit['Es_Penalizacion'] == 1]
                st.dataframe(
                    evidencia_total[[col_serie, 'Folio', 'Fecha_DT', 'Tecnico_Ant', 'Folio_Ant', 'Dias_Garantia']].rename(
                        columns={'Folio': 'Folio Falla Hoy', 'Tecnico_Ant': 'Responsable', 'Folio_Ant': 'Folio Original', 'Dias_Garantia': 'Días Duró'}
                    ), use_container_width=True, hide_index=True
                )

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("👈 Selecciona el archivo y configura el mes en la barra lateral.")

if __name__ == "__main__":
    main()
