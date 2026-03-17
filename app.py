import pandas as pd

# 1. Cargar los datos (Asegúrate de que el nombre del archivo coincida)
df = pd.read_excel('reportes_tecnicos.xlsx')

# 2. Preparación de datos
# Convertimos a datetime para asegurar que el orden cronológico sea real
df['Última visita'] = pd.to_datetime(df['Última visita'])

# Limpieza básica: Eliminar filas sin número de serie o fecha
df = df.dropna(subset=['N.° de serie', 'Última visita'])

# 3. Lógica Maestra: Ordenar y Agrupar
# Ordenamos por serie y fecha (antiguo a reciente)
df = df.sort_values(by=['N.° de serie', 'Última visita'], ascending=True)

# Identificamos la última intervención de cada equipo
# (Transform permite marcar cada fila del grupo con el valor máximo de su fecha)
df['Es_ultima'] = 0
df.loc[df.groupby('N.° de serie')['Última visita'].idxmax(), 'Es_ultima'] = 1

# 4. Aplicar Penalización (SOLO CORRECTIVOS QUE NO SEAN EL ÚLTIMO)
def calcular_penalizacion(row):
    if row['Categoría'] == 'CORRECTIVO' and row['Es_ultima'] == 0:
        return 1
    return 0

df['Penaliza'] = df.apply(calcular_penalizacion, axis=1)

# 5. Generar Resumen por Técnico
resumen_tecnicos = df.groupby('Técnico')['Penaliza'].sum().reset_index()
resumen_tecnicos.columns = ['Técnico', 'Total de Penalizaciones']

# --- RESULTADOS ---
print("--- Muestra del DataFrame Procesado ---")
print(df[['N.° de serie', 'Técnico', 'Última visita', 'Categoría', 'Es_ultima', 'Penaliza']].head(15))

print("\n--- Tabla de Penalizaciones por Técnico ---")
print(resumen_tecnicos.sort_values(by='Total de Penalizaciones', ascending=False))

# Opcional: Guardar a un nuevo Excel
# df.to_excel('analisis_penalizaciones_final.xlsx', index=False)
