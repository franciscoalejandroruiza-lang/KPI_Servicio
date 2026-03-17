import streamlit as st
import pandas as pd
import plotly.express as px

# ... (Mantener la lógica de procesamiento anterior para calcular 'Penaliza') ...

if uploaded_file:
    # --- PROCESAMIENTO ---
    # (El código previo que calcula df['Penaliza'] y df['Es_ultima'])

    st.subheader("📋 Resumen de Desempeño por Técnico")

    # 1. Crear la tabla resumen agrupando por Técnico
    resumen_tabla = df.groupby('Técnico').agg(
        Reportes_Vistos=('N.° de serie', 'count'),  # Cuenta todas las filas (todas las categorías)
        Penalizaciones=('Penaliza', 'sum')          # Suma los 1 detectados (solo correctivos reincidentes)
    ).reset_index()

    # 2. Calcular la columna Total (o Score final)
    # Aquí puedes definir si el 'Total' es la resta, o simplemente mostrar los datos
    resumen_tabla['Efectividad %'] = ((resumen_tabla['Reportes_Vistos'] - resumen_tabla['Penalizaciones']) / resumen_tabla['Reportes_Vistos'] * 100).round(1)

    # 3. Mostrar la tabla con formato profesional
    st.dataframe(
        resumen_tabla.sort_values(by='Penalizaciones', ascending=False),
        column_config={
            "Técnico": "Nombre del Técnico",
            "Reportes_Vistos": st.column_config.NumberColumn("Total Reportes", help="Incluye Correctivos, Preventivos, etc."),
            "Penalizaciones": st.column_config.NumberColumn("Penalizaciones 🚩", help="Solo reincidencias en Correctivos"),
            "Efectividad %": st.column_config.ProgressColumn("Índice de Solución", format="%d%%", min_value=0, max_value=100)
        },
        use_container_width=True,
        hide_index=True
    )

    # 4. Gráfico comparativo rápido
    fig_comparativo = px.bar(
        resumen_tabla, 
        x='Técnico', 
        y=['Reportes_Vistos', 'Penalizaciones'],
        barmode='group',
        title="Reportes Totales vs. Penalizaciones",
        labels={'value': 'Cantidad', 'variable': 'Métrica'},
        color_discrete_map={'Reportes_Vistos': '#3498db', 'Penalizaciones': '#e74c3c'}
    )
    st.plotly_chart(fig_comparativo, use_container_width=True)
