import pandas as pd

def get_data_universe(df, month_name, year, history_months):
    """Limpia datos y segmenta el mes actual vs el historial de reincidencias."""
    df.columns = df.columns.str.strip()
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce')
    
    months_dict = {
        "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
        "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
    }
    
    month_num = months_dict.get(month_name, 1)
    end_date = pd.Timestamp(year=year, month=month_num, day=1) + pd.offsets.MonthEnd(0)
    start_date_history = (pd.Timestamp(year=year, month=month_num, day=1) - pd.DateOffset(months=history_months))
    start_date_month = pd.Timestamp(year=year, month=month_num, day=1)
    
    df_history = df[(df['Fecha recepción'] >= start_date_history) & (df['Fecha recepción'] <= end_date)].copy()
    df_current = df[(df['Fecha recepción'] >= start_date_month) & (df['Fecha recepción'] <= end_date)].copy()
    
    return df_history, df_current

def calculate_penalties(df_history, scores):
    """Calcula el total de puntos de penalización por técnico."""
    if 'Categoría' not in df_history.columns: return pd.DataFrame(columns=['Técnico', 'Penalizaciones'])
    
    cat_target = ['CORRECTIVO', 'REINCIDENCIA']
    df_p = df_history[df_history['Categoría'].isin(cat_target)].copy()
    
    if 'Técnico' in df_p.columns:
        df_p = df_p[~df_p['Técnico'].str.contains('Sistemas', case=False, na=False)]
    
    if df_p.empty: return pd.DataFrame(columns=['Técnico', 'Penalizaciones'])

    # Ordenar por serie y fecha para encontrar la última visita
    df_p = df_p.sort_values(by=['N.° de serie', 'Fecha recepción'])
    df_p['es_ultimo'] = df_p.groupby('N.° de serie')['Fecha recepción'].transform('max') == df_p['Fecha recepción']
    
    # Se penaliza si NO fue la última visita (el problema persistió)
    df_p['Puntos'] = df_p.apply(lambda r: 0 if r['es_ultimo'] else scores.get(r['Categoría'], 1.0), axis=1)
    
    return df_p.groupby('Técnico')['Puntos'].sum().reset_index().rename(columns={'Puntos': 'Penalizaciones'})

def get_detailed_penalties(df_history, scores):
    """Detalle de folios, clientes y series que causaron la penalización."""
    cat_target = ['CORRECTIVO', 'REINCIDENCIA']
    df_p = df_history[df_history['Categoría'].isin(cat_target)].copy()
    
    if df_p.empty: return pd.DataFrame()

    df_p = df_p.sort_values(by=['N.° de serie', 'Fecha recepción'])
    df_p['es_ultimo'] = df_p.groupby('N.° de serie')['Fecha recepción'].transform('max') == df_p['Fecha recepción']
    
    df_audit = df_p[df_p['es_ultimo'] == False].copy()
    df_audit['Puntos_R'] = df_audit['Categoría'].map(scores)
    return df_audit
