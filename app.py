import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Auditoría Real", layout="wide")

def main():
    st.title("🛡️ Auditoría SenAudit Pro")
    st.markdown("Cálculo de penalizaciones por reincidencia (Garantía de 3 meses).")

    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio", type=["xlsx", "xlsb"])

    if archivo:
        try:
            # 1. CARGA TOTAL (Sin filtrar nada aún)
            engine = 'openpyxl' if archivo.name.endswith('xlsx') else 'pyxlsb'
            df = pd.read_excel(archivo, engine=engine)
            df.columns = df.columns.str.strip()
            
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()
            
            # 2. PARÁMETROS
            st.sidebar.header("Configuración")
            dias_garantia = st.sidebar.slider("Días de garantía", 1, 365, 90)
            
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = st.sidebar.selectbox("Mes a auditar", meses_nombres, index=datetime.now().month - 1)
            mes_num = meses_nombres.index(mes_sel) + 1
            anio_eval = st.sidebar.number_input("Año", value=2026)

            # 3. MATEMÁTICAS PANDAS (Lógica de "El último es intocable")
            # Ordenamos todo el universo de datos
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # Calculamos la reincidencia mirando HACIA ADELANTE en todo el archivo
            df['Fecha_Sig'] = df.groupby(col_serie)['Fecha_DT'].shift(-1)
            df['Folio_Sig'] = df.groupby(col_serie)['Folio'].shift(-1)
            df['Dias_Diff'] = (df['Fecha_Sig'] - df['Fecha_DT']).dt.days

            # Aplicamos la penalización: 
            # SI tiene un siguiente AND es Correctivo/Resuelta AND está en rango de días
            cond_cat = df['Categoría'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            cond_est = df['Estatus'].astype(str).str.upper().str.contains('RESUELTA', na=False)
            cond_dias = (df['Dias_Diff'] >= 0) & (df['Dias_Diff'] <= dias_garantia)

            df['Es_Penalizacion'] = (cond_cat & cond_est & cond_dias).astype(int)

            # 4. FILTRADO PARA MOSTRAR SOLO EL MES ELEGIDO
            # Aquí es donde separamos lo que queremos ver, pero la penalización ya se calculó
            # usando incluso folios de meses siguientes si fue necesario.
            df_mes = df[(df['Fecha_DT'].dt.month == mes_num) & (df['Fecha_DT'].dt.year == anio_eval)].copy()

            # --- VISUALIZACIÓN ---
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(f"Resumen {mes_sel}")
                resumen = df_mes.groupby('Técnico').agg(
                    Total_Servicios=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                resumen['% Efectividad'] = ((resumen['Total_Servicios'] - resumen['Penalizaciones']) / resumen['Total_Servicios'] * 100).round(1)
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True, hide_index=True)

            with col2:
                st.subheader("Verificar Técnico")
                tec = st.text_input("Nombre:").upper()
                if tec:
                    puntos = df_mes[df_mes['Técnico'].str.contains(tec, na=False)]['Es_Penalizacion'].sum()
                    st.metric(f"Penalizaciones de {tec}", puntos)

            st.divider()
            st.subheader(f"Lista de Evidencia ({mes_sel})")
            # Solo mostramos los que SI penalizaron para que los compares con tus 89
            evidencia = df_mes[df_mes['Es_Penalizacion'] == 1]
            if not evidencia.empty:
                st.dataframe(evidencia[[col_serie, 'Folio', 'Técnico', 'Fecha_DT', 'Dias_Diff', 'Folio_Sig']], use_container_width=True)
            else:
                st.info("No se encontraron penalizaciones con estos filtros.")

        except Exception as e:
            st.error(f"Error: {e}")
            
