import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="SenAudit Pro - Chihuahua", layout="wide")

def main():
    st.title("🛡️ Sistema de Auditoría: Control de Penalizaciones")

    # =============================
    # SIDEBAR - CONFIGURACIÓN
    # =============================
    st.sidebar.header("⚙️ Configuración")
    archivo = st.sidebar.file_uploader("Cargar Reporte Excel", type=["xlsx", "csv"])

    if archivo:
        # Carga inteligente de archivos
        df = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo)
        
        # Limpieza de nombres de columnas (quita espacios invisibles)
        df.columns = df.columns.str.strip()

        # CORRECCIÓN DE COLUMNA: Usamos 'N.° de serie' que es el estándar de tu archivo
        col_serie = 'N.° de serie' if 'N.° de serie' in df.columns else 'N.° de equipo'
        
        df['Fecha_DT'] = pd.to_datetime(df['Última visita'], errors='coerce')
        df = df.dropna(subset=['Fecha_DT', 'Folio', col_serie])

        # =============================
        # SELECTORES DE TIEMPO
        # =============================
        meses_dict = {
            1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio",
            7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"
        }

        col1, col2 = st.sidebar.columns(2)
        mes_eval = col1.selectbox("Mes", list(meses_dict.keys()), format_func=lambda x: meses_dict[x], index=datetime.now().month - 1)
        anio_eval = col2.number_input("Año", value=2026)
        ventana = st.sidebar.slider("Historial de rastreo (meses)", 1, 12, 3)

        # =============================
        # LÓGICA DE FECHAS (TÚNEL DEL TIEMPO)
        # =============================
        fecha_fin_mes = datetime(anio_eval, mes_eval, 1) + relativedelta(months=1) - relativedelta(days=1)
        fecha_inicio_historial = datetime(anio_eval, mes_eval, 1) - relativedelta(months=ventana)

        # Filtramos el rango total (Historial + Mes actual)
        df_rango = df[(df['Fecha_DT'] >= fecha_inicio_historial) & (df['Fecha_DT'] <= fecha_fin_mes)].copy()
        
        # Ordenamos por serie y fecha para que el 'último' sea realmente el más nuevo
        df_rango = df_rango.sort_values([col_serie, 'Fecha_DT'], ascending=True)

        # =============================
        # PROCESAMIENTO DE PENALIZACIONES
        # =============================
        df_rango['Es_Penalizacion'] = 0
        
        for serie, grupo in df_rango.groupby(col_serie):
            if len(grupo) > 1:
                # Obtenemos los índices de todos los folios de esta máquina
                indices = grupo.index.tolist()
                
                # REGLA: El último (indices[-1]) se salva. 
                # Penalizamos del primero hasta el penúltimo (indices[:-1])
                for idx in indices[:-1]:
                    # Solo penalizamos si es CORRECTIVO
                    if "CORRECT" in str(df_rango.loc[idx, 'Categoría']).upper():
                        df_rango.loc[idx, 'Es_Penalizacion'] = 1

        # =============================
        # FILTRADO PARA REPORTES DEL MES
        # =============================
        # Datos del mes para la pestaña de Resumen
        df_mes = df_rango[(df_rango['Fecha_DT'].dt.month == mes_eval) & (df_rango['Fecha_DT'].dt.year == anio_eval)]

        # =============================
        # INTERFAZ (TABS)
        # =============================
        tab1, tab2, tab3 = st.tabs(["📊 Resumen", "⚠️ Penalizaciones", "🔍 Detalle de Auditoría"])

        with tab1:
            st.subheader(f"Productividad - {meses_dict[mes_eval]} {anio_eval}")
            resumen_prod = df_mes.groupby('Técnico').size().reset_index(name='Reportes Totales')
            st.dataframe(resumen_prod.sort_values('Reportes Totales', ascending=False), use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("Conteo de Penalizaciones")
            # Aquí mostramos las penalizaciones que el técnico acumuló (pueden ser sus folios de meses pasados o actuales)
            resumen_penal = df_rango[df_rango['Es_Penalizacion'] == 1].groupby('Técnico').size().reset_index(name='Penalizaciones')
            st.table(resumen_penal.sort_values('Penalizaciones', ascending=False))

        with tab3:
            st.subheader("Evidencia de Folios Penalizados")
            tecnicos_con_falla = sorted(df_rango[df_rango['Es_Penalizacion'] == 1]['Técnico'].unique())
            tecnico_sel = st.selectbox("Revisar técnico:", ["Todos"] + tecnicos_con_falla)

            df_evidencia = df_rango[df_rango['Es_Penalizacion'] == 1][['Folio', col_serie, 'Técnico', 'Última visita', 'Categoría', 'Problema reportado']]
            
            if tecnico_sel != "Todos":
                df_evidencia = df_evidencia[df_evidencia['Técnico'] == tecnico_sel]

            st.dataframe(df_evidencia, use_container_width=True, hide_index=True)

    else:
        st.info("Sube el archivo Excel de servicios para analizar la calidad del equipo.")

if __name__ == "__main__":
    main()
