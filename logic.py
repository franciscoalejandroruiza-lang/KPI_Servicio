import pandas as pd

def get_data_universe(df, month_name, year, history_months):
    """Limpia datos y segmenta el universo actual vs el historial de reincidencias."""
    df.columns = df.columns.str.strip()
    # Conversión segura de fechas para evitar errores por formato
    df['Fecha recepción'] = pd.to_datetime(df['Fecha recepción'], errors='coerce') [cite: 1]
    
    months_dict = {
        "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
        "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12
    }
    
    month_num = months_dict.get(month_name, 3)
    
    # Definición de rangos temporales para el análisis
    end_date = pd.Timestamp(year=year, month=month_num, day=1) + pd.offsets.MonthEnd(0)
    start_date_history = (pd.Timestamp(year=year, month=month_num, day=1) - pd.DateOffset(months=history_months))
    start_date_month = pd.Timestamp(year=year, month=month_num, day=1)
    
    df_history = df[(df['Fecha recepción'] >= start_date_history) & (df['Fecha recepción'] <= end_date)].copy()
    df_current = df[(df['Fecha recepción'] >= start_date_month) & (df['Fecha recepción'] <= end_date)].copy()
    
    return df_history, df_current

def calculate_penalties(df_history, scores):
    """Calcula el puntaje de penalización total por técnico basado en la última visita."""
    cat_target = ['CORRECTIVO', 'REINCIDENCIA']
    df_penal = df_history[df_history['Categoría'].isin(cat_target)].copy()
    
    # Exclusión de personal de Sistemas para no sesgar KPIs técnicos
    if 'Técnico' in df_penal.columns:
        df_penal = df_penal[~df_penal['Técnico'].str.contains('Sistemas', case=False, na=False)]
    
    if df_penal.empty:
        return pd.DataFrame(columns=['Técnico', 'Penalizaciones'])

    # Lógica de Responsabilidad: Se penaliza si NO fue la última visita registrada
    df_penal = df_penal.sort_values(by=['N.° de serie', 'Fecha recepción'])
    df_penal['es_ultimo'] = df_penal.groupby('N.° de serie')['Fecha recepción'].transform('max') == df_penal['Fecha recepción']
    
    def get_points(row):
        return 0 if row['es_ultimo'] else scores.get(row['Categoría'], 1.0)

    df_penal['Puntos_Penalizacion'] = df_penal.apply(get_points, axis=1)
    
    return df_penal.groupby('Técnico')['Puntos_Penalizacion'].sum().reset_index().rename(columns={'Puntos_Penalizacion': 'Penalizaciones'})

def get_detailed_penalties(df_history, scores):
    """Extrae el detalle granular (Folio, Cliente, Serie) para auditoría de mejora continua."""
    cat_target = ['CORRECTIVO', 'REINCIDENCIA']
    df_penal = df_history[df_history['Categoría'].isin(cat_target)].copy()
    
    if 'Técnico' in df_penal.columns:
        df_penal = df_penal[~df_penal['Técnico'].str.contains('Sistemas', case=False, na=False)]
    
    if df_penal.empty: 
        return pd.DataFrame()

    df_penal = df_penal.sort_values(by=['N.° de serie', 'Fecha recepción'])
    df_penal['es_ultimo'] = df_penal.groupby('N.° de serie')['Fecha recepción'].transform('max') == df_penal['Fecha recepción']
    
    # Filtramos solo los eventos que "rebotaron" (generaron penalización)
    df_audit = df_penal[df_penal['es_ultimo'] == False].copy()
    df_audit['Puntos'] = df_audit['Categoría'].map(scores)
    
    return df_audit
