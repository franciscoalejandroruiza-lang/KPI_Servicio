import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro - Automatizado", layout="wide")
import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro - Auditor de Reincidencias", layout="wide")

def main():
    st.title("🛡️ Auditoría de Servicios y Penalizaciones")
    st.markdown("Análisis de reincidencias basado en el historial de folios por equipo.")

    # 1. Carga de Archivo
    archivo = st.sidebar.file_uploader("Subir Reporte (CSV)", type=["csv"])

    if archivo:
        # Lectura de datos (asumiendo el formato del archivo subido)
        df = pd.read_csv(archivo)
        
        # Limpieza de columnas y estandarización
        df.columns = df.columns.str.strip()
        
        # Usamos 'Fecha recepción' o 'Última visita' según disponibilidad
        col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
        df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce')
        
        # Identificar columna de serie
        col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
        
        # Limpiar filas críticas
        df = df.dropna(subset=['Fecha_DT', 'Folio', col_serie, 'Técnico'])

        # 2. Configuración de la Auditoría
        st.sidebar.header("Configuración de Mes")
        meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                         7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        mes_eval = st.sidebar.selectbox("Mes a evaluar", list(meses_nombres.keys()), 
                                        format_func=lambda x: meses_nombres[x], index=2) # Default Marzo
        anio_eval = st.sidebar.number_input("Año", value=2026)
        
        # 3. Lógica de Penalización por Reincidencia
        # Ordenamos por serie y fecha para rastrear la historia de cada máquina
        df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)

        # Creamos columnas para el análisis
        df['Es_Penalizacion'] = 0
        df['Dias_Desde_Anterior'] = None
        df['Folio_Anterior'] = None

        # Procesamos cada equipo individualmente
        for serie, grupo in df.groupby(col_serie):
            if len(grupo) > 1:
                # Comparamos cada folio con el anterior
                for i in range(1, len(grupo)):
                    idx_actual = grupo.index[i]
                    idx_previo = grupo.index[i-1]
                    
                    # Calculamos diferencia de días
                    dif = (df.loc[idx_actual, 'Fecha_DT'] - df.loc[idx_previo, 'Fecha_DT']).days
                    
                    # REGLA: Si la visita anterior fue CORRECTIVO y pasaron menos de 30 días
                    # el técnico de la visita ANTERIOR es penalizado porque el equipo falló de nuevo.
                    cat_previa = str(df.loc[idx_previo, 'Categoría']).upper()
                    if "CORRECT" in cat_previa and dif <= 30:
                        df.at[idx_previo, 'Es_Penalizacion'] = 1
                        df.at[idx_previo, 'Dias_Desde_Anterior'] = dif # Guardamos dato para evidencia
                        df.at[idx_previo, 'Folio_Anterior'] = df.loc[idx_actual, 'Folio']

        # 4. Filtrar resultados para el mes seleccionado
        df_mes = df[(df['Fecha_DT'].dt.month == mes_eval) & (df['Fecha_DT'].dt.year == anio_eval)].copy()

        # --- PANEL DE RESULTADOS ---
        col_m1, col_m2 = st.columns([1, 1])
        
        with col_m1:
            st.subheader(f"Resumen: {meses_nombres[mes_eval]} {anio_eval}")
            resumen = df_mes.groupby('Técnico').agg(
                Servicios_Totales=('Folio', 'count'),
                Penalizaciones=('Es_Penalizacion', 'sum')
            ).reset_index()
            resumen['Efectividad'] = ((resumen['Servicios_Totales'] - resumen['Penalizaciones']) / resumen['Servicios_Totales'] * 100).round(1)
            st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

        with col_m2:
            st.subheader("Fallas por Técnico")
            if not resumen.empty:
                st.bar_chart(resumen.set_index('Técnico')['Penalizaciones'])

        # 5. Detalle de Evidencia (Para cuando un técnico pregunte ¿por qué me penalizaron?)
        st.divider()
        st.subheader("🔍 Detalle de Folios Penalizados")
        
        evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
        
        if not evidencia.empty:
            # Seleccionamos columnas útiles para la revisión
            columnas_ver = ['Folio', 'Técnico', col_serie, 'Fecha_DT', 'Categoría', 'Problema reportado', 'Folio_Anterior']
            st.dataframe(evidencia[columnas_ver], use_container_width=True)
            
            st.info("💡 **Nota:** Un folio aparece penalizado si el mismo equipo volvió a entrar a servicio en menos de 30 días después de esa visita.")
        else:
            st.success("No se encontraron penalizaciones en este periodo.")

    else:
        st.info("👈 Por favor, carga el archivo del reporte en la barra lateral.")

if __name__ == "__main__":
    main()
def main():
    st.title("🛡️ Auditoría Automatizada de Servicios")
    st.markdown("Carga tu archivo Excel para calcular las penalizaciones bajo la lógica de **Efecto Dominó**.")

    # 1. Carga de Archivo
    archivo = st.sidebar.file_uploader("Subir Reporte (Excel o CSV)", type=["xlsx", "csv"])

    if archivo:
        # Lectura de datos
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)
        
        # Limpieza de columnas
        df.columns = df.columns.str.strip()
        
        # Estandarización de fechas
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        
        # Identificar columna de serie (puede variar el nombre)
        col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
        
        # Limpiar filas sin datos clave
        df = df.dropna(subset=['Fecha_DT', 'Folio', col_serie, 'Técnico'])

        # 2. Configuración de la Auditoría
        st.sidebar.header("Configuración")
        meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                         7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        mes_eval = st.sidebar.selectbox("Mes a evaluar", list(meses_nombres.keys()), 
                                        format_func=lambda x: meses_nombres[x], index=1) # Default Febrero
        anio_eval = st.sidebar.number_input("Año", value=2026)
        ventana_meses = st.sidebar.slider("Historial de rastreo (Meses)", 1, 12, 3)

        # 3. Lógica de "Efecto Dominó"
        # Rango: Desde (Mes Eval - Ventana) hasta el fin del Mes Eval
        fecha_fin_auditoria = datetime(anio_eval, mes_eval, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio_rastreo = datetime(anio_eval, mes_eval, 1) - relativedelta(months=ventana_meses)

        # Filtramos el universo de datos que afectan la auditoría
        df_auditoria = df[(df['Fecha_DT'] >= fecha_inicio_rastreo) & 
                          (df['Fecha_DT'] <= fecha_fin_auditoria)].copy()
        
        # Ordenamos cronológicamente por serie
        df_auditoria = df_auditoria.sort_values([col_serie, 'Fecha_DT'], ascending=True)

        # Marcado de penalizaciones
        df_auditoria['Es_Penalizacion'] = 0
        
        for serie, grupo in df_auditoria.groupby(col_serie):
            if len(grupo) > 1:
                # El último reporte de la serie NO se penaliza (es el que cerró el ciclo)
                indices_anteriores = grupo.index[:-1]
                
                for idx in indices_anteriores:
                    # REGLA: Solo penaliza si es CORRECTIVO
                    categoria = str(df_auditoria.loc[idx, 'Categoría']).upper()
                    if "CORRECT" in categoria:
                        df_auditoria.loc[idx, 'Es_Penalizacion'] = 1

        # 4. Resultados específicos del Mes de Evaluación
        df_resultados_mes = df_auditoria[(df_auditoria['Fecha_DT'].dt.month == mes_eval) & 
                                         (df_auditoria['Fecha_DT'].dt.year == anio_eval)]

        # --- VISUALIZACIÓN ---
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            st.subheader(f"Resumen General: {meses_nombres[mes_eval]}")
            resumen = df_resultados_mes.groupby('Técnico').agg(
                Servicios_Totales=('Folio', 'count'),
                Penalizaciones=('Es_Penalizacion', 'sum')
            ).reset_index()
            resumen['Efectividad_Neta'] = resumen['Servicios_Totales'] - resumen['Penalizaciones']
            st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

        with col_m2:
            st.subheader("Top Máquinas con Reincidencia")
            top_series = df_resultados_mes[df_resultados_mes['Es_Penalizacion'] == 1].groupby(col_serie).size().reset_index(name='Fallas')
            st.bar_chart(top_series.set_index(col_serie).head(10))

        # Detalle para revisión manual
        st.divider()
        st.subheader("🔍 Buscador de Evidencia (Detalle por Técnico)")
        tecnico_filtro = st.selectbox("Selecciona un técnico para ver sus penalizaciones:", 
                                      ["Todos"] + sorted(df_auditoria['Técnico'].unique().tolist()))
        
        evidencia = df_auditoria[df_auditoria['Es_Penalizacion'] == 1]
        if tecnico_filtro != "Todos":
            evidencia = evidencia[evidencia['Técnico'] == tecnico_filtro]
        
        st.write(f"Mostrando {len(evidencia)} folios penalizados.")
        st.dataframe(evidencia[[col_serie, 'Folio', 'Técnico', 'Última visita', 'Problema reportado']], use_container_width=True)

    else:
        st.info("👆 Por favor, carga el archivo Excel en la barra lateral para comenzar.")

if __name__ == "__main__":
    main()
