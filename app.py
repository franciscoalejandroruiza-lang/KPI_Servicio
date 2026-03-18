import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Penalización Total", layout="wide")

def main():
    st.title("🛡️ Auditoría de Reincidencias: Barrido de Historial")
    st.markdown("Lógica: Se penalizan **todos** los folios previos a la visita más reciente de cada equipo.")

    # 1. Carga de Archivo Excel
    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio (.xlsx)", type=["xlsx"])

    if archivo:
        try:
            df = pd.read_excel(archivo, engine='openpyxl')
            df.columns = df.columns.str.strip()
            
            # Identificación de columnas clave
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Limpieza y ordenamiento
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce')
            df = df.dropna(subset=['Fecha_DT', col_serie, 'Técnico', 'Folio'])
            
            # Ordenamos por equipo y por fecha (de más antiguo a más nuevo)
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # 2. Lógica de Penalización Masiva
            df['Es_Penalizacion'] = 0
            df['Tipo_Registro'] = "Visita Reciente"

            for serie, grupo in df.groupby(col_serie):
                if len(grupo) > 1:
                    # Obtenemos los índices de todos los folios excepto el último
                    indices_previos = grupo.index[:-1]
                    # Marcamos todos los anteriores como penalización
                    df.loc[indices_previos, 'Es_Penalizacion'] = 1
                    df.loc[indices_previos, 'Tipo_Registro'] = "Reincidencia (Penalizada)"

            # 3. Filtros de visualización (Mes de consulta)
            st.sidebar.header("Filtro de Reporte Mensual")
            meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                             7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            
            mes_eval = st.sidebar.selectbox("Mes a evaluar", list(meses_nombres.keys()), 
                                            format_func=lambda x: meses_nombres[x], index=datetime.now().month - 1)
            anio_eval = st.sidebar.number_input("Año", value=2026)

            # Filtrar para el resumen del mes
            df_mes = df[(df['Fecha_DT'].dt.month == mes_eval) & (df['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- DASHBOARD ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader(f"Conteo de Penalizaciones - {meses_nombres[mes_eval]}")
                resumen = df_mes.groupby('Técnico').agg(
                    Folios_Atendidos=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                # Ordenar por el que tiene más penalizaciones
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with c2:
                st.subheader("Gráfico de Impacto por Técnico")
                if not resumen.empty:
                    st.bar_chart(resumen.set_index('Técnico')['Penalizaciones'])

            # 4. Detalle de Auditoría
            st.divider()
            st.subheader("🔍 Detalle de Folios Penalizados (Historial)")
            
            # Mostrar solo los penalizados para revisión
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            
            if not evidencia.empty:
                st.write(f"Se encontraron {len(evidencia)} folios que no fueron la solución definitiva para el equipo.")
                st.dataframe(evidencia[[col_serie, 'Folio', 'Técnico', 'Fecha_DT', 'Categoría', 'Tipo_Registro']], use_container_width=True)
            else:
                st.success("No hay penalizaciones bajo esta regla en el mes seleccionado.")

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")
    else:
        st.info("👈 Por favor, carga el archivo Excel para procesar el barrido de folios.")

if __name__ == "__main__":
    main()
