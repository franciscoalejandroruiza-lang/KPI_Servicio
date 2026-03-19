import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Garantía 3 Meses", layout="wide")

def main():
    st.title("🛡️ Auditoría de Garantía: SenAudit Pro")
    st.markdown("### Objetivo: Penalizar el trabajo mal hecho en el pasado detectado hoy.")

    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio", type=["xlsx", "xlsb"])

    if archivo:
        try:
            # 1. Carga y Normalización
            engine = 'openpyxl' if archivo.name.endswith('xlsx') else 'pyxlsb'
            df = pd.read_excel(archivo, engine=engine)
            df.columns = df.columns.str.strip()
            
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper()

            # 2. Configuración del Mes de Auditoría (El "Escáner")
            st.sidebar.header("Mes de Detección")
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = st.sidebar.selectbox("Ver fallas de:", meses_nombres, index=1)
            anio_sel = st.sidebar.number_input("Año", value=2026)
            mes_num = meses_nombres.index(mes_sel) + 1

            # --- LÓGICA DE PENALIZACIÓN RETROACTIVA ---
            
            # Ordenamos todo el historial
            df = df.sort_values([col_serie, 'Fecha_DT'], ascending=True)

            # Usamos SHIFT(1) para mirar al pasado
            # Cada fila (falla de hoy) mira quién fue el técnico anterior en esa serie
            df['Tecnico_Anterior'] = df.groupby(col_serie)['Técnico'].shift(1)
            df['Fecha_Anterior'] = df.groupby(col_serie)['Fecha_DT'].shift(1)
            df['Folio_Anterior'] = df.groupby(col_serie)['Folio'].shift(1)
            df['Estatus_Anterior'] = df.groupby(col_serie)['Estatus'].shift(1)
            df['Cat_Anterior'] = df.groupby(col_serie)['Categoría'].shift(1)

            # Cálculo de días que duró la reparación anterior
            df['Dias_Duracion'] = (df['Fecha_DT'] - df['Fecha_Anterior']).dt.days

            # REGLA DE CASTIGO:
            # Si hoy (Febrero) hay un CORRECTIVO y hace menos de 90 días 
            # alguien (Diciembre/Enero) la entregó como RESUELTA/CORRECTIVO.
            es_falla_hoy = df['Categoría'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            fue_resuelta_antes = df['Estatus_Anterior'].astype(str).str.upper().str.contains('RESUELTA', na=False)
            fue_correctivo_antes = df['Cat_Anterior'].astype(str).str.upper().str.contains('CORRECTIVO', na=False)
            dentro_garantia = (df['Dias_Duracion'] >= 0) & (df['Dias_Duracion'] <= 90)

            df['Penalizar_Al_Anterior'] = (es_falla_hoy & fue_resuelta_antes & fue_correctivo_antes & dentro_garantia).astype(int)

            # --- FILTRADO: Solo mostramos las fallas detectadas en el mes seleccionado ---
            df_deteccion = df[(df['Fecha_DT'].dt.month == mes_num) & (df['Fecha_DT'].dt.year == anio_sel)].copy()

            # --- INTERFAZ ---
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(f"Técnicos Penalizados por fallas en {mes_sel}")
                # Aquí agrupamos por el TÉCNICO ANTERIOR (el que trabajó mal)
                resumen_castigo = df_deteccion.groupby('Tecnico_Anterior').agg(
                    Fallas_Detectadas_Hoy=('Penalizar_Al_Anterior', 'sum')
                ).reset_index().rename(columns={'Tecnico_Anterior': 'Técnico Responsable'})
                
                st.dataframe(resumen_castigo.sort_values('Fallas_Detectadas_Hoy', ascending=False), use_container_width=True, hide_index=True)

            with col2:
                st.subheader("⚠️ ¿A quién castigó Febrero?")
                tec = st.text_input("Nombre del técnico:").upper()
                if tec:
                    puntos = resumen_castigo[resumen_castigo['Técnico Responsable'].str.contains(tec, na=False)]['Fallas_Detectadas_Hoy'].sum()
                    st.metric(f"Penalizaciones acumuladas", int(puntos))

            st.divider()
            st.subheader("📋 Detalle: Quién trabajó la máquina antes de que fallara hoy")
            evidencia = df_deteccion[df_deteccion['Penalizar_Al_Anterior'] == 1]
            if not evidencia.empty:
                st.write(f"En {mes_sel} fallaron estas máquinas. Se penaliza al técnico que las vio antes:")
                st.dataframe(evidencia[[col_serie, 'Folio', 'Fecha_DT', 'Tecnico_Anterior', 'Folio_Anterior', 'Fecha_Anterior', 'Dias_Duracion']].rename(
                    columns={
                        'Folio': 'Folio Falla Hoy',
                        'Fecha_DT': 'Fecha Falla Hoy',
                        'Tecnico_Anterior': 'Técnico a Penalizar',
                        'Folio_Anterior': 'Folio Mal Hecho',
                        'Dias_Duracion': 'Días que aguantó'
                    }
                ), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error: {e}")
