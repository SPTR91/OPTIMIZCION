import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="Constructor Base Chattigo", page_icon="⚙️", layout="wide")

# Diseño corporativo
st.markdown("""
    <style>
    .main {background-color: #F8F9FA;}
    h1 {color: #E3173E; font-family: 'Arial', sans-serif; font-weight: 700;}
    h3 {color: #333333; font-family: 'Arial', sans-serif;}
    .stButton>button {background-color: #E3173E; color: white; border-radius: 5px; border: none; font-weight: bold;}
    .stButton>button:hover {background-color: #AE0800; color: white;}
    </style>
""", unsafe_allow_html=True)

st.title("⚙️ Constructor Dinámico para Chattigo")
st.markdown("Sube tus bases crudas, consolídalas y arma tu plantilla exportable con los campos exactos.")

uploaded_files = st.file_uploader("1. Sube tus archivos Excel (.xlsx)", type=['xlsx'], accept_multiple_files=True)

if uploaded_files:
    try:
        with st.spinner('Consolidando bases de datos...'):
            dfs = [pd.read_excel(file) for file in uploaded_files]
            df = pd.concat(dfs, ignore_index=True)
        
        cols_upper = {str(c).upper().strip(): c for c in df.columns}
        estado_key = next((k for k in cols_upper.keys() if "ESTADO" in k and "CIVIL" not in k and "ADMISIÓN" not in k), None)
        
        if estado_key:
            estado_col_real = cols_upper[estado_key]
            st.success(f"✅ Se consolidaron {len(uploaded_files)} archivo(s) correctamente.")
            
            estados_unicos = df[estado_col_real].dropna().astype(str).unique().tolist()
            st.markdown("### 2. Selecciona los Estados a procesar")
            estados_seleccionados = st.multiselect("Filtra tu base consolidada:", estados_unicos)
            
            st.markdown("### 3. Arma tus columnas")
            opciones_amigables = ["NOMBRE", "DNI", "CORREO"]
            
            cols_extra = st.multiselect(
                "La columna 'destination' irá primero. Selecciona qué más deseas incluir:", 
                opciones_amigables, 
                default=opciones_amigables
            )
            
            if st.button("Procesar y Generar Plantilla"):
                if not estados_seleccionados:
                    st.warning("⚠️ Debes seleccionar al menos un estado.")
                else:
                    with st.spinner('Construyendo base de datos final...'):
                        df_filtrado = df[df[estado_col_real].isin(estados_seleccionados)]
                        resultados = []
                        historial = set()
                        
                        cel_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "CELULAR" in k), None))
                        fijo_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "FIJO" in k), None))
                        otros_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "OTROS" in k), None))
                        
                        nombres_col = cols_upper.get("NOMBRES")
                        paterno_col = cols_upper.get("APELLIDO PATERNO")
                        materno_col = cols_upper.get("APELLIDO MATERNO")
                        dni_col = cols_upper.get(next((k for k in cols_upper.keys() if "DNI" in k), None))
                        correo_col = cols_upper.get(next((k for k in cols_upper.keys() if "CORREO" in k), None))
                        
                        for index, row in df_filtrado.iterrows():
                            # LÓGICA DE CASCADA ESTRICTA (Imprime el primero lleno)
                            val_nombres = str(row.get(nombres_col, '')).strip() if nombres_col else ""
                            val_paterno = str(row.get(paterno_col, '')).strip() if paterno_col else ""
                            val_materno = str(row.get(materno_col, '')).strip() if materno_col else ""
                            
                            val_nombres = "" if val_nombres.lower() == 'nan' else val_nombres
                            val_paterno = "" if val_paterno.lower() == 'nan' else val_paterno
                            val_materno = "" if val_materno.lower() == 'nan' else val_materno
                            
                            if val_nombres:
                                nombre_final = val_nombres
                            elif val_paterno:
                                nombre_final = val_paterno
                            elif val_materno:
                                nombre_final = val_materno
                            else:
                                nombre_final = f"Contacto_{index}"

                            numeros_crudos = []
                            if cel_col_real: numeros_crudos.append(str(row.get(cel_col_real, '')))
                            if fijo_col_real: numeros_crudos.append(str(row.get(fijo_col_real, '')))
                            if otros_col_real: 
                                otros = str(row.get(otros_col_real, ''))
                                if otros and otros.lower() != 'nan':
                                    numeros_crudos.extend(re.split(r'[|,]', otros))
                                    
                            for num in numeros_crudos:
                                if not num or str(num).lower() == 'nan': continue
                                
                                limpio = re.sub(r'\D', '', str(num))
                                final = ""
                                
                                if len(limpio) == 9 and limpio.startswith("9"):
                                    final = "51" + limpio
                                elif len(limpio) == 11 and limpio.startswith("519"):
                                    final = limpio
                                    
                                if final and final != "51999999999":
                                    clave = f"{nombre_final}_{final}"
                                    if clave not in historial:
                                        historial.add(clave)
                                        
                                        fila_res = {'destination': final}
                                        
                                        if "NOMBRE" in cols_extra:
                                            fila_res["NOMBRE"] = nombre_final
                                        if "DNI" in cols_extra:
                                            val_dni = str(row.get(dni_col, '')) if dni_col else ""
                                            fila_res["DNI"] = "" if val_dni.lower() == 'nan' else val_dni
                                        if "CORREO" in cols_extra:
                                            val_correo = str(row.get(correo_col, '')) if correo_col else ""
                                            fila_res["CORREO"] = "" if val_correo.lower() == 'nan' else val_correo
                                            
                                        resultados.append(fila_res)
                        
                        if resultados:
                            df_final = pd.DataFrame(resultados)
                            st.success(f"✅ Se extrajeron {len(df_final)} contactos listos.")
                            st.dataframe(df_final.head())
                            
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                df_final.to_excel(writer, index=False, sheet_name='Chattigo')
                                workbook = writer.book
                                worksheet = writer.sheets['Chattigo']
                                
                                format_dest = workbook.add_format({'bold': True, 'fg_color': '#F17B27', 'font_color': 'white', 'font_name': 'Calibri', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
                                format_headers = workbook.add_format({'bold': True, 'fg_color': '#1C2D5A', 'font_color': 'white', 'font_name': 'Calibri', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
                                format_data = workbook.add_format({'font_name': 'Calibri', 'font_size': 11, 'valign': 'vcenter'})
                                
                                for col_num, value in enumerate(df_final.columns.values):
                                    fmt = format_dest if col_num == 0 else format_headers
                                    worksheet.write(0, col_num, value, fmt)
                                    max_len = max(df_final.iloc[:, col_num].astype(str).map(len).max(), len(str(value))) + 5
                                    worksheet.set_column(col_num, col_num, max_len, format_data)
                                    
                                worksheet.freeze_panes(1, 0)
                            
                            st.download_button("📥 Descargar Archivo Consolidado (.xlsx)", data=output.getvalue(), file_name="Plantilla_Chattigo_Limpia.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                        else:
                            st.warning("⚠️ Ningún número superó los filtros.")
        else:
            st.error("❌ No se encontró la columna 'ESTADO'.")
    except Exception as e:
        st.error(f"Error: {e}")
