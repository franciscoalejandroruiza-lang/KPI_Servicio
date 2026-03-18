import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SenAudit Pro - Validación Exacta", layout="wide")

def main():
    st.title("🛡️ Auditoría SenAudit Pro: Validación de Datos")
    st.markdown("Comparación de folios reincidentes para técnicos de campo.")

    archivo = st.sidebar.file_uploader("Subir Reporte de Servicio (.xlsx)", type=["xlsx"])

    if archivo:
        try:
            # 1. Carga y Normalización TOTAL
            df = pd.read_excel(archivo, engine='openpyxl')
            df.columns = df.columns.str.strip()
            
            # Identificación de columnas
            col_fecha = 'Fecha recepción' if 'Fecha recepción' in df.columns else 'Última visita'
            col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
            
            # Limpieza agresiva de datos
            df['Fecha_DT'] = pd.to_datetime(df[col_fecha], errors='coerce').dt.tz_localize(None)
            df['Técnico'] = df['Técnico'].str.strip().str.upper() # Evita errores por minúsculas/espacios
            
            # 2. El Filtro que definimos: Solo Correctivos Resueltos
            # NOTA: Si tus 89 penalizaciones incluyen 'Preventivos', quita este filtro.
            df_valido = df[
                (df['Categoría'].str.contains('CORRECTIVO', case=False, na=False)) & 
                (df['Estatus'].str.contains('RESUELTA', case=False, na=False))
            ].copy()

            # --- CONFIGURACIÓN ---
            dias_garantia = st.sidebar.slider("Días de garantía para reincidencia", 1, 365, 30)
            meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            mes_sel = st.sidebar.selectbox("Mes a consultar", meses_nombres, index=datetime.now().month - 1)
            mes_num = meses_nombres.index(mes_sel) + 1

            # 3. Lógica de Penalización (Barrido por Serie)
            df_valido = df_valido.sort_values([col_serie, 'Fecha_DT'], ascending=True)
            df_valido['Es_Penalizacion'] = 0
            df_valido['Días_Transcurridos'] = 0
            df_valido['Folio_Siguiente'] = ""

            for serie, grupo in df_valido.groupby(col_serie):
                if len(grupo) > 1:
                    # Analizamos todas las visitas de la máquina
                    for i in range(len(grupo) - 1):
                        idx_actual = grupo.index[i]
                        idx_sig = grupo.index[i+1]
                        
                        dif = (df_valido.loc[idx_sig, 'Fecha_DT'] - df_valido.loc[idx_actual, 'Fecha_DT']).days
                        
                        # Si vuelve a fallar dentro del rango, se penaliza al técnico actual
                        if 0 <= dif <= dias_garantia:
                            df_valido.at[idx_actual, 'Es_Penalizacion'] = 1
                            df_valido.at[idx_actual, 'Días_Transcurridos'] = dif
                            df_valido.at[idx_actual, 'Folio_Siguiente'] = df_valido.loc[idx_sig, 'Folio']

            # 4. Resultados del Mes
            df_mes = df_valido[df_valido['Fecha_DT'].dt.month == mes_num].copy()

            # --- VISUALIZACIÓN ---
            c1, c2 = st.columns([1, 1])
            with c1:
                st.subheader(f"Resumen {mes_sel}")
                resumen = df_mes.groupby('Técnico').agg(
                    Total_Correctivos=('Folio', 'count'),
                    Penalizaciones=('Es_Penalizacion', 'sum')
                ).reset_index()
                st.dataframe(resumen.sort_values('Penalizaciones', ascending=False), use_container_width=True)

            with c2:
                # Buscador específico para Alejandro o cualquier técnico
                st.subheader("🔎 Auditor de Técnico Específico")
                tecnico_buscado = st.text_input("Escribe el nombre del técnico para validar sus 89 folios:", "ALEJANDRO RUIZ").upper()
                
                if tecnico_buscado:
                    detalles = df_mes[df_mes['Técnico'].str.contains(tecnico_buscado, na=False)]
                    total_pen = detalles['Es_Penalizacion'].sum()
                    st.metric(f"Penalizaciones de {tecnico_buscado}", total_pen)
                    
                    if total_pen != 89:
                        st.warning(f"El sistema cuenta {total_pen}. Si tú cuentas 89, revisa si estás contando folios que no son 'Correctivos' o que pasan los {dias_garantia} días.")

            st.divider()
            st.subheader("📋 Evidencia Detallada (Para conciliación)")
            st.write("Esta tabla muestra folio por folio por qué se aplicó la penalización:")
            st.dataframe(df_mes[df_mes['Es_Penalizacion'] == 1][[col_serie, 'Folio', 'Técnico', 'Fecha_DT', 'Días_Transcurridos', 'Folio_Siguiente']], use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("Carga el archivo para auditar los folios.")

if __name__ == "__main__":
    main()
