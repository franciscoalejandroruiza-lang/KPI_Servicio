import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro - Automatizado", layout="wide")

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
