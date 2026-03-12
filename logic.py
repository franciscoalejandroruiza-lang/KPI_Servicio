import pandas as pd

def get_data_universe(df, month_name, year, history_months):
    df.columns = df.columns.str.strip()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'])
    
    months_dict = {
        "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
        "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
    }
    
    month_num = months_dict[month_name]
    
    # Fecha final (fin del mes seleccionado)
    end_date = pd.Timestamp(year=year, month=month_num, day=1) + pd.offsets.MonthEnd(0)
    # Fecha inicial (incluyendo el historial)
    start_date_history = (pd.Timestamp(year=year, month=month_num, day=1) - pd.DateOffset(months=history_months))
    # Fecha inicial (solo el mes seleccionado)
    start_date_month = pd.Timestamp(year=year, month=month_num, day=1)
    
    df_history = df[(df['Fecha recepción'] >= start_date_history) & (df['Fecha recepción'] <= end_date)].copy()
    df_current = df[(df['Fecha recepción'] >= start_date_month) & (df['Fecha recepción'] <= end_date)].copy()
    
    return df_history, df_current

def calculate_penalties(df_history, scores):
    cat_target = ['CORRECTIVO', 'REINCIDENCIA']
    df_penal = df_history[df_history['Categoría'].isin(cat_target)].copy()
    
    # Excluir Sistemas
    df_penal = df_penal[~df_penal['Técnico'].str.contains('Sistemas', case=False, na=False)]
    
    if df_penal.empty:
        return pd.DataFrame(columns=['Técnico', 'Penalizaciones'])

    # Lógica de "Última visita" sobre el historial completo
    df_penal = df_penal.sort_values(by=['N.° de serie', 'Fecha recepción'])
    df_penal['es_ultimo'] = df_penal.groupby('N.° de serie')['Fecha recepción'].transform('max') == df_penal['Fecha recepción']
    
    # Solo penaliza a los que NO fueron los últimos en el historial
    def get_points(row):
        return 0 if row['es_ultimo'] else scores.get(row['Categoría'], 1.0)

    df_penal['Puntos_Penalizacion'] = df_penal.apply(get_points, axis=1)
    
    resumen_p = df_penal.groupby('Técnico')['Puntos_Penalizacion'].sum().reset_index()
    resumen_p.columns = ['Técnico', 'Penalizaciones']
    return resumen_p
