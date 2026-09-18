import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="Constructor Base Chattigo", page_icon="⚙️", layout="wide")

st.title("⚙️ Constructor Dinámico para Chattigo")
st.markdown("Sube tu base cruda, filtra por estados y arma tu plantilla a medida.")

uploaded_file = st.file_uploader("1. Sube tu archivo Excel (.xlsx)", type=['xlsx'])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        
        cols_upper = {str(c).upper().strip(): c for c in df.columns}
        estado_key = next((k for k in cols_upper.keys() if "ESTADO" in k and "CIVIL" not in k and "ADMISIÓN" not in k), None)
        
        if estado_key:
            estado_col_real = cols_upper[estado_key]
            st.success("✅ Archivo cargado correctamente.")
            
            # Selector de Estados
            estados_unicos = df[estado_col_real].dropna().astype(str).unique().tolist()
            st.markdown("### 2. Selecciona los Estados a procesar")
            estados_seleccionados = st.multiselect("Filtra tu base:", estados_unicos)
            
            # Selector de Columnas
            st.markdown("### 3. Arma tus columnas")
            todas_las_columnas = df.columns.tolist()
            
            # Pre-selección inteligente de columnas comunes
            columnas_defecto = []
            for k, c in cols_upper.items():
                if any(palabra in k for palabra in ["NOMBRE", "APELLIDO", "DNI", "CORREO", "PROGRAMA"]):
                    columnas_defecto.append(c)
                    
            cols_extra = st.multiselect(
                "La columna 'destination' (teléfono validado) siempre será la primera. Selecciona qué más deseas incluir:", 
                todas_las_columnas, 
                default=columnas_defecto
            )
            
            if st.button("Procesar y Generar Plantilla"):
                if not estados_seleccionados:
                    st.warning("⚠️ Debes seleccionar al menos un estado.")
                elif not cols_extra:
                    st.warning("⚠️ Debes seleccionar al menos una columna adicional.")
                else:
                    with st.spinner('Construyendo base de datos...'):
                        df_filtrado = df[df[estado_col_real].isin(estados_seleccionados)]
                        resultados = []
                        historial = set()
                        
                        cel_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "CELULAR" in k), None))
                        fijo_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "FIJO" in k), None))
                        otros_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "OTROS" in k), None))
                        nombre_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "NOMBRE" in k or "APELLIDO" in k), None))
                        
                        for index, row in df_filtrado.iterrows():
                            numeros_crudos = []
                            if cel_col_real: numeros_crudos.append(str(row.get(cel_col_real, '')))
                            if fijo_col_real: numeros_crudos.append(str(row.get(fijo_col_real, '')))
                            if otros_col_real: 
                                otros = str(row.get(otros_col_real, ''))
                                if otros and otros.lower() != 'nan':
                                    numeros_crudos.extend(re.split(r'[|,]', otros))
                                    
                            # Llave única para evitar spam al mismo usuario
                            identificador_persona = str(row.get(nombre_col_real, index)) if nombre_col_real else str(index)
                            
                            for num in numeros_crudos:
                                if not num or str(num).lower() == 'nan': continue
                                
                                limpio = re.sub(r'\D', '', str(num))
                                final = ""
                                
                                if len(limpio) == 9 and limpio.startswith("9"):
                                    final = "51" + limpio
                                elif len(limpio) == 11 and limpio.startswith("519"):
                                    final = limpio
                                    
                                if final and final != "51999999999":
                                    clave = f"{identificador_persona}_{final}"
                                    if clave not in historial:
                                        historial.add(clave)
                                        
                                        # destination va obligatoriamente al inicio
                                        fila_res = {'destination': final}
                                        for col in cols_extra:
                                            fila_res[col] = row.get(col, '')
                                        resultados.append(fila_res)
                        
                        if resultados:
                            df_final = pd.DataFrame(resultados)
                            st.success(f"✅ Se validaron y extrajeron {len(df_final)} contactos listos para envío.")
                            st.dataframe(df_final.head(10))
                            
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                df_final.to_excel(writer, index=False, sheet_name='Chattigo')
                                workbook = writer.book
                                worksheet = writer.sheets['Chattigo']
                                
                                # Formato exacto requerido por la plantilla original
                                format_dest = workbook.add_format({
                                    'bold': True, 'fg_color': '#F17B27', 'font_color': 'white', 
                                    'font_name': 'Calibri', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'
                                })
                                format_headers = workbook.add_format({
                                    'bold': True, 'fg_color': '#4431B0', 'font_color': 'white', 
                                    'font_name': 'Calibri', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'
                                })
                                format_data = workbook.add_format({
                                    'font_name': 'Calibri', 'font_size': 11, 'valign': 'vcenter'
                                })
                                
                                for col_num, value in enumerate(df_final.columns.values):
                                    fmt = format_dest if col_num == 0 else format_headers
                                    worksheet.write(0, col_num, value, fmt)
                                    
                                    # Ajuste automático de ancho de columna con respiro extra
                                    max_len = max(df_final.iloc[:, col_num].astype(str).map(len).max(), len(str(value))) + 5
                                    worksheet.set_column(col_num, col_num, max_len, format_data)
                                    
                                worksheet.freeze_panes(1, 0)
                            
                            st.download_button(
                                label="📥 Descargar Archivo (.xlsx)",
                                data=output.getvalue(),
                                file_name="Plantilla_Chattigo_Dinamica.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        else:
                            st.warning("⚠️ Ningún número superó los filtros de validación telefónica.")
        else:
            st.error("❌ No se encontró la columna 'ESTADO'. Revisa la estructura de tu archivo.")
    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
