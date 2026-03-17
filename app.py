import streamlit as st
import pandas as pd
import plotly.express as px

# ... (Supongamos que ya cargaste el df y calculaste la columna 'Penaliza' con la lógica anterior) ...

if uploaded_file:
    # --- LOGICA DE AGRUPACIÓN ---
    
    # Creamos la tabla agrupada por técnico
    resumen_tecnico = df.groupby('Técnico').agg(
        Reportes_Vistos=('N.° de serie', 'count'),  # Total de intervenciones (todas las categorías)
        Penalizaciones=('Penaliza', 'sum')          # Suma de 1s (solo correctivos reincidentes)
    ).reset_index()

    # Calculamos el Total (Reportes limpios de penalización)
    # Esto muestra cuántos trabajos fueron realizados correctamente sin reincidencia
    resumen_tecnico['Trabajos_Efectivos'] = resumen_tecnico['Reportes_Vistos'] - resumen_tecnico['Penalizaciones']

    st.subheader("📊 Tabla de Control de Mantenimiento")

    # Mostrar la tabla con formato de colores para las penalizaciones
    st.dataframe(
        resumen_tecnico.sort_values(by='Penalizaciones', ascending=False),
        column_config={
            "Técnico": "Técnico",
            "Reportes_Vistos": st.column_config.NumberColumn(
                "Reportes Vistos",
                help="Total de visitas realizadas (todas las categorías)"
            ),
            "Penalizaciones": st.column_config.NumberColumn(
                "Penalizaciones 🚩",
                help="Reincidencias detectadas en correctivos",
                format="%d"
            ),
            "Trabajos_Efectivos": st.column_config.NumberColumn(
                "Total Efectivo",
                help="Reportes vistos menos penalizaciones"
            )
        },
        use_container_width=True,
        hide_index=True
    )

    # --- VISUALIZACIÓN COMPLEMENTARIA ---
    st.divider()
    
    # Gráfico de barras apiladas para ver la proporción de penalizaciones vs total
    fig = px.bar(
        resumen_tecnico, 
        x='Técnico', 
        y=['Trabajos_Efectivos', 'Penalizaciones'],
        title="Proporción de Penalizaciones por Carga de Trabajo",
        labels={'value': 'Cantidad de Reportes', 'variable': 'Estado'},
        color_discrete_map={'Trabajos_Efectivos': '#2ecc71', 'Penalizaciones': '#e74c3c'},
        barmode='stack'
    )
    st.plotly_chart(fig, use_container_width=True)
