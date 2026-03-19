import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SenAudit Pro - Filtro Dinámico", layout="wide")

def main():
    st.title("🛡️ SenAudit Pro: Control de Productividad y Garantía")
    
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
            st.sidebar.header("⚙️ Configuración del Mes")
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            
            # El usuario elige el mes que quiere auditar/ver
            mes_sel = st.sidebar.selectbox("Selecciona el Mes:", meses_nombres, index=1)
            anio_sel = st.sidebar.number_input("Año:", value=2026)
            mes_num = meses_nombres.index(mes_sel) + 1

            # --- LÓGICA DE AUDITORÍA ---
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)
            df['Tecnico_Ant'] = df.groupby(col_serie)['Técnico'].shift(1)
            df['Fecha_Ant'] = df.groupby(col_serie)['Fecha_DT'].shift(1)
            df['Estatus_Ant'] = df.groupby(col_serie)['Estatus'].shift(1)
            df['Dias_Garantia'] = (df['Fecha_DT'] - df['Fecha_Ant']).dt.days

            # Penalización: Correctivo hoy + Resuelta antes + <= 90 días
            es_falla_hoy = df['Categoría'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            fue_resuelta_ant = df['Estatus_Ant'].astype(str).str.upper().str.contains('RESUELTA', na=False)
            df['Es_Penalizacion'] = (es_falla_hoy & fue_resuelta_ant & (df['Dias_Garantia'] <= 90)).astype(int)

            # --- PESTAÑAS ---
            tab_general, tab_auditoria = st.tabs(["📊 Resumen Mensual", "🔍 Auditoría de Reincidencias"])

            with tab_general:
                # FILTRO CLAVE: Solo el mes y año configurados por ti
                df_mes_vista = df[(df['Fecha_DT'].dt.month == mes_num) & 
                                  (df['Fecha_DT'].dt.year == anio_sel) & 
                                  (df['Estatus'].str.contains('RESUELTA', case=False, na=False))].copy()
                
                st.subheader(f"Productividad en {mes_sel} {anio_sel}")
                
                # Resumen de Resueltos por Técnico
                resumen_vista = df_mes_vista.groupby('Técnico').agg(
                    Folios_Resueltos=('Folio', 'count'),
                    Equipos_Distintos=(col_serie, 'nunique')
                ).reset_index()

                # Mostrar tabla con estilo similar al que enviaste (azul)
                st.dataframe(
                    resumen_vista.sort_values('Folios_Resueltos', ascending=False).style.background_gradient(cmap='Blues', subset=['Folios_Resueltos']),
                    use_container_width=True, 
                    hide_index=True
                )
                
                st.info(f"Mostrando únicamente los folios resueltos durante el mes de **{mes_sel}**.")

            with tab_auditoria:
                st.subheader(f"Auditoría de Garantía: {mes_sel}")
                # Solo folios que reincidieron (fallaron) en el mes seleccionado
                df_penal = df[(df['Fecha_DT'].dt.month == mes_num) & (df['Fecha_DT'].dt.year == anio_sel)].copy()
                
                ranking = df_penal.groupby('Tecnico_Ant').agg(
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index().rename(columns={'Tecnico_Ant': 'Técnico Responsable'})
                
                st.dataframe(ranking.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("👈 Configura el mes y carga el reporte para comenzar.")

if __name__ == "__main__":
    main()
