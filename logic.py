import pandas as pd

def process_data(df, target_date, history_months):
    # Limpieza de nombres de columnas por si acaso
    df.columns = df.columns.str.strip()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'])
    
    end_date = pd.Timestamp(target_date)
    start_date = end_date - pd.DateOffset(months=history_months)
    
    return df[(df['Fecha recepción'] >= start_date) & (df['Fecha recepción'] <= end_date)].copy()

def calculate_penalties(df, scores):
    cat_target = ['CORRECTIVO', 'REINCIDENCIA']
    
    # Filtro: Categorías y exclusión de Sistemas
    df_penal = df[df['Categoría'].isin(cat_target)].copy()
    df_penal = df_penal[~df_penal['Técnico'].str.contains('Sistemas', case=False, na=False)]
    
    if df_penal.empty:
        return pd.DataFrame(columns=['Técnico', 'CORRECTIVO', 'REINCIDENCIA', 'Total penalizaciones'])

    # Lógica: Ordenar por serie y fecha
    df_penal = df_penal.sort_values(by=['N.° de serie', 'Fecha recepción'])
    
    # El último técnico NO se penaliza (is_last = True)
    df_penal['is_last'] = df_penal.groupby('N.° de serie')['Fecha recepción'].transform('max') == df_penal['Fecha recepción']
    
    def get_points(row):
        return 0 if row['is_last'] else scores.get(row['Categoría'], 1.0)

    df_penal['Puntos'] = df_penal.apply(get_points, axis=1)
    
    # Agrupar por técnico
    matriz = df_penal.groupby(['Técnico', 'Categoría'])['Puntos'].sum().unstack(fill_value=0)
    for col in cat_target:
        if col not in matriz.columns: matriz[col] = 0
            
    matriz['Total penalizaciones'] = matriz['CORRECTIVO'] + matriz['REINCIDENCIA']
    return matriz.reset_index()
