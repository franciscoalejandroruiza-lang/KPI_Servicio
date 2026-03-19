import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="SenAudit Pro - Auditoría de Garantía", layout="wide")

def main():
    st.title("🛡️ SenAudit Pro: Control de Calidad y Garantía")
    st.markdown("### Análisis de Reincidencias: El Escáner de Febrero")
    st.info("Esta interfaz audita los folios de febrero para encontrar quién trabajó la máquina antes y no dio la garantía de 3 meses.")

    # --- BARRA LATERAL: CARGA Y FILTROS ---
    st.sidebar.header("📂 Carga de Datos")
    archivo = st.sidebar.file_uploader("Subir Reporte (XLSB o XLSX)", type=["xlsx", "xlsb"])

    if archivo:
        try:
            # Lectura del archivo
            engine = 'openpyxl' if archivo.name.endswith('xlsx') else 'pyxlsb'
            df = pd.read_excel(archivo, engine=engine)
            df.columns = df.columns.str.strip()
            
            # Identificación de columnas
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Limpieza básica
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            df = df.dropna(subset=['Fecha_DT', col_serie])

            # Configuración del Mes de Auditoría
            st.sidebar.header("⚙️ Configuración del Escáner")
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = st.sidebar.selectbox("Mes a Escanear (Fallas actuales)", meses_nombres, index=1)
            anio_sel = st.sidebar.number_input("Año", value=2026)
            mes_num = meses_nombres.index(mes_sel) + 1

            # --- LÓGICA MATEMÁTICA DE PENALIZACIÓN ---
            # Ordenamos todo el historial para que el sistema pueda "viajar al pasado"
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # Miramos quién estuvo ANTES en esa misma máquina
            df['Tecnico_Anterior'] = df.groupby(col_serie)['Técnico'].shift(1)
            df['Fecha_Anterior'] = df.groupby(col_serie)['Fecha_DT'].shift(1)
            df['Folio_Anterior'] = df.groupby(col_serie)['Folio'].shift(1)
            df['Estatus_Anterior'] = df.groupby(col_serie)['Estatus'].shift(1)
            df['Cat_Anterior'] = df.groupby(col_serie)['Categoría'].shift(1)

            # Calculamos cuántos días pasaron entre que el anterior la dejó y hoy falló
            df['Dias_Duracion'] = (df['Fecha_DT'] - df['Fecha_Anterior']).dt.days

            # REGLA DE ORO: Penalizar si hoy es CORRECTIVO y el anterior fue <= 90 días
            es_falla_hoy = df['Categoría'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            fue_resuelta_antes = df['Estatus_Anterior'].astype(str).str.upper().str.contains('RESUELTA', na=False)
            dentro_garantia = (df['Dias_Duracion'] >= 0) & (df['Dias_Duracion'] <= 90)

            df['Penalizar_Al_Anterior'] = (es_falla_hoy & fue_resuelta_antes & dentro_garantia).astype(int)

            # --- VISTA DE RESULTADOS (FILTRADO POR EL MES ELEGIDO) ---
            df_deteccion = df[(df['Fecha_DT'].dt.month == mes_num) & (df['Fecha_DT'].dt.year == anio_sel)].copy()

            # --- INTERFAZ VISUAL ---
            tab1, tab2 = st.tabs(["📊 Ranking de Responsables", "🔍 Detalle de Evidencia"])

            with tab1:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(f"Técnicos Penalizados en {mes_sel}")
                    # Agrupamos por el técnico que hizo el trabajo original (el anterior)
                    resumen = df_deteccion.groupby('Tecnico_Anterior').agg(
                        Penalizaciones_Acumuladas=('Penalizar_Al_Anterior', 'sum')
                    ).reset_index().rename(columns={'Tecnico_Anterior': 'Técnico Responsable'})
                    
                    st.dataframe(resumen.sort_values('Penalizaciones_Acumuladas', ascending=False), 
                                 use_container_width=True, hide_index=True)

                with col2:
                    st.subheader("Buscador Directo")
                    nombre = st.text_input("Escribe nombre (ej. ALEJANDRO):").upper()
                    if nombre:
                        puntos = resumen[resumen['Técnico Responsable'].str.contains(nombre, na=False)]['Penalizaciones_Acumuladas'].sum()
                        st.metric("Total Penalizaciones", int(puntos))

            with tab2:
                st.subheader(f"Listado de Fallas Detectadas en {mes_sel}")
                evidencia = df_deteccion[df_deteccion['Penalizar_Al_Anterior'] == 1]
                if not evidencia.empty:
                    st.dataframe(
                        evidencia[[col_serie, 'Folio', 'Fecha_DT', 'Tecnico_Anterior', 'Folio_Anterior', 'Dias_Duracion']].rename(
                            columns={
                                'Folio': 'Folio Falla Hoy',
                                'Fecha_DT': 'Fecha Hoy',
                                'Tecnico_Anterior': 'Técnico a Penalizar',
                                'Folio_Anterior': 'Folio Mal Hecho',
                                'Dias_Duracion': 'Días que duró la reparación'
                            }
                        ), use_container_width=True, hide_index=True
                    )
                else:
                    st.success("No se encontraron fallas en este mes que penalicen trabajos anteriores.")

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")
    else:
        st.warning("👈 Por favor, carga el archivo Excel para ver el tablero.")

if __name__ == "__main__":
    main()
