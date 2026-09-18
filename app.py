import streamlit as st
import pandas as pd
import re
import io

# 1. CONFIGURACIÓN DE PÁGINA (ESTILO MINIMALISTA)
st.set_page_config(page_title="Constructor Chattigo", page_icon="⚙️", layout="wide")

# 2. INYECCIÓN CSS: ESTILO APPLE + ESAN BRANDING
st.markdown("""
    <style>
    /* Tipografía y fondo blanco inmaculado */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #FFFFFF !important;
        color: #4E5054 !important;
    }
    
    /* Títulos limpios y jerárquicos */
    h1 {
        font-weight: 700 !important;
        color: #111111 !important;
        letter-spacing: -1px;
    }
    
    h3 {
        font-weight: 600 !important;
        color: #333333 !important;
        font-size: 1.2rem !important;
        margin-top: 1.5rem !important;
    }

    /* Acento Rojo ESAN */
    .esan-red {
        color: #E3173E;
    }
    
    /* Botones estilo Apple (Bordes redondeados, sombra suave) */
    .stButton>button {
        background-color: #E3173E !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        box-shadow: 0 4px 6px rgba(227, 23, 62, 0.15) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton>button:hover {
        background-color: #AE0800 !important;
        box-shadow: 0 6px 10px rgba(174, 8, 0, 0.25) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Cajas de subida de archivos limpias */
    [data-testid="stFileUploadDropzone"] {
        background-color: #F8F9FA !important;
        border: 2px dashed #E0E0E0 !important;
        border-radius: 16px !important;
        transition: border 0.3s ease !important;
    }
    
    [data-testid="stFileUploadDropzone"]:hover {
        border: 2px dashed #E3173E !important;
    }
    
    /* Selectores múltiples (Chips) redondos y limpios */
    .stMultiSelect div[data-baseweb="select"] {
        border-radius: 12px !important;
        border: 1px solid #E0E0E0 !important;
        background-color: #F8F9FA !important;
    }
    
    .stMultiSelect div[data-baseweb="tag"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E3173E !important;
        color: #E3173E !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    /* Alertas suaves */
    .stAlert {
        border-radius: 12px !important;
        border: none !important;
    }
    
    /* Checkbox estilo limpio */
    .stCheckbox label span {
        color: #333333 !important;
        font-weight: 500 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. INTERFAZ DE USUARIO
st.markdown("<h1>⚙️ Constructor <span class='esan-red'>Chattigo</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 1.1rem; color: #696A6D; margin-bottom: 2rem;'>Sube tus bases crudas, consolídalas y genera tu plantilla impecable.</p>", unsafe_allow_html=True)

uploaded_files = st.file_uploader("Arrastra tus archivos Excel (.xlsx) aquí", type=['xlsx'], accept_multiple_files=True)

if uploaded_files:
    try:
        with st.spinner('Consolidando datos de forma segura...'):
            dfs = [pd.read_excel(file) for file in uploaded_files]
            df = pd.concat(dfs, ignore_index=True)
        
        cols_upper = {str(c).upper().strip(): c for c in df.columns}
        estado_key = next((k for k in cols_upper.keys() if "ESTADO" in k and "CIVIL" not in k and "ADMISIÓN" not in k), None)
        
        if estado_key:
            estado_col_real = cols_upper[estado_key]
            st.success(f"✅ Se consolidaron {len(uploaded_files)} archivo(s) correctamente con un total de {len(df)} registros.")
            
            st.markdown("### 2. Selecciona los Estados a procesar")
            estados_unicos = df[estado_col_real].dropna().astype(str).unique().tolist()
            estados_seleccionados = st.multiselect("Filtra tu base consolidada:", estados_unicos)
            
            st.markdown("### 3. Estructura de Salida")
            st.markdown("<p style='font-size: 0.9rem; color: #696A6D; margin-bottom: 1rem;'>La columna 'destination' (teléfono) irá siempre al inicio. Selecciona qué más deseas incluir:</p>", unsafe_allow_html=True)
            
            # Cambiado a Checkboxes
            col1, col2, col3 = st.columns(3)
            with col1:
                incluir_nombre = st.checkbox("NOMBRE", value=True)
            with col2:
                incluir_dni = st.checkbox("DNI", value=False)
            with col3:
                incluir_correo = st.checkbox("CORREO", value=False)
            
            cols_extra = []
            if incluir_nombre: cols_extra.append("NOMBRE")
            if incluir_dni: cols_extra.append("DNI")
            if incluir_correo: cols_extra.append("CORREO")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Procesar y Generar Plantilla"):
                if not estados_seleccionados:
                    st.warning("⚠️ Selecciona al menos un estado para procesar.")
                else:
                    with st.spinner('Procesando lógica de cascada y validando números...'):
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
                            st.success(f"✅ Proceso completado con éxito. Se extrajeron {len(df_final)} contactos válidos.")
                            st.dataframe(df_final.head(), use_container_width=True)
                            
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                df_final.to_excel(writer, index=False, sheet_name='Chattigo')
                                workbook = writer.book
                                worksheet = writer.sheets['Chattigo']
                                
                                # Formato Excel Corporativo ESAN
                                format_dest = workbook.add_format({'bold': True, 'fg_color': '#E3173E', 'font_color': 'white', 'font_name': 'Inter', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
                                format_headers = workbook.add_format({'bold': True, 'fg_color': '#696A6D', 'font_color': 'white', 'font_name': 'Inter', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
                                format_data = workbook.add_format({'font_name': 'Inter', 'font_size': 11, 'valign': 'vcenter'})
                                
                                for col_num, value in enumerate(df_final.columns.values):
                                    fmt = format_dest if col_num == 0 else format_headers
                                    worksheet.write(0, col_num, value, fmt)
                                    max_len = max(df_final.iloc[:, col_num].astype(str).map(len).max(), len(str(value))) + 5
                                    worksheet.set_column(col_num, col_num, max_len, format_data)
                                    
                                worksheet.freeze_panes(1, 0)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.download_button(
                                label="📥 Descargar Plantilla (.xlsx)", 
                                data=output.getvalue(), 
                                file_name="Plantilla_Chattigo_ESAN.xlsx", 
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        else:
                            st.warning("⚠️ Ningún número superó los filtros telefónicos.")
        else:
            st.error("❌ No se encontró la columna 'ESTADO'. Revisa la estructura de los archivos subidos.")
    except Exception as e:
        st.error(f"Ocurrió un error al procesar: {e}")
