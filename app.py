import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Auditoría Anual", layout="wide")

def main():
    st.title("🛡️ Auditoría de Servicios y Reincidencias")
    st.markdown("Configurado para análisis de hasta 365 días de garantía.")

    # 1. Carga de Archivo Excel
    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio (.xlsx)", type=["xlsx"])

    if archivo:
        try:
            # Lectura de Excel con motor optimizado
            df = pd.read_excel(archivo, engine='openpyxl')
            df.columns = df.columns.str.strip()
            
            # Identificación de columnas
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Limpieza y conversión
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce')
            df = df.dropna(subset=['Fecha_DT', col_serie, 'Técnico'])
            
            # 2. Configuración de la Auditoría (Hasta 365 días)
            st.sidebar.header("Parámetros de Garantía")
            
            # Ajuste solicitado: Slider de 1 a 365 días
            dias_garantia = st.sidebar.slider("Días de garantía para reincidencia", 1, 365, 30)
            
            st.sidebar.divider()
            meses_nombres = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
                             7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
            
            mes_eval = st.sidebar.selectbox("Mes a visualizar", list(meses_nombres.keys()), 
                                            format_func=lambda x: meses_nombres[x], index=datetime.now().month - 1)
            anio_eval = st.sidebar.number_input("Año", value=2026)

            # 3. Lógica de Auditoría Global
            # Ordenamos todo el historial por equipo y fecha
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)
            df['Es_Penalizacion'] = 0
            df['Detalle_Falla'] = ""

            # Análisis de reincidencia equipo por equipo
            for serie, grupo in df.groupby(col_serie):
                if len(grupo) > 1:
                    # Comparamos cada visita con la inmediata posterior
                    for i in range(len(grupo) - 1):
                        idx_actual = grupo.index[i]
                        idx_siguiente = grupo.index[i+1]
                        
                        # Calculamos los días que pasaron hasta la siguiente falla
                        dif = (df.loc[idx_siguiente, 'Fecha_DT'] - df.loc[idx_actual, 'Fecha_DT']).days
                        
                        # Si la visita actual fue CORRECTIVO y el equipo volvió a fallar dentro del rango
                        if "CORRECT" in str(df.loc[idx_actual, 'Categoría']).upper() and 0 <= dif <= dias_garantia:
                            df.at[idx_actual, 'Es_Penalizacion'] = 1
                            folio_reincidente = df.loc[idx_siguiente, 'Folio']
                            df.at[idx_actual, 'Detalle_Falla'] = f"Reincidencia en {dif} días (Folio {folio_reincidente})"

            # 4. Filtrado del mes para el reporte visual
            df_mes = df[(df['Fecha_DT'].dt.month == mes_eval) & (df['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- DASHBOARD ---
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader(f"Efectividad de Técnicos - {meses_nombres[mes_eval]}")
                resumen = df_mes.groupby('Técnico').agg(
                    Servicios=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                resumen['Efectividad %'] = ((resumen['Servicios'] - resumen['Penalizaciones']) / resumen['Servicios'] * 100).round(1)
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with c2:
                st.subheader("Tendencia de Penalizaciones")
                if not resumen.empty:
                    st.bar_chart(resumen.set_index('Técnico')['Penalizaciones'])

            # Evidencia detallada
            st.divider()
            st.subheader(f"🔍 Auditoría de Reincidencias (Garantía de {dias_garantia} días)")
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            
            if not evidencia.empty:
                st.dataframe(evidencia[['Folio', 'Técnico', col_serie, 'Fecha_DT', 'Detalle_Falla']], use_container_width=True)
            else:
                st.success(f"No hay reincidencias detectadas en el rango de {dias_garantia} días para este mes.")

        except Exception as e:
            st.error(f"Error al procesar el Excel: {e}")

    else:
        st.info("👈 Por favor, carga el archivo Excel para iniciar el escaneo de 365 días.")

if __name__ == "__main__":
    main()
