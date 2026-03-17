import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit - Parte 2", layout="wide")

def main():
    st.title("📊 Parte 2: Análisis de Reincidencias y Penalizaciones")
    
    st.sidebar.header("Configuración de Auditoría")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:
        # 1. Carga de datos
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo, engine='openpyxl')
        
        # Limpieza y conversión de fechas
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        df = df.dropna(subset=['Fecha_DT', 'Folio', 'N.° de serie'])

        # 2. Configuración de Rango de fechas
        meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                      7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        
        col1, col2 = st.sidebar.columns(2)
        mes_eval = col1.selectbox("Mes a evaluar", options=range(1, 13), format_func=lambda x: meses_dict[x], index=1)
        anio_eval = col2.number_input("Año", value=2026)
        
        # AQUÍ ESTÁ TU APARTADO:
        meses_atras = st.sidebar.slider("Meses de historial hacia atrás", 0, 6, 3)
        dias_ventana = st.sidebar.number_input("Días para reincidencia", value=15)

        # 3. Cálculo de Fechas
        # Fecha fin: último día del mes seleccionado
        fecha_fin = datetime(anio_eval, mes_eval, 1) + relativedelta(months=1) - relativedelta(days=1)
        # Fecha inicio: N meses atrás desde el inicio del mes seleccionado
        fecha_inicio = datetime(anio_eval, mes_eval, 1) - relativedelta(months=meses_atras)

        st.sidebar.info(f"Analizando desde: {fecha_inicio.strftime('%d/%m/%Y')} hasta: {fecha_fin.strftime('%d/%m/%Y')}")

        # 4. Filtrado de Datos
        # Filtramos todo el rango para buscar reincidencias
        mask_rango = (df['Fecha_DT'] >= pd.Timestamp(fecha_inicio)) & (df['Fecha_DT'] <= pd.Timestamp(fecha_fin))
        df_rango = df.loc[mask_rango].copy().drop_duplicates(subset=['Folio'])

        # 5. LÓGICA DE PENALIZACIÓN
        df_rango['Es_Reincidente'] = False
        # Ordenamos por serie y fecha (reciente primero)
        df_rango = df_rango.sort_values(['N.° de serie', 'Fecha_DT'], ascending=[True, False])

        for serie, grupo in df_rango.groupby('N.° de serie'):
            if len(grupo) > 1:
                indices = grupo.index
                for i in range(len(indices) - 1):
                    # Comparamos reporte actual (i) con el anterior en el tiempo (i+1)
                    diff = (df_rango.loc[indices[i], 'Fecha_DT'] - df_rango.loc[indices[i+1], 'Fecha_DT']).days
                    
                    if diff <= dias_ventana:
                        # REGLA: Solo penaliza si el anterior era CORRECTIVO
                        if str(df_rango.loc[indices[i+1], 'Categoría']).upper() == 'CORRECTIVO':
                            df_rango.loc[indices[i+1], 'Es_Reincidente'] = True

        # 6. FILTRO FINAL PARA EL REPORTE
        # Solo mostramos en el resumen los folios que ocurrieron EN EL MES EVALUADO
        mask_mes_eval = (df_rango['Fecha_DT'].dt.month == mes_eval) & (df_rango['Fecha_DT'].dt.year == anio_eval)
        df_reporte = df_rango.loc[mask_mes_eval]

        # 7. VISUALIZACIÓN DE RESULTADOS
        resumen = df_reporte.groupby('Técnico').agg(
            Resueltos=('Folio', 'count'),
            Penalizados=('Es_Reincidente', 'sum')
        ).reset_index()
        
        resumen['Efectividad %'] = ((resumen['Resueltos'] - resumen['Penalizados']) / resumen['Resueltos'] * 100).round(1)
        
        st.subheader(f"📊 Relación de Desempeño: {meses_dict[mes_eval]} {anio_eval}")
        st.table(resumen.sort_values('Resueltos', ascending=False))

        with st.expander("Ver detalle de folios analizados (Marcados en rojo las penalizaciones)"):
            def color_penalizado(row):
                return ['background-color: #ffcccc' if row.Es_Reincidente else '' for _ in row]
            st.dataframe(df_reporte.style.apply(color_penalizado, axis=1))

    else:
        st.info("Carga el archivo para aplicar la lógica de historial.")

if __name__ == "__main__":
    main()
