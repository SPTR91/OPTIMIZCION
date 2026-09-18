import streamlit as st
import pandas as pd
import re
import io

# 1. CONFIGURACIÓN DE PÁGINA Y DISEÑO TIPO "APPLE / ESAN"
st.set_page_config(page_title="Constructor Base Chattigo", page_icon="⚙️", layout="wide")

# Inyectamos CSS para un diseño limpio, blanco, gris y rojo corporativo
st.markdown("""
    <style>
    /* Fondo general súper limpio y blanco/gris muy claro */
    .stApp {
        background-color: #FAFAFA;
        color: #333333;
        font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* Títulos sobrios y elegantes */
    h1, h2, h3 {
        color: #333333;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    h1 {
        font-size: 2.2rem;
        margin-bottom: 0.5rem;
    }
    
    /* Acentos rojos corporativos (ESAN) */
    .highlight-red {
        color: #E3173E;
    }
    
    /* Estilo de botones: Rojos con bordes redondeados suaves */
    .stButton>button {
        background-color: #E3173E;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 2px 4px rgba(227, 23, 62, 0.2);
    }
    
    .stButton>button:hover {
        background-color: #AE0800; /* Rojo sombra ESAN */
        box-shadow: 0 4px 8px rgba(174, 8, 0, 0.3);
        transform: translateY(-1px);
    }
    
    /* Estilo de los selectores múltiples (Chips) */
    .stMultiSelect div[data-baseweb="select"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .stMultiSelect div[data-baseweb="tag"] {
        background-color: #F5F5F5;
        color: #333333;
        border: 1px solid #DDDDDD;
        border-radius: 6px;
    }
    
    /* Alertas con estilo más suave y bordes redondeados */
    .stAlert {
        border-radius: 8px;
        border: none;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Contenedor de subida de archivos */
    [data-testid="stFileUploadDropzone"] {
        background-color: #FFFFFF;
        border: 2px dashed #CCCCCC;
        border-radius: 12px;
        padding: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# 2. INTERFAZ DE USUARIO
st.markdown("<h1>⚙️ Constructor Dinámico <span class='highlight-red'>Chattigo</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #696A6D; font-size: 1.1rem; margin-bottom: 2rem;'>Consolida tus bases, filtra por estados y genera tu plantilla lista para envío.</p>", unsafe_allow_html=True)

st.markdown("### 1. Carga de Archivos")
uploaded_files = st.file_uploader("Sube tus archivos Excel (.xlsx). Puedes arrastrar múltiples archivos a la vez.", type=['xlsx'], accept_multiple_files=True)

if uploaded_files:
    try:
        with st.spinner('Consolidando datos...'):
            dfs = [pd.read_excel(file) for file in uploaded_files]
            df = pd.concat(dfs, ignore_index=True)
        
        cols_upper = {str(c).upper().strip(): c for c in df.columns}
        estado_key = next((k for k in cols_upper.keys() if "ESTADO" in k and "CIVIL" not in k and "ADMISIÓN" not in k), None)
        
        if estado_key:
            estado_col_real = cols_upper[estado_key]
            st.success(f"✅ Se consolidaron {len(uploaded_files)} archivo(s) correctamente con un total de {len(df)} registros.")
            
            st.markdown("<hr style='border: none; border-top: 1px solid #EAEAEA; margin: 2rem 0;'>", unsafe_allow_html=True)
            
            # Selector de Estados
            estados_unicos = df[estado_col_real].dropna().astype(str).unique().tolist()
            st.markdown("### 2. Filtro de Estados")
            estados_seleccionados = st.multiselect("Selecciona los estados a procesar:", estados_unicos)
            
            st.markdown("<hr style='border: none; border-top: 1px solid #EAEAEA; margin: 2rem 0;'>", unsafe_allow_html=True)
            
            # Selector de Columnas (Minimalista)
            st.markdown("### 3. Estructura de Salida")
            opciones_amigables = ["NOMBRE", "DNI", "CORREO"]
            
            cols_extra = st.multiselect(
                "La columna 'destination' (teléfono) irá siempre al inicio. ¿Qué más deseas incluir?", 
                opciones_amigables, 
                default=["NOMBRE"]
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Procesar y Generar Plantilla"):
                if not estados_seleccionados:
                    st.warning("⚠️ Debes seleccionar al menos un estado para procesar.")
                else:
                    with st.spinner('Construyendo base de datos final...'):
                        df_filtrado = df[df[estado_col_real].isin(estados_seleccionados)]
                        resultados = []
                        historial = set()
                        
                        # Mapeo de columnas telefónicas
                        cel_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "CELULAR" in k), None))
                        fijo_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "FIJO" in k), None))
                        otros_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "OTROS" in k), None))
                        
                        # Mapeo de datos personales para la Cascada
                        nombres_col = cols_upper.get("NOMBRES")
                        paterno_col = cols_upper.get("APELLIDO PATERNO")
                        materno_col = cols_upper.get("APELLIDO MATERNO")
                        dni_col = cols_upper.get(next((k for k in cols_upper.keys() if "DNI" in k), None))
                        correo_col = cols_upper.get(next((k for k in cols_upper.keys() if "CORREO" in k), None))
                        
                        for index, row in df_filtrado.iterrows():
                            
                            # 3. LÓGICA DE CASCADA (Nombre + Paterno + Materno)
                            val_nombres = str(row.get(nombres_col, '')).strip() if nombres_col else ""
                            val_paterno = str(row.get(paterno_col, '')).strip() if paterno_col else ""
                            val_materno = str(row.get(materno_col, '')).strip() if materno_col else ""
                            
                            val_nombres = "" if val_nombres.lower() == 'nan' else val_nombres
                            val_paterno = "" if val_paterno.lower() == 'nan' else val_paterno
                            val_materno = "" if val_materno.lower() == 'nan' else val_materno
                            
                            # Se suma Paterno o Materno si existen, ignorando vacíos
                            partes_nombre = [p for p in [val_nombres, val_paterno, val_materno] if p]
                            nombre_final = " ".join(partes_nombre)
                            
                            if not nombre_final:
                                nombre_final = f"Contacto_{index}"

                            # Extracción y limpieza de teléfonos
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
                                        
                                        # Estructurar fila según selección del usuario
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
                            st.success(f"✅ Proceso completado. Se extrajeron {len(df_final)} contactos válidos.")
                            st.dataframe(df_final.head(), use_container_width=True)
                            
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                df_final.to_excel(writer, index=False, sheet_name='Chattigo')
                                workbook = writer.book
                                worksheet = writer.sheets['Chattigo']
                                
                                # Formato Institucional ESAN para la salida
                                format_dest = workbook.add_format({'bold': True, 'fg_color': '#E3173E', 'font_color': 'white', 'font_name': 'Arial', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
                                format_headers = workbook.add_format({'bold': True, 'fg_color': '#333333', 'font_color': 'white', 'font_name': 'Arial', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
                                format_data = workbook.add_format({'font_name': 'Arial', 'font_size': 11, 'valign': 'vcenter'})
                                
                                for col_num, value in enumerate(df_final.columns.values):
                                    fmt = format_dest if col_num == 0 else format_headers
                                    worksheet.write(0, col_num, value, fmt)
                                    max_len = max(df_final.iloc[:, col_num].astype(str).map(len).max(), len(str(value))) + 5
                                    worksheet.set_column(col_num, col_num, max_len, format_data)
                                    
                                worksheet.freeze_panes(1, 0)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            st.download_button(
                                label="📥 Descargar Archivo Excel (.xlsx)", 
                                data=output.getvalue(), 
                                file_name="Plantilla_Chattigo_Limpia.xlsx", 
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        else:
                            st.warning("⚠️ Ningún número superó los filtros telefónicos.")
        else:
            st.error("❌ No se encontró la columna 'ESTADO'. Revisa la estructura de los archivos subidos.")
    except Exception as e:
        st.error(f"Ocurrió un error al procesar: {e}")
