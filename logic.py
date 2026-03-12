import pandas as pd

def process_data(df, target_date, history_months):
    # Limpiar espacios en nombres de columnas
    df.columns = df.columns.str.strip()
    # Convertir a fecha la columna del reporte
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'])
    
    end_date = pd.Timestamp(target_date)
    start_date = end_date - pd.DateOffset(months=history_months)
    
    mask = (df['Fecha recepción'] >= start_date) & (df['Fecha recepción'] <= end_date)
    return df[mask].copy()

def calculate_penalties(df, scores):
    # Categorías que reciben penalización
    cat_target = ['CORRECTIVO', 'REINCIDENCIA']
    
    # Filtrar datos: Solo categorías objetivo y quitar a "Sistemas"
    df_penal = df[df['Categoría'].isin(cat_target)].copy()
    df_penal = df_penal[~df_penal['Técnico'].str.contains('Sistemas', case=False, na=False)]
    
    if df_penal.empty:
        return pd.DataFrame(columns=['Técnico', 'CORRECTIVO', 'REINCIDENCIA', 'Total penalizaciones'])

    # Ordenar por número de serie y fecha para ver quién fue el último
    df_penal = df_penal.sort_values(by=['N.° de serie', 'Fecha recepción'])
    
    # Identificar la última visita por cada equipo (N.° de serie)
    # El último técnico NO recibe puntos de penalización
    df_penal['es_ultimo'] = df_penal.groupby('N.° de serie')['Fecha recepción'].transform('max') == df_penal['Fecha recepción']
    
    def get_points(row):
        # Si es el último técnico en tocar el equipo, puntos = 0
        if row['es_ultimo']:
            return 0
        # Si hubo alguien después de él, se aplica el puntaje configurado
        return scores.get(row['Categoría'], 1.0)

    df_penal['Puntos_Penalizacion'] = df_penal.apply(get_points, axis=1)
    
    # Crear la matriz por técnico
    matriz = df_penal.groupby(['Técnico', 'Categoría'])['Puntos_Penalizacion'].sum().unstack(fill_value=0)
    
    # Asegurar que aparezcan las columnas aunque no haya datos
    for col in cat_target:
        if col not in matriz.columns: matriz[col] = 0
            
    matriz['Total penalizaciones'] = matriz['CORRECTIVO'] + matriz['REINCIDENCIA']
    return matriz.reset_index()
