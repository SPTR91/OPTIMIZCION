import streamlit as st
import os
import pandas as pd
import re
import io
import csv
import datetime
import requests
from supabase import create_client, Client
import extra_streamlit_components as stx

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(page_title="Filtro Bases Chattigo", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #FFFFFF !important;
        color: #4E5054 !important;
    }
    h1 {font-weight: 700 !important; color: #111111 !important; letter-spacing: -1px;}
    h3 {font-weight: 600 !important; color: #333333 !important; font-size: 1.2rem !important; margin-top: 1.5rem !important;}
    .esan-red {color: #E3173E;}
    
    .stButton>button {
        background-color: #E3173E !important; color: #FFFFFF !important; border-radius: 12px !important;
        border: none !important; padding: 0.6rem 1.5rem !important; font-weight: 600 !important;
        box-shadow: 0 4px 6px rgba(227, 23, 62, 0.15) !important; transition: all 0.3s ease !important;
    }
    .stButton>button:hover {background-color: #AE0800 !important; transform: translateY(-1px) !important;}
    
    [data-testid="stFileUploadDropzone"] {background-color: #F8F9FA !important; border: 2px dashed #E0E0E0 !important; border-radius: 16px !important;}
    .stAlert {border-radius: 12px !important; border: none !important;}
    .stCheckbox label span {color: #333333 !important; font-weight: 500 !important;}
    .stTextInput input {border-radius: 10px !important; border: 1px solid #E0E0E0 !important; background-color: #F8F9FA !important; color: #333333 !important;}
    div[data-testid="stMetric"] {background-color: #F8F9FA; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN A SUPABASE Y COOKIES DE SESIÓN
# ==========================================
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyGm-pDC2avah3JdRr-df856xyglaDr3aD4u1dNW3aB18JwhQpEp-5-Om-pMSBV5Gga/exec"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kqalrigciifqvirejgoe.supabase.co").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_E6g6X8EpkewpMvOiFnml5A_9yNr9GBC").strip()
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()

@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource
def init_admin_supabase() -> Client:
    if SUPABASE_SERVICE_KEY:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()
admin_supabase = init_admin_supabase()

cookie_manager = stx.CookieManager(key="chattigo_cookies")

if 'user' not in st.session_state:
    st.session_state.user = None
if 'rol' not in st.session_state:
    st.session_state.rol = None

# Restaurar sesión automáticamente desde cookies si existe
if not st.session_state.user:
    saved_uid = cookie_manager.get("chattigo_uid")
    if saved_uid:
        try:
            perfil = supabase.table("perfiles").select("*").eq("id", saved_uid).execute()
            if perfil.data:
                class DummyUser:
                    def __init__(self, uid, email):
                        self.id = uid
                        self.email = email
                st.session_state.user = DummyUser(perfil.data[0]['id'], perfil.data[0]['email'])
                st.session_state.rol = perfil.data[0]['rol']
        except Exception:
            pass

# ==========================================
# 3. PANTALLA DE ACCESO (LOGIN / REGISTRO)
# ==========================================
if not st.session_state.user:
    st.markdown("<h1>Filtro Bases <span class='esan-red'>Chattigo</span></h1>", unsafe_allow_html=True)
    tab_login, tab_register = st.tabs(["Iniciar Sesión", "Registrarse"])
    
    with tab_login:
        with st.form("login_form"):
            email_login = st.text_input("Correo Electrónico")
            pass_login = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email_login.strip(), "password": pass_login})
                    st.session_state.user = res.user
                    perfil = supabase.table("perfiles").select("rol").eq("id", res.user.id).execute()
                    st.session_state.rol = perfil.data[0]['rol'] if perfil.data else 'asesor'
                    
                    # Guardar sesión por 30 días en el navegador
                    exp_date = datetime.datetime.now() + datetime.timedelta(days=30)
                    cookie_manager.set("chattigo_uid", res.user.id, expires_at=exp_date)
                    st.rerun()
                except Exception:
                    st.error("Correo o contraseña incorrectos.")
                    
    with tab_register:
        with st.form("register_form"):
            reg_nombre = st.text_input("Nombre")
            reg_apellido = st.text_input("Apellido")
            reg_email = st.text_input("Correo Electrónico")
            reg_pass = st.text_input("Contraseña (Mínimo 6 caracteres)", type="password")
            reg_pass_conf = st.text_input("Confirmar Contraseña", type="password")
            
            if st.form_submit_button("Crear Cuenta"):
                if reg_pass != reg_pass_conf:
                    st.error("Las contraseñas no coinciden.")
                elif len(reg_pass) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres.")
                elif not reg_nombre or not reg_apellido or not reg_email:
                    st.error("Todos los campos son obligatorios.")
                else:
                    try:
                        supabase.auth.sign_up({
                            "email": reg_email.strip(), 
                            "password": reg_pass,
                            "options": {"data": {"nombre": reg_nombre.strip(), "apellido": reg_apellido.strip()}}
                        })
                        st.success("Cuenta creada correctamente. Ya puedes ingresar en la pestaña 'Iniciar Sesión'.")
                    except Exception as e:
                        st.error(f"No se pudo crear la cuenta: {e}")
    st.stop()

# ==========================================
# 4. CABECERA PRINCIPAL Y NAVEGACIÓN
# ==========================================
def cerrar_sesion():
    try:
        cookie_manager.delete("chattigo_uid")
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.user = None
    st.session_state.rol = None
    st.rerun()

col_head1, col_head2 = st.columns([8, 2])
with col_head1:
    st.markdown("<h1>Filtro Bases <span class='esan-red'>Chattigo</span></h1>", unsafe_allow_html=True)
with col_head2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Cerrar Sesión", use_container_width=True):
        cerrar_sesion()

if st.session_state.rol == 'admin':
    tabs = st.tabs(["Filtro Operativo", "Mi Historial", "Impacto y Ranking", "Gestión de Usuarios"])
else:
    tabs = st.tabs(["Filtro Operativo", "Mi Historial"])

def guardar_historial_bd(user_id, nombre_archivo, categoria, filas, testigo):
    try:
        supabase.table("historial_procesamiento").insert({
            "user_id": user_id,
            "nombre_archivo": nombre_archivo,
            "categoria": categoria,
            "filas_procesadas": filas,
            "uso_testigo": testigo
        }).execute()
    except Exception:
        pass

# ==========================================
# PESTAÑA 1: FILTRO OPERATIVO
# ==========================================
with tabs[0]:
    def obtener_ip_usuario():
        try:
            headers = st.context.headers
            if headers:
                ip = headers.get("X-Forwarded-For") or headers.get("X-Real-Ip")
                if ip: return ip.split(",")[0].strip()
        except Exception:
            pass
        return "IP_Oculta"

    def registrar_kpi(categoria, filas_procesadas, uso_testigo):
        if not WEBHOOK_URL or "PEGA_AQUI" in WEBHOOK_URL: return
        try:
            payload = {
                "ip": obtener_ip_usuario(),
                "categoria": categoria,
                "filas": filas_procesadas,
                "testigo": "Sí" if uso_testigo else "No"
            }
            requests.post(WEBHOOK_URL, json=payload, timeout=3)
        except Exception:
            pass 

    def limpiar_numero_testigo(num_str):
        if not num_str: return ""
        limpio = re.sub(r'\D', '', str(num_str))
        if len(limpio) == 9 and limpio.startswith("9"): return "51" + limpio
        elif len(limpio) == 11 and limpio.startswith("519"): return limpio
        return ""

    categoria = st.radio("Selecciona el tipo de base a procesar:", ["Convocatorias", "Segmentos"], horizontal=True)
    st.markdown("<p style='font-size: 1.1rem; color: #696A6D; margin-bottom: 2rem;'>Sube tus bases y genera tu plantilla!</p>", unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Arrastra tus archivos Excel o CSV aquí", type=['xlsx', 'csv'], accept_multiple_files=True)

    if uploaded_files:
        try:
            nombres_archivos = ", ".join([f.name for f in uploaded_files])
            with st.spinner('Consolidando datos de forma segura...'):
                dfs = []
                for file in uploaded_files:
                    if file.name.endswith('.csv'):
                        df_temp = pd.read_csv(file, encoding='utf-8', on_bad_lines='skip', dtype=str)
                        
                        # Blindaje para CSVs encapsulados en una sola columna entre comillas
                        if len(df_temp.columns) == 1 and (',' in str(df_temp.columns[0]) or ';' in str(df_temp.columns[0])):
                            file.seek(0)
                            sep_char = ';' if ';' in str(df_temp.columns[0]) and ',' not in str(df_temp.columns[0]) else ','
                            df_temp = pd.read_csv(file, sep=sep_char, encoding='utf-8', on_bad_lines='skip', dtype=str, quoting=csv.QUOTE_NONE)
                            df_temp.columns = [str(c).strip().strip('"').strip("'") for c in df_temp.columns]
                            df_temp = df_temp.apply(lambda col: col.map(lambda x: str(x).strip().strip('"').strip("'") if pd.notna(x) else x))
                            
                        dfs.append(df_temp)
                    else:
                        dfs.append(pd.read_excel(file, dtype=str))
                df = pd.concat(dfs, ignore_index=True)
                
            cols_upper = {str(c).upper().strip(): c for c in df.columns}
            
            # LÓGICA 1: CONVOCATORIAS
            if categoria == "Convocatorias":
                estado_key = next((k for k in cols_upper.keys() if "ESTADO" in k and "CIVIL" not in k and "ADMISIÓN" not in k), None)
                
                if estado_key:
                    estado_col_real = cols_upper[estado_key]
                    st.success(f"Se consolidaron {len(uploaded_files)} archivo(s) con un total de {len(df)} registros.")
                    
                    st.markdown("### 2. Filtro de Estados")
                    estados_unicos = sorted(df[estado_col_real].dropna().astype(str).unique().tolist())
                    estados_seleccionados = []
                    
                    cols_est = st.columns(3)
                    for i, estado in enumerate(estados_unicos):
                        with cols_est[i % 3]:
                            if st.checkbox(estado, key=f"est_{i}"):
                                estados_seleccionados.append(estado)
                    
                    st.markdown("### 3. Estructura de Salida y Control")
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        incluir_nombre = st.checkbox("Incluir columna NOMBRE", value=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    usar_testigo = st.checkbox("Añadir mi número")
                    
                    num_asesor_input = ""
                    nombre_asesor_input = ""
                    
                    if usar_testigo:
                        col_t1, col_t2 = st.columns(2)
                        with col_t1:
                            num_asesor_input = st.text_input("Número (Requerido):", placeholder="Ej: 987654321")
                        with col_t2:
                            nombre_asesor_input = st.text_input("Nombre (Opcional):", placeholder="Ej: Manuel")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if st.button("Procesar y Generar Plantilla"):
                        if not estados_seleccionados:
                            st.warning("Selecciona al menos un estado para procesar.")
                        else:
                            with st.spinner('Procesando...'):
                                df_filtrado = df[df[estado_col_real].isin(estados_seleccionados)]
                                resultados = []
                                historial = set()
                                
                                num_testigo = ""
                                if usar_testigo:
                                    num_testigo = limpiar_numero_testigo(num_asesor_input)
                                    if num_asesor_input and not num_testigo:
                                        st.warning("El número ingresado no es válido. Se procesará sin él.")
                                    elif num_testigo:
                                        historial.add(f"ASESOR_{num_testigo}")
                                        fila_testigo = {'destination': num_testigo}
                                        if incluir_nombre:
                                            fila_testigo['NOMBRE'] = nombre_asesor_input.strip() if nombre_asesor_input.strip() else "Estimado(a)"
                                        resultados.append(fila_testigo)

                                cel_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "CELULAR" in k), None))
                                fijo_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "FIJO" in k), None))
                                otros_col_real = cols_upper.get(next((k for k in cols_upper.keys() if "OTROS" in k), None))
                                nombres_col = cols_upper.get("NOMBRES")
                                paterno_col = cols_upper.get("APELLIDO PATERNO")
                                materno_col = cols_upper.get("APELLIDO MATERNO")
                                
                                for index, row in df_filtrado.iterrows():
                                    val_nombres = str(row.get(nombres_col, '')).strip() if nombres_col else ""
                                    val_paterno = str(row.get(paterno_col, '')).strip() if paterno_col else ""
                                    val_materno = str(row.get(materno_col, '')).strip() if materno_col else ""
                                    
                                    val_nombres = "" if val_nombres.lower() == 'nan' else val_nombres
                                    val_paterno = "" if val_paterno.lower() == 'nan' else val_paterno
                                    val_materno = "" if val_materno.lower() == 'nan' else val_materno
                                    
                                    if val_nombres: nombre_final = val_nombres
                                    elif val_paterno: nombre_final = val_paterno
                                    elif val_materno: nombre_final = val_materno
                                    else: nombre_final = "Estimado(a)"

                                    numeros_crudos = []
                                    if cel_col_real: numeros_crudos.append(str(row.get(cel_col_real, '')))
                                    if fijo_col_real: numeros_crudos.append(str(row.get(fijo_col_real, '')))
                                    if otros_col_real: 
                                        otros = str(row.get(otros_col_real, ''))
                                        if otros and otros.lower() != 'nan':
                                            numeros_crudos.extend(re.split(r'[|,]', otros))
                                            
                                    for num in numeros_crudos:
                                        if not num or str(num).lower() == 'nan': continue
                                        if num.endswith('.0'): num = num[:-2]
                                        limpio = re.sub(r'\D', '', str(num))
                                        final = ""
                                        if len(limpio) == 9 and limpio.startswith("9"): final = "51" + limpio
                                        elif len(limpio) == 11 and limpio.startswith("519"): final = limpio
                                            
                                        if final and final not in ["51999999999", "51987654321"]:
                                            clave = f"{nombre_final}_{final}"
                                            if clave not in historial and f"ASESOR_{final}" not in historial:
                                                historial.add(clave)
                                                fila_res = {'destination': final}
                                                if incluir_nombre: fila_res["NOMBRE"] = nombre_final
                                                resultados.append(fila_res)
                                
                                if resultados:
                                    df_final = pd.DataFrame(resultados)
                                    registrar_kpi("Convocatorias", len(df_final), bool(num_testigo))
                                    guardar_historial_bd(st.session_state.user.id, nombres_archivos, "Convocatorias", len(df_final), bool(num_testigo))
                                    st.success(f"Proceso completado. Se extrajeron {len(df_final)} contactos válidos.")
                                    
                                    output = io.BytesIO()
                                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                        df_final.to_excel(writer, index=False, sheet_name='Chattigo')
                                        workbook = writer.book
                                        worksheet = writer.sheets['Chattigo']
                                        format_dest = workbook.add_format({'bold': True, 'fg_color': '#F17B27', 'font_color': 'white', 'font_name': 'Inter', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
                                        format_headers = workbook.add_format({'bold': True, 'fg_color': '#4431B0', 'font_color': 'white', 'font_name': 'Inter', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
                                        format_data = workbook.add_format({'font_name': 'Inter', 'font_size': 11, 'valign': 'vcenter'})
                                        
                                        for col_num, value in enumerate(df_final.columns.values):
                                            fmt = format_dest if col_num == 0 else format_headers
                                            worksheet.write(0, col_num, value, fmt)
                                            max_len = max(df_final.iloc[:, col_num].astype(str).map(len).max(), len(str(value))) + 5
                                            worksheet.set_column(col_num, col_num, max_len, format_data)
                                        worksheet.freeze_panes(1, 0)
                                    
                                    nombre_archivo = f"PLANTILLA_HSM_{datetime.datetime.now().strftime('%d-%m-%y')}"
                                    st.download_button(label="Descargar Plantilla (.xlsx)", data=output.getvalue(), file_name=f"{nombre_archivo}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                                else:
                                    st.warning("Ningún número superó los filtros.")
                else:
                    st.error("No se encontró la columna 'ESTADO'.")

            # LÓGICA 2: SEGMENTOS
            elif categoria == "Segmentos":
                st.success(f"Se consolidaron {len(uploaded_files)} archivo(s) de Segmentos con {len(df)} registros.")
                
                st.markdown("### 2. Estructura de Salida y Control")
                exportar_nombre = st.checkbox("Incluir columna NOMBRE", value=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                usar_testigo_seg = st.checkbox("Añadir mi número", key="chk_seg")
                
                num_asesor_seg = ""
                nombre_asesor_seg = ""
                
                if usar_testigo_seg:
                    col_ts1, col_ts2 = st.columns(2)
                    with col_ts1:
                        num_asesor_seg = st.text_input("Número (Requerido):", placeholder="Ej: 987654321", key="num_seg")
                    with col_ts2:
                        nombre_asesor_seg = st.text_input("Nombre (Opcional):", placeholder="Ej: Manuel", key="nom_seg")
                
                if st.button("Procesar Segmentos"):
                    with st.spinner('Limpiando caracteres y validando números...'):
                        resultados = []
                        historial = set()
                        
                        num_testigo_seg = ""
                        if usar_testigo_seg:
                            num_testigo_seg = limpiar_numero_testigo(num_asesor_seg)
                            if num_asesor_seg and not num_testigo_seg:
                                st.warning("El número ingresado no es válido. Se procesará sin él.")
                            elif num_testigo_seg:
                                historial.add(f"ASESOR_{num_testigo_seg}")
                                fila_testigo = {'destination': num_testigo_seg}
                                if exportar_nombre:
                                    fila_testigo['NOMBRE'] = nombre_asesor_seg.strip() if nombre_asesor_seg.strip() else "Estimado(a)"
                                resultados.append(fila_testigo)

                        phone_col = next((c for c in df.columns if "WHATSAPP" in str(c).upper() or "NÚMERO" in str(c).upper() or "NUMERO" in str(c).upper()), None)
                        nombres_col = next((c for c in df.columns if "NOMBRES" in str(c).upper()), None)
                        paterno_col = next((c for c in df.columns if "APELLIDO_PATERNO" in str(c).upper() or "APELLIDO PATERNO" in str(c).upper()), None)
                        
                        if not phone_col:
                            st.error("No se detectó la columna de teléfono/WhatsApp.")
                        else:
                            for index, row in df.iterrows():
                                num_raw = str(row.get(phone_col, '')).strip()
                                if not num_raw or num_raw.lower() == 'nan': continue
                                if num_raw.endswith('.0'): num_raw = num_raw[:-2]
                                limpio = re.sub(r'\D', '', num_raw)
                                final = ""
                                if len(limpio) == 9 and limpio.startswith("9"): final = "51" + limpio
                                elif len(limpio) == 11 and limpio.startswith("519"): final = limpio
                                
                                if final and final not in ["51999999999", "51987654321"]:
                                    val_nombres = str(row.get(nombres_col, '')).strip() if nombres_col else ""
                                    val_paterno = str(row.get(paterno_col, '')).strip() if paterno_col else ""
                                    val_nombres = "" if val_nombres.lower() == 'nan' else val_nombres
                                    val_paterno = "" if val_paterno.lower() == 'nan' else val_paterno
                                    
                                    if val_nombres: nombre_final = val_nombres
                                    elif val_paterno: nombre_final = re.sub(r'[^a-zA-Z\s]', '', val_paterno).strip()
                                    else: nombre_final = "Estimado(a)"
                                    if not nombre_final: nombre_final = "Estimado(a)"

                                    clave = f"{nombre_final}_{final}"
                                    if clave not in historial and f"ASESOR_{final}" not in historial:
                                        historial.add(clave)
                                        fila_res = {'destination': final}
                                        if exportar_nombre: fila_res["NOMBRE"] = nombre_final
                                        resultados.append(fila_res)
                            
                            if resultados:
                                df_final = pd.DataFrame(resultados)
                                registrar_kpi("Segmentos", len(df_final), bool(num_testigo_seg))
                                guardar_historial_bd(st.session_state.user.id, nombres_archivos, "Segmentos", len(df_final), bool(num_testigo_seg))
                                st.success(f"Se extrajeron {len(df_final)} contactos válidos y limpios.")
                                
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                    df_final.to_excel(writer, index=False, sheet_name='Chattigo')
                                    workbook = writer.book
                                    worksheet = writer.sheets['Chattigo']
                                    format_dest = workbook.add_format({'bold': True, 'fg_color': '#F17B27', 'font_color': 'white', 'font_name': 'Inter', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
                                    format_headers = workbook.add_format({'bold': True, 'fg_color': '#4431B0', 'font_color': 'white', 'font_name': 'Inter', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
                                    format_data = workbook.add_format({'font_name': 'Inter', 'font_size': 11, 'valign': 'vcenter'})
                                    
                                    for col_num, value in enumerate(df_final.columns.values):
                                        fmt = format_dest if col_num == 0 else format_headers
                                        worksheet.write(0, col_num, value, fmt)
                                        max_len = max(df_final.iloc[:, col_num].astype(str).map(len).max(), len(str(value))) + 5
                                        worksheet.set_column(col_num, col_num, max_len, format_data)
                                    worksheet.freeze_panes(1, 0)
                                
                                nombre_archivo = f"PLANTILLA_HSM_{datetime.datetime.now().strftime('%d-%m-%y')}"
                                st.download_button(label="Descargar Plantilla (.xlsx)", data=output.getvalue(), file_name=f"{nombre_archivo}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                            else:
                                st.warning("Ningún número superó los filtros.")
        except Exception as e:
            st.error(f"Ocurrió un error al procesar: {e}")

# ==========================================
# PESTAÑA 2: MI HISTORIAL (ASESOR Y ADMIN)
# ==========================================
with tabs[1]:
    st.markdown("### Últimos 10 archivos procesados")
    res = supabase.table("historial_procesamiento").select("*").eq("user_id", st.session_state.user.id).order("fecha_hora", desc=True).limit(10).execute()
    if res.data:
        df_historial = pd.DataFrame(res.data)
        df_historial['fecha_hora'] = pd.to_datetime(df_historial['fecha_hora']).dt.strftime('%d-%m-%Y %H:%M')
        df_historial = df_historial[['fecha_hora', 'nombre_archivo', 'categoria', 'filas_procesadas']]
        df_historial.columns = ['Fecha y Hora', 'Archivo Procesado', 'Categoría', 'Contactos Extraídos']
        st.dataframe(df_historial, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no has procesado ningún archivo.")

# ==========================================
# PESTAÑAS 3 Y 4: EXCLUSIVAS DE ADMIN
# ==========================================
if st.session_state.rol == 'admin':
    with tabs[2]:
        st.markdown("### Panel de Control e Impacto Global")
        res_total = supabase.table("historial_procesamiento").select("*").execute()
        perfiles_res = supabase.table("perfiles").select("id, nombre, apellido").execute()
        
        if res_total.data and perfiles_res.data:
            df_dash = pd.DataFrame(res_total.data)
            df_perfiles = pd.DataFrame(perfiles_res.data)
            df_perfiles['Asesor'] = df_perfiles['nombre'] + " " + df_perfiles['apellido']
            
            df_cruzado = pd.merge(df_dash, df_perfiles, left_on='user_id', right_on='id', how='left')
            df_cruzado['Asesor'] = df_cruzado['Asesor'].fillna("Usuario Eliminado")
            df_cruzado['Fecha'] = pd.to_datetime(df_cruzado['fecha_hora']).dt.date
            
            # Filtro de Fechas
            col_f1, col_f2 = st.columns(2)
            min_date = df_cruzado['Fecha'].min()
            max_date = df_cruzado['Fecha'].max()
            with col_f1:
                fecha_inicio = st.date_input("Fecha Inicio", min_date)
            with col_f2:
                fecha_fin = st.date_input("Fecha Fin", max_date)
                
            df_filtrado_dash = df_cruzado[(df_cruzado['Fecha'] >= fecha_inicio) & (df_cruzado['Fecha'] <= fecha_fin)]
            
            # Tarjetas Macro
            total_filas = int(df_filtrado_dash['filas_procesadas'].sum())
            total_ejecuciones = len(df_filtrado_dash)
            usuarios_recurrentes = df_filtrado_dash['user_id'].nunique()
            tasa_testigo = round((df_filtrado_dash['uso_testigo'].sum() / total_ejecuciones) * 100, 1) if total_ejecuciones > 0 else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Datos Exportados", f"{total_filas:,}")
            c2.metric("Bases Procesadas", total_ejecuciones)
            c3.metric("Usuarios Activos", usuarios_recurrentes)
            c4.metric("Tasa Uso Testigo", f"{tasa_testigo}%")
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("#### Ranking de Datos Exportados por Asesor")
                ranking_vol = df_filtrado_dash.groupby('Asesor')['filas_procesadas'].sum().sort_values(ascending=True)
                st.bar_chart(ranking_vol, color="#E3173E", height=320)
                
            with col_g2:
                st.markdown("#### Evolución de Datos Exportados en el Tiempo")
                evol_tiempo = df_filtrado_dash.groupby('Fecha')['filas_procesadas'].sum()
                st.line_chart(evol_tiempo, color="#E3173E", height=320)
                
            st.markdown("#### Ponderado de Uso por Asesor")
            ponderado = df_filtrado_dash.groupby('Asesor').agg(
                Bases_Procesadas=('id_x', 'count'),
                Datos_Exportados=('filas_procesadas', 'sum')
            ).reset_index()
            ponderado['Peso (%)'] = ((ponderado['Datos_Exportados'] / total_filas) * 100).round(1).astype(str) + '%'
            ponderado = ponderado.sort_values(by='Datos_Exportados', ascending=False)
            ponderado.columns = ['Asesor', 'Bases Procesadas', 'Contactos Exportados', 'Ponderado del Total']
            st.dataframe(ponderado, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos operativos registrados aún.")

    with tabs[3]:
        st.markdown("### Administración de Cuentas de Usuario")
        if not SUPABASE_SERVICE_KEY:
            st.warning("Nota: Para poder cambiar contraseñas o eliminar usuarios, asegúrate de haber agregado la variable SUPABASE_SERVICE_KEY en Render.")
            
        perfiles_list = supabase.table("perfiles").select("*").order("creado_el", desc=True).execute()
        if perfiles_list.data:
            for idx, u in enumerate(perfiles_list.data):
                with st.expander(f"{u['nombre']} {u['apellido']}  —  {u['email']}  ({u['rol'].upper()})"):
                    col_u1, col_u2 = st.columns([3, 1])
                    with col_u1:
                        nueva_pass = st.text_input("Asignar nueva contraseña (mín. 6 caracteres)", key=f"pass_{u['id']}", type="password")
                        if st.button("Actualizar Contraseña", key=f"btn_pass_{u['id']}"):
                            if len(nueva_pass) < 6:
                                st.error("La contraseña debe tener al menos 6 caracteres.")
                            else:
                                try:
                                    admin_supabase.auth.admin.update_user_by_id(u['id'], {"password": nueva_pass})
                                    st.success(f"Contraseña actualizada para {u['nombre']}.")
                                except Exception as e:
                                    st.error(f"Error al cambiar clave: {e}")
                    with col_u2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if u['id'] != st.session_state.user.id:
                            if st.button("Eliminar Usuario", key=f"btn_del_{u['id']}"):
                                try:
                                    supabase.table("historial_procesamiento").delete().eq("user_id", u['id']).execute()
                                    supabase.table("perfiles").delete().eq("id", u['id']).execute()
                                    admin_supabase.auth.admin.delete_user(u['id'])
                                    st.success("Usuario eliminado correctamente.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al eliminar: {e}")
