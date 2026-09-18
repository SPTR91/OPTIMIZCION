import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="Procesador Chattigo ESAN", page_icon="⚙️", layout="wide")

st.title("⚙️ Limpiador de Bases para Chattigo")
st.markdown("Sube tu archivo CRM, filtra y exporta la base lista para enviar mensajes.")

uploaded_file = st.file_uploader("1. Sube tu archivo Excel (.xlsx)", type=['xlsx'])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        
        # Buscar columnas clave ignorando mayúsculas/espacios
        cols_upper = {str(c).upper().strip(): c for c in df.columns}
        
        estado_key = next((k for k in cols_upper.keys() if "ESTADO" in k and "CIVIL" not in k and "ADMISIÓN" not in k), None)
        cel_key = next((k for k in cols_upper.keys() if "CELULAR" in k), None)
        fijo_key = next((k for k in cols_upper.keys() if "FIJO" in k), None)
        otros_key = next((k for k in cols_upper.keys() if "OTROS" in k), None)
        nombre_key = next((k for k in cols_upper.keys() if "NOMBRES" in k or "APELLIDO" in k), None)
        
        if estado_key and (cel_key or fijo_key or otros_key):
            estado_col_real = cols_upper[estado_key]
            
            st.success("✅ Archivo cargado correctamente.")
            
            # Selector de Estados
            estados_unicos = df[estado_col_real].dropna().astype(str).unique().tolist()
            st.markdown("### 2. Selecciona los Estados a procesar")
            estados_seleccionados = st.multiselect("Estados (Ej: Solicitó información, Revisando información):", estados_unicos)
            
            # Selector de Columnas Extras
            st.markdown("### 3. Selecciona las columnas adicionales")
            todas_las_columnas = df.columns.tolist()
            # Sugerencias por defecto si existen
            columnas_defecto = []
            if nombre_key: columnas_defecto.append(cols_upper[nombre_key])
            for k, c in cols_upper.items():
                if "DNI" in k or "CORREO" in k or "PROGRAMA" in k:
                    columnas_defecto.append(c)
                    
            cols_extra = st.multiselect("La columna 'destination' (teléfono) siempre irá primera. ¿Qué más necesitas?", 
                                        todas_las_columnas, 
                                        default=columnas_defecto)
            
            if st.button("Procesar Base de Datos"):
                if not estados_seleccionados:
                    st.warning("⚠️ Debes seleccionar al menos un estado.")
                else:
                    with st.spinner('Procesando y limpiando números...'):
                        # Filtrar base
                        df_filtrado = df[df[estado_col_real].isin(estados_seleccionados)]
                        resultados = []
                        historial = set()
                        
                        cel_col_real = cols_upper.get(cel_key) if cel_key else None
                        fijo_col_real = cols_upper.get(fijo_key) if fijo_key else None
                        otros_col_real = cols_upper.get(otros_key) if otros_key else None
                        
                        for index, row in df_filtrado.iterrows():
                            numeros_crudos = []
                            if cel_col_real: numeros_crudos.append(str(row.get(cel_col_real, '')))
                            if fijo_col_real: numeros_crudos.append(str(row.get(fijo_col_real, '')))
                            if otros_col_real: 
                                otros = str(row.get(otros_col_real, ''))
                                if otros and otros.lower() != 'nan':
                                    # Separar por pipe | o coma
                                    numeros_crudos.extend(re.split(r'[|,]', otros))
                                    
                            nombre_fila = str(row.get(cols_extra[0], index)) if cols_extra else str(index)
                            
                            for num in numeros_crudos:
                                if not num or str(num).lower() == 'nan': continue
                                
                                # Limpieza: solo dígitos
                                limpio = re.sub(r'\D', '', str(num))
                                final = ""
                                
                                # Reglas de ESAN
                                if len(limpio) == 9 and limpio.startswith("9"):
                                    final = "51" + limpio
                                elif len(limpio) == 11 and limpio.startswith("519"):
                                    final = limpio
                                    
                                if final and final != "51999999999":
                                    clave = f"{nombre_fila}_{final}"
                                    if clave not in historial:
                                        historial.add(clave)
                                        
                                        # Armar fila resultado
                                        fila_res = {'destination': final}
                                        for col in cols_extra:
                                            fila_res[col] = row.get(col, '')
                                        resultados.append(fila_res)
                        
                        if resultados:
                            df_final = pd.DataFrame(resultados)
                            
                            st.success(f"✅ Proceso terminado: Se rescataron {len(df_final)} contactos válidos.")
                            st.dataframe(df_final.head(10))
                            
                            # Exportar a Excel
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                df_final.to_excel(writer, index=False, sheet_name='Plantilla Chatigo')
                                workbook = writer.book
                                worksheet = writer.sheets['Plantilla Chatigo']
                                
                                # Formato cabecera ESAN
                                header_format = workbook.add_format({
                                    'bold': True,
                                    'fg_color': '#4431B0',
                                    'font_color': 'white',
                                    'font_name': 'Calibri',
                                    'font_size': 11,
                                    'align': 'center',
                                    'valign': 'vcenter'
                                })
                                dest_format = workbook.add_format({
                                    'bold': True,
                                    'fg_color': '#F17B27',
                                    'font_color': 'white',
                                    'font_name': 'Calibri',
                                    'font_size': 11,
                                    'align': 'center',
                                    'valign': 'vcenter'
                                })
                                
                                for col_num, value in enumerate(df_final.columns.values):
                                    fmt = dest_format if col_num == 0 else header_format
                                    worksheet.write(0, col_num, value, fmt)
                                    worksheet.set_column(col_num, col_num, 20)
                            
                            st.download_button(
                                label="📥 Descargar Plantilla (.xlsx)",
                                data=output.getvalue(),
                                file_name="Base_Procesada_Chattigo.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        else:
                            st.warning("No se encontraron números válidos con esos filtros.")
        else:
            st.error("No se encontraron las columnas clave (ESTADO, CELULAR, TELÉFONO FIJO). Revisa tu archivo.")
    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
