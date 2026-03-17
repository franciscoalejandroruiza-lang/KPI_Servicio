import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def analizar_datos_exactos(df, mes_base, anio_base, meses_atras):
    # 1. Limpieza inicial y conversión de tipos
    df['Fecha'] = pd.to_datetime(df['Última visita'], errors='coerce')
    df = df.dropna(subset=['Fecha', 'Folio'])
    
    # 2. Definir el rango de fechas exacto
    fecha_fin = datetime(anio_base, mes_base, 1) + relativedelta(months=1) - relativedelta(days=1)
    fecha_inicio = datetime(anio_base, mes_base, 1) - relativedelta(months=meses_atras)
    
    # 3. FILTRO CRÍTICO: Solo estatus RESUELTA y dentro del rango de fechas
    mask = (
        (df['Fecha'] >= pd.Timestamp(fecha_inicio)) & 
        (df['Fecha'] <= pd.Timestamp(fecha_fin)) & 
        (df['Estatus'].str.upper() == 'RESUELTA')
    )
    df_periodo = df.loc[mask].copy()
    
    # Eliminar posibles duplicados de folios para evitar el conteo doble (210 vs 105)
    df_periodo = df_periodo.drop_duplicates(subset=['Folio'])

    # 4. LÓGICA DE PENALIZACIÓN (Solo para CORRECTIVOS reincidentes)
    df_periodo['Es_Reincidente'] = False
    
    # Agrupamos por serie para comparar historial
    for serie, grupo in df_periodo.groupby('N.° de serie'):
        if len(grupo) > 1:
            # Ordenar por fecha para identificar el orden de visitas
            grupo = grupo.sort_values('Fecha', ascending=False)
            indices = grupo.index
            
            # El primero (más reciente) es el que solucionó. 
            # Los anteriores (i+1) se analizan:
            for i in range(len(indices) - 1):
                # REGLA: Si el reporte anterior fue CORRECTIVO y RESUELTO, se penaliza
                # por no haber sido una solución definitiva ante la nueva falla.
                if df_periodo.loc[indices[i+1], 'Categoría'].upper() == 'CORRECTIVO':
                    df_periodo.loc[indices[i+1], 'Es_Reincidente'] = True
                    
    return df_periodo

# --- INTERFAZ STREAMLIT ---
# (Asumiendo que ya tienes la carga de archivo configurada arriba)
# ... 

if 'df' in locals():
    # Ejecutar el análisis con los parámetros de la UI
    resultado = analizar_datos_exactos(df, mes_base, anio_base, meses_atras)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Reportes Resueltos (Netos)", len(resultado))
    with col2:
        penalizados = resultado['Es_Reincidente'].sum()
        st.metric("Reportes Penalizados (Correctivos)", int(penalizados))

    st.dataframe(resultado)
