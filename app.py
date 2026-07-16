import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar
import plotly.express as px
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# ⚡ CONFIGURACIÓN DE PÁGINA Y CONEXIÓN
# ==========================================
st.set_page_config(page_title="Disponibilidades ENEL", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ==========================================
# 📧 FUNCIONES DE CORREO (OUTLOOK / OFFICE 365)
# ==========================================
def obtener_config_correo():
    try: 
        data = supabase.table("config_admin").select("*").execute().data
        if data: return data[0]
        return None
    except: return None

def enviar_correo(destinatario, asunto, mensaje_html):
    if not destinatario: return False
    config = obtener_config_correo()
    if not config or not config.get("correo_bot") or not config.get("password_bot"):
        print("Faltan credenciales del bot para enviar correo.")
        return False
        
    remitente = config["correo_bot"]
    password = config["password_bot"]
    
    try:
        msg = MIMEMultipart()
        msg['From'] = remitente
        msg['To'] = destinatario
        msg['Subject'] = asunto
        msg.attach(MIMEText(mensaje_html, 'html'))
        
        server = smtplib.SMTP('smtp.office365.com', 587)
        server.starttls()
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        print(f"✅ Correo enviado con éxito a {destinatario}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar correo: {e}")
        return False

# ==========================================
# 🛠️ FUNCIONES AUXILIARES Y RECUPERACIÓN DE DATOS
# ==========================================
def obtener_ingenieros(): 
    try: return supabase.table("ingenieros").select("*").execute().data
    except: return []

def obtener_vacaciones(): 
    try: return supabase.table("vacaciones").select("*").execute().data
    except: return []

def obtener_asignaciones(): 
    try: return supabase.table("asignaciones").select("*").execute().data
    except: return []

def obtener_festivos_extra():
    try: return supabase.table("festivos_extra").select("*").execute().data
    except: return []

def obtener_propuestas():
    try: return supabase.table("propuestas_ausentismos").select("*").execute().data
    except: return []

def obtener_contrasenas():
    try: return supabase.table("credenciales_admin").select("*").execute().data
    except: return []

def obtener_estilo_motivo(motivo, estado="Aprobado"):
    if estado == "Pendiente": return ("⏳", "#fff3e0", "#e65100")
    if estado == "Rechazado": return ("❌", "#ffebee", "#c62828")
    
    estilos = {
        "Vacaciones": ("🌴", "#e0f7fa", "#006064"),
        "Incapacidad Médica": ("🤒", "#ffebee", "#c62828"),
        "Permiso Empresa": ("🏢", "#f3e5f5", "#6a1b9a"),
        "Licencia": ("📜", "#e8f5e9", "#2e7d32"),
        "Festivo": ("🎊", "#e8eaf6", "#283593"),
        "Otro": ("⚠️", "#fff8e1", "#ff8f00")
    }
    return estilos.get(motivo, ("⚠️", "#fff8e1", "#ff8f00"))

def obtener_estilo_rol(tipo_dia, rol_mostrar):
    if "MANUAL" in tipo_dia.upper(): return ("📌", "#ffe0b2", "#e65100")
    if "Despacho" in rol_mostrar or "DESPACHO" in tipo_dia.upper(): return ("🌅", "#f3e5f5", "#4a148c")
    if "Líder" in rol_mostrar: return ("👑", "#e3f2fd", "#1565c0")
    if "Apoyo" in rol_mostrar: return ("🤝", "#e8f5e9", "#2e7d32")
    if "Supervisor" in rol_mostrar: return ("🛡️", "#fff3e0", "#e65100")
    return ("⚡", "#f3e5f5", "#6a1b9a")

# Recuperación de datos iniciales
lista_ingenieros = obtener_ingenieros()
lista_vacaciones = obtener_vacaciones()
lista_asignaciones = obtener_asignaciones()
lista_festivos_extra = obtener_festivos_extra()
lista_propuestas = obtener_propuestas()
lista_contrasenas = obtener_contrasenas()

dict_nombres_ing = {ing["id"]: ing["nombre"] for ing in lista_ingenieros}
dict_correos_ing = {ing["id"]: ing.get("correo", "") for ing in lista_ingenieros}

# ==========================================
# 🔐 SISTEMA DE AUTENTICACIÓN Y ROLES
# ==========================================
if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_izq, col_centro, col_der = st.columns([1, 2, 1])
    
    with col_centro:
        st.markdown("""
        <div style='text-align: center; padding: 25px; background-color: #ffffff; border-radius: 12px; border-bottom: 5px solid #ff9800; box-shadow: 0px 8px 20px rgba(0,0,0,0.08); margin-bottom: 25px;'>
            <h1 style='color: #1e3c72; margin-bottom: 5px; font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;'>⚡ DISPONIBILIDADES</h1>
            <h4 style='color: #7f8c8d; margin-top: 0px; font-weight: 400;'>Plataforma de Control Operativo y Equidad</h4>
        </div>
        """, unsafe_allow_html=True)
        
        tipo_acceso = st.selectbox("👤 Selecciona tu perfil de acceso:", ["👨‍💻 Empleado (Consulta y Solicitudes)", "🛡️ Administrador / Jefe"])
        st.markdown("<hr style='margin: 15px 0px;'>", unsafe_allow_html=True)
        
        if "Administrador" in tipo_acceso:
            pwd = st.text_input("🔑 Contraseña de acceso seguro:", type="password")
            if st.button("🚀 Ingresar al Sistema", use_container_width=True, type="primary"):
                claves_validas = [p['password'] for p in lista_contrasenas] if lista_contrasenas else []
                claves_validas.append("AdminEnel2026*")
                
                if pwd in claves_validas:
                    st.session_state.role = "admin"
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta. Intenta nuevamente.")
        else:
            st.info("💡 **Modo Empleado:** Acceso a consulta del calendario, envío de propuestas de ausentismo y auditoría de equidad.")
            if st.button("🚀 Ingresar como Empleado", use_container_width=True, type="primary"):
                st.session_state.role = "empleado"
                st.rerun()
        
        st.markdown("""
        <div style='text-align: center; margin-top: 35px; padding: 25px; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.15);'>
            <p style='margin: 0; font-size: 13px; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px;'>Diseñado y Desarrollado por</p>
            <h2 style='margin: 8px 0; color: #ffffff; font-weight: 600;'>👨‍💻 Sergio Cutiva</h2>
            <div style='width: 60px; height: 3px; background-color: #ff9800; margin: 12px auto; border-radius: 2px;'></div>
            <p style='margin: 0; font-size: 14px; line-height: 1.6;'>
                <span style='opacity: 0.9;'>📧 sergio.cutiva@enel.com</span><br>
                <span style='opacity: 0.9;'>📧 sergiocutivam@gmail.com</span>
            </p>
            <p style='margin: 15px 0 0 0; font-size: 12px; opacity: 0.7; font-style: italic;'>Automatización y Mejora de Procesos | Enel Colombia</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.stop() 

# ==========================================
# 👨‍💻 BARRA LATERAL (CONFIGURACIÓN)
# ==========================================
with st.sidebar:
    st.markdown(f"### ⚡ ENEL Colombia")
    if st.session_state.role == "admin": st.success("🛡️ Sesión: Administrador")
    else: st.info("👨‍💻 Sesión: Empleado")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.role = None
        st.rerun()
        
    st.markdown("---")
    
    if st.session_state.role == "admin":
        with st.expander("📧 Configurar Correos (Outlook)", expanded=False):
            st.caption("Configura el bot enviador y el correo receptor del administrador.")
            config_actual = obtener_config_correo() or {}
            
            with st.form("form_config_correos"):
                c_jefe = st.text_input("Recibe alertas (Correo del Jefe):", value=config_actual.get("correo_jefe", ""))
                c_bot = st.text_input("Correo Bot (Outlook que envía):", value=config_actual.get("correo_bot", ""))
                p_bot = st.text_input("Contraseña App (Outlook):", value=config_actual.get("password_bot", ""), type="password")
                
                col_btn1, col_btn2 = st.columns(2)
                btn_guardar = col_btn1.form_submit_button("💾 Guardar Todo")
                btn_borrar_jefe = col_btn2.form_submit_button("🗑️ Quitar Jefe")
                
                if btn_guardar:
                    datos = {"correo_jefe": c_jefe, "correo_bot": c_bot, "password_bot": p_bot}
                    if config_actual.get("id"):
                        supabase.table("config_admin").update(datos).eq("id", config_actual["id"]).execute()
                    else:
                        supabase.table("config_admin").insert(datos).execute()
                    st.success("Configuración de correos guardada.")
                    st.rerun()
                    
                if btn_borrar_jefe:
                    if config_actual.get("id"):
                        supabase.table("config_admin").update({"correo_jefe": ""}).eq("id", config_actual["id"]).execute()
                        st.success("Correo del jefe eliminado.")
                        st.rerun()

        with st.expander("🔐 Gestión de Contraseñas", expanded=False):
            st.caption("Administra las claves de acceso al sistema.")
            nueva_pwd = st.text_input("Agregar nueva contraseña:", type="password")
            if st.button("💾 Guardar Contraseña"):
                if nueva_pwd:
                    try:
                        supabase.table("credenciales_admin").insert({"password": nueva_pwd}).execute()
                        st.success("Contraseña añadida.")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
            
            if lista_contrasenas:
                st.markdown("---")
                st.markdown("**Contraseñas Registradas:**")
                for p in lista_contrasenas:
                    col_pwd1, col_pwd2 = st.columns([3, 1])
                    col_pwd1.code("*" * len(p['password']))
                    if col_pwd2.button("🗑️", key=f"del_pwd_{p['id']}"):
                        try:
                            supabase.table("credenciales_admin").delete().eq("id", p["id"]).execute()
                            st.rerun()
                        except: pass
        st.markdown("---")
    
    with st.expander("📆 Configuración de Festivos Fijos", expanded=False):
        str_festivos_default = (
            "2026-01-01, 2026-01-12, 2026-03-23, 2026-04-02, 2026-04-03, 2026-05-01, 2026-05-18, 2026-06-08, 2026-06-15, 2026-06-29, 2026-07-20, 2026-08-07, 2026-08-17, 2026-10-12, 2026-11-02, 2026-11-16, 2026-12-08, 2026-12-25, "
            "2027-01-01, 2027-01-11, 2027-03-22, 2027-03-25, 2027-03-26, 2027-05-01, 2027-05-10, 2027-05-31, 2027-06-07, 2027-07-05, 2027-07-20, 2027-08-07, 2027-08-16, 2027-10-18, 2027-11-01, 2027-11-15, 2027-12-08, 2027-12-25"
        )
        if st.session_state.role == "admin":
            st.caption("Festivos Colombianos base")
            str_festivos = st.text_area("Lista Base (AAAA-MM-DD)", str_festivos_default, height=100)
        else:
            str_festivos = str_festivos_default
            st.caption("Los festivos base son inyectados automáticamente por el sistema.")
    
    if st.session_state.role == "admin":
        with st.expander("➕ Agregar Nuevo Festivo (Dinámico)", expanded=False):
            st.caption("Agrega días festivos imprevistos (Ej. Decretos de última hora)")
            with st.form("form_festivo_nuevo"):
                f_nuevo_festivo = st.date_input("Fecha del Festivo")
                desc_festivo = st.text_input("Descripción / Motivo")
                if st.form_submit_button("Guardar Festivo"):
                    try:
                        supabase.table("festivos_extra").insert({"fecha": str(f_nuevo_festivo), "descripcion": desc_festivo}).execute()
                        st.success("Festivo agregado.")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
                        
            if lista_festivos_extra:
                st.markdown("**Festivos Adicionales Guardados:**")
                for f_ext in lista_festivos_extra:
                    st.caption(f"📍 {f_ext['fecha']} - {f_ext['descripcion']}")

    festivos_colombia_lista = [f.strip() for f in str_festivos.split(",") if f.strip()]
    festivos_colombia_lista.extend([f['fecha'] for f in lista_festivos_extra])

    st.markdown("---")
    st.markdown("**Desarrollado y mantenido por:**")
    st.markdown("👨‍💻 **Sergio Cutiva**")
    st.markdown("📧 *sergio.cutiva@enel.com*")
    st.markdown("---")
    st.caption("Versión 11.5 | Fusión Completa de Reglas e Inviabilidades")

# ==========================================
# ⚡ INTERFAZ PRINCIPAL (NAVEGADOR HORIZONTAL)
# ==========================================
FECHA_MIN = date(2026, 1, 1)
st.title("⚡ Panel Operativo de Disponibilidades")
st.markdown("---")

if st.session_state.role == "admin":
    opciones_nav = [
        "📅 Calendario Operativo", 
        "📊 Dashboard Ejecutivo",
        "📩 Portal de Ausentismos", 
        "👥 Gestión de Equipo", 
        "🌴 Panel RRHH", 
        "⚙️ Motor Algorítmico",
        "🔄 Asignaciones Manuales"
    ]
else:
    opciones_nav = [
        "📅 Calendario Operativo", 
        "📊 Dashboard y Auditoría",
        "📩 Portal de Ausentismos"
    ]

pestana_actual = st.radio("Menú Principal:", opciones_nav, horizontal=True, label_visibility="collapsed")
st.markdown("---")

# ==========================================
# 📊 PESTAÑA DASHBOARD Y AUDITORÍA
# ==========================================
if "Dashboard" in pestana_actual:
    st.header("📈 Panel de Análisis Operativo")
    
    if len(lista_ingenieros) > 0:
        total_ing = len([i for i in lista_ingenieros if not i.get('exento_disponibilidad', False)])
        total_turnos = len(lista_asignaciones)
        total_ausencias = sum([(datetime.strptime(v['fecha_fin'], "%Y-%m-%d") - datetime.strptime(v['fecha_inicio'], "%Y-%m-%d")).days + 1 for v in lista_vacaciones]) if lista_vacaciones else 0
        prop_pendientes = len([p for p in lista_propuestas if p.get('estado') == 'Pendiente'])
        
        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        col_k1.metric(label="👥 Ingenieros Activos (Motor)", value=total_ing)
        col_k2.metric(label="⚡ Total Turnos Asignados", value=total_turnos)
        col_k3.metric(label="🌴 Días de Ausentismo (Año)", value=total_ausencias)
        col_k4.metric(label="⏳ Propuestas Pendientes", value=prop_pendientes)
        st.markdown("---")

    st.markdown("### 🕵️ Auditoría de Transparencia (Motor Algorítmico)")
    st.caption("Verifica el cumplimiento de los tiempos de descanso (cooldown) y alternancia de turnos de cualquier compañero.")
    ing_auditar = st.selectbox("Selecciona un profesional para auditar su historial reciente:", lista_ingenieros, format_func=lambda x: x["nombre"])
    if ing_auditar:
        turnos_ing_audit = sorted([a for a in lista_asignaciones if a["ingeniero_id"] == ing_auditar["id"]], key=lambda x: datetime.strptime(x["fecha"], "%Y-%m-%d"), reverse=True)
        if turnos_ing_audit:
            col_aud1, col_aud2 = st.columns([1, 2])
            with col_aud1:
                st.success(f"Últimos registros de **{ing_auditar['nombre']}**:")
                for t in turnos_ing_audit[:6]:
                    st.markdown(f"- 📅 **{t['fecha']}** : {t['tipo_dia']}")
            with col_aud2:
                st.info("💡 **Reglas verificadas por el sistema:**\n- 20 días mínimo entre bloques de guardia.\n- Sin FDS consecutivos ni turnos de seguido.\n- Adyacencia mínima de 7 días estricta aislando Despachos.\n- Límite absoluto: Nadie es Líder 2 veces seguidas.")
        else:
            st.write("No hay turnos registrados en el historial para esta persona.")
    
    st.markdown("---")
    
    if len(lista_asignaciones) == 0: 
        st.warning("No hay turnos asignados para analizar gráficas.")
    else:
        df_asig = pd.DataFrame(lista_asignaciones)
        df_asig['Nombre'] = df_asig['ingeniero_id'].map(dict_nombres_ing)
        
        def categorizar_turno(row):
            tipo = row['tipo_dia'].upper()
            fecha_str = row['fecha']
            fecha_dt = pd.to_datetime(fecha_str)
            if "DESPACHO" in tipo: return "DESPACHO"
            if "FDS" in tipo: return "FDS"
            if "SEMANA" in tipo: return "SEMANA"
            if "MANUAL" in tipo:
                if fecha_dt.weekday() >= 4: return "FDS"
                elif fecha_dt.weekday() == 0 and fecha_str in festivos_colombia_lista: return "FDS"
                else: return "SEMANA"
            return "SEMANA"
            
        df_asig['Categoria'] = df_asig.apply(categorizar_turno, axis=1)
        df_asig['Fecha_dt'] = pd.to_datetime(df_asig['fecha'])
        df_asig['Mes'] = df_asig['Fecha_dt'].dt.strftime('%Y-%m') 
        
        df_asig = df_asig.sort_values(['Nombre', 'Categoria', 'Fecha_dt'])
        df_asig['Dias_Dif'] = df_asig.groupby(['Nombre', 'Categoria'])['Fecha_dt'].diff().dt.days
        df_asig['Nuevo_Turno'] = (df_asig['Dias_Dif'] > 1).astype(int)
        df_asig['Nuevo_Turno'] = df_asig['Nuevo_Turno'].fillna(1) 
        df_asig['ID_Bloque'] = df_asig.groupby(['Nombre', 'Categoria'])['Nuevo_Turno'].cumsum()
        df_turnos_agrupados = df_asig.groupby(['Nombre', 'Categoria', 'ID_Bloque']).size().reset_index(name='Dias_en_Turno')
        conteo_turnos_reales = df_turnos_agrupados.groupby(['Nombre', 'Categoria']).size().reset_index(name='Cantidad_Turnos')

        st.markdown("### ⚖️ Distribución de Carga Operativa")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_turnos = px.bar(conteo_turnos_reales, x='Nombre', y='Cantidad_Turnos', color='Categoria', title="Bloques de Guardia Asignados (Semana vs FDS vs Despacho)", color_discrete_map={"SEMANA": "#1f77b4", "FDS": "#ff7f0e", "DESPACHO": "#8e24aa"}, text_auto=True)
            st.plotly_chart(fig_turnos, use_container_width=True)
        with col_g2:
            conteo_dias = df_asig.groupby(['Nombre', 'Categoria']).size().reset_index(name='Cantidad_Dias')
            fig_dias = px.bar(conteo_dias, x='Nombre', y='Cantidad_Dias', color='Categoria', title="Días Exactos Trabajados", color_discrete_map={"SEMANA": "#1f77b4", "FDS": "#ff7f0e", "DESPACHO": "#8e24aa"}, text_auto=True)
            st.plotly_chart(fig_dias, use_container_width=True)

        st.markdown("---")
        
        st.markdown("### 📈 Evolución de Carga por Mes")
        tendencia_mes = df_asig.groupby(['Mes', 'Categoria']).size().reset_index(name='Turnos')
        fig_linea = px.line(tendencia_mes, x='Mes', y='Turnos', color='Categoria', markers=True, title="Histórico de Ocupación por Mes", color_discrete_map={"SEMANA": "#1f77b4", "FDS": "#ff7f0e", "DESPACHO": "#8e24aa"})
        st.plotly_chart(fig_linea, use_container_width=True)

        st.markdown("---")

        st.markdown("### 🌴 Impacto de Ausentismos")
        if len(lista_vacaciones) > 0:
            vac_records = []
            for v in lista_vacaciones:
                nom = dict_nombres_ing.get(v['ingeniero_id'], 'Desconocido')
                dias_fuera = (datetime.strptime(v['fecha_fin'], "%Y-%m-%d") - datetime.strptime(v['fecha_inicio'], "%Y-%m-%d")).days + 1
                vac_records.append({'Nombre': nom, 'Motivo': v.get('motivo', 'Otro'), 'Dias_Ausente': dias_fuera})
            df_vac_stats = pd.DataFrame(vac_records).groupby(['Nombre', 'Motivo'])['Dias_Ausente'].sum().reset_index()
            
            col_v1, col_v2 = st.columns([2, 1])
            with col_v1:
                fig_vac_bar = px.bar(df_vac_stats, x='Nombre', y='Dias_Ausente', color='Motivo', title="Días Totales de Ausencia por Profesional", text_auto=True, color_discrete_map={"Vacaciones": "#00bcd4", "Incapacidad Médica": "#f44336", "Permiso Empresa": "#9c27b0", "Licencia": "#4caf50", "Festivo": "#283593", "Otro": "#ff9800"})
                st.plotly_chart(fig_vac_bar, use_container_width=True)
            with col_v2: 
                st.plotly_chart(px.pie(df_vac_stats, names='Motivo', values='Dias_Ausente', title="Motivos Globales", hole=0.4), use_container_width=True)
        else: st.info("No hay registros de ausentismos para analizar.")

        st.markdown("---")
        
        df_asig['Rol_Limpio'] = df_asig['tipo_dia'].apply(lambda x: x.split('(')[-1].replace(')', '').strip() if '(' in x else x)
        df_asig['Rol_Limpio'] = df_asig['Rol_Limpio'].replace({"Apoyo 1": "Apoyo", "Apoyo 2": "Apoyo", "Despacho 6 AM": "Despacho"})
        roles_por_turno = df_asig.groupby(['Nombre', 'Rol_Limpio', 'ID_Bloque', 'Categoria']).size().reset_index(name='Dias_En_Rol')
        conteo_roles = roles_por_turno.groupby(['Nombre', 'Rol_Limpio']).size().reset_index(name='Cantidad_Turnos')
        
        st.markdown("### 🎭 Análisis Profundo de Roles Específicos")
        col_r_gen, col_r_det = st.columns([1, 1])
        
        with col_r_gen:
            fig_roles = px.bar(conteo_roles, y='Nombre', x='Cantidad_Turnos', color='Rol_Limpio', title="Consolidado Total de Funciones", color_discrete_map={"Líder": "#1565c0", "Apoyo": "#2e7d32", "Supervisor": "#e65100", "Despacho": "#8e24aa"}, orientation='h', barmode='stack', text_auto=True)
            fig_roles.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_roles, use_container_width=True)
            
        with col_r_det:
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("Detalle Matricial de Turnos por Profesional")
            conteo_roles_cat = roles_por_turno.groupby(['Nombre', 'Rol_Limpio', 'Categoria']).size().reset_index(name='Cantidad_Turnos')
            pivot_roles_cat = conteo_roles_cat.pivot_table(index='Nombre', columns=['Categoria', 'Rol_Limpio'], values='Cantidad_Turnos', fill_value=0)
            pivot_roles_cat.columns = [f"{col[1]} en {col[0]}" for col in pivot_roles_cat.columns]
            pivot_roles_cat['Total Consolidado'] = pivot_roles_cat.sum(axis=1)
            st.dataframe(pivot_roles_cat.sort_values(by="Total Consolidado", ascending=False), use_container_width=True)

        st.markdown("---")
        st.markdown("### 🔍 Análisis Específico de Roles por Tipo de Jornada")
        conteo_roles_cat = roles_por_turno.groupby(['Nombre', 'Rol_Limpio', 'Categoria']).size().reset_index(name='Cantidad_Turnos')
        col_r1, col_r2 = st.columns([1, 1.8])
        
        with col_r1:
            ing_filtrado = st.selectbox("Seleccione el profesional a auditar:", df_asig['Nombre'].unique())
            fig_ind = px.bar(conteo_roles_cat[conteo_roles_cat['Nombre'] == ing_filtrado], x='Categoria', y='Cantidad_Turnos', color='Rol_Limpio', barmode='group', text_auto=True, title=f"Desglose para {ing_filtrado}", color_discrete_map={"Líder": "#1565c0", "Apoyo": "#2e7d32", "Supervisor": "#e65100", "Despacho": "#8e24aa"})
            st.plotly_chart(fig_ind, use_container_width=True)

        with col_r2:
            pivot_roles_cat = conteo_roles_cat.pivot_table(index='Nombre', columns=['Categoria', 'Rol_Limpio'], values='Cantidad_Turnos', fill_value=0)
            pivot_roles_cat.columns = [f"{col[1]} en {col[0]}" for col in pivot_roles_cat.columns]
            pivot_roles_cat['Total Consolidado'] = pivot_roles_cat.sum(axis=1)
            st.dataframe(pivot_roles_cat.sort_values(by="Total Consolidado", ascending=False), use_container_width=True)


        st.markdown("---")

        st.markdown("### 🗂️ Explorador de Datos Crudos")
        st.caption("Tablas detalladas con el registro exacto de las operaciones y personal.")
        col_t_left, col_t_right = st.columns(2)
        
        with col_t_left:
            st.markdown("**📝 Historial Completo de Asignaciones**")
            df_mostrar = df_asig[['fecha', 'Nombre', 'tipo_dia', 'Categoria']].copy()
            df_mostrar.columns = ['Fecha Asignada', 'Profesional', 'Rol Registrado', 'Tipo de Jornada']
            df_mostrar = df_mostrar.sort_values(by='Fecha Asignada', ascending=False)
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
            
        with col_t_right:
            st.markdown("**👥 Consolidado de Personal**")
            if len(lista_ingenieros) > 0:
                df_pers = pd.DataFrame(lista_ingenieros)
                df_pers['Estado Exención'] = df_pers.get('exento_disponibilidad', False).apply(lambda x: "Exento (No Motor)" if x else "Participa")
                df_pers['En Inducción'] = df_pers.get('es_nuevo', False).apply(lambda x: "Sí" if x else "No")
                cols_mostrar = ['nombre', 'rol', 'Estado Exención', 'En Inducción']
                df_pers_show = df_pers[cols_mostrar].copy()
                df_pers_show.columns = ['Nombre Completo', 'Rol Contractual', 'Estatus Guardia', '¿Es Nuevo?']
                st.dataframe(df_pers_show, use_container_width=True, hide_index=True)

# ==========================================
# 📅 PESTAÑA CALENDARIO
# ==========================================
elif "Calendario" in pestana_actual:
    st.header("🗓️ Visualización de Disponibilidad")
    
    with st.expander("📖 **¿Cómo se asignan los turnos? (Reglas de Transparencia)**"):
        st.markdown("""
        El motor algorítmico asigna los turnos automáticamente basándose en las siguientes reglas para garantizar total equidad:
        * **Muros Infranqueables:** Un profesional jamás recibirá turnos seguidos (Back-to-Back). Un Despacho aísla sus guardias usando la Regla Sandwich (7 días libres).
        * **Variables Independientes:** Los Despachos tienen su propio contador de nivelación para repartirse equitativamente. Hacer despachos NO suma turnos a tu nivelación de Guardia FDS/Semana.
        * **Jornadas Bloqueadas:** Se manejan bloques de Despacho (Lun-Vie), Semana (Lun-Jue) o Fin de Semana (Vie-Dom). En caso de Lunes Festivo, el fin de semana se extiende hasta el Lunes.
        * **Roles por Jornada:** En Semana operan 2 ingenieros (Líder/Apoyo). En FDS operan 4 personas (Líder, 2 Apoyos, 1 Supervisor). Despacho es individual.
        * **No Repetición de FDS:** 🔄 Ningún profesional (salvo Supervisores por necesidad operativa) puede ser asignado a un Fin de Semana si su última guardia fue también un Fin de Semana.
        * **Restricción de Líder Consecutivo:** 🚫 Ningún profesional puede ejercer el rol de Líder en dos turnos seguidos.
        * **Descanso (Cooldown):** ⏳ Nadie recibe un turno si no han pasado al menos 20 días desde su última guardia.
        * **Prioridad Restringidos:** ⚠️ Quienes no pueden hacer turnos de Fin de Semana, tienen máxima prioridad para recibir al menos un turno de Semana o Despacho al mes.
        * **Inducción (Prioridad Nuevo):** 🎓 El personal "Nuevo" es priorizado inicialmente en roles de Apoyo para garantizar un aprendizaje seguro sin exponer la operación.
        * **Excepciones de Último Recurso:** 🛑 El motor solo romperá las reglas de Cooldown y No Repetición de FDS si no hay más personal disponible para evitar huecos, pero **JAMÁS** romperá los muros infranqueables (turnos/líderes seguidos).
        """)
    st.markdown("---")

    if len(lista_ingenieros) == 0:
        st.info("ℹ️ El sistema no tiene profesionales registrados aún. El administrador debe configurarlos.")
    else:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            año_sel = st.selectbox("Seleccionar Año (Operativo):", [2026, 2027, 2028, 2029, 2030], index=0)
        with col_m2:
            mes_sel = st.selectbox("Seleccionar Mes (Operativo):", list(range(1, 13)), format_func=lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][x - 1])
            
        st.markdown("---")
        tipo_vista = st.radio("Formato de visualización:", ["📅 Vista Calendario", "🗂️ Vista Matriz (Por Persona)"], horizontal=True, key="vista_t1")
        
        primer_dia = datetime(año_sel, mes_sel, 1)
        if mes_sel == 12: ultimo_dia = datetime(año_sel + 1, 1, 1) - timedelta(days=1)
        else: ultimo_dia = datetime(año_sel, mes_sel + 1, 1) - timedelta(days=1)
        rango_dias = [primer_dia + timedelta(days=x) for x in range((ultimo_dia - primer_dia).days + 1)]

        if "Matriz" in tipo_vista:
            columnas_dias = [d.strftime("%Y-%m-%d") for d in rango_dias]
            nombres_columnas_bonitas = []
            for d in rango_dias:
                str_fecha = d.strftime("%Y-%m-%d")
                nombre_base = d.strftime("%d-%b (%a)")
                if str_fecha in festivos_colombia_lista: nombres_columnas_bonitas.append(f"🎊 {nombre_base}")
                else: nombres_columnas_bonitas.append(nombre_base)

            matriz_df = pd.DataFrame(index=[ing["nombre"] for ing in lista_ingenieros], columns=columnas_dias)
            matriz_df = matriz_df.fillna("—")
            
            for vac in lista_vacaciones:
                nom_ing = dict_nombres_ing.get(vac["ingeniero_id"])
                if nom_ing in matriz_df.index:
                    v_ini, v_fin = datetime.strptime(vac["fecha_inicio"], "%Y-%m-%d"), datetime.strptime(vac["fecha_fin"], "%Y-%m-%d")
                    dia_aux = v_ini
                    while dia_aux <= v_fin:
                        str_dia = dia_aux.strftime("%Y-%m-%d")
                        motivo = vac.get('motivo', 'Ausente')
                        emo, _, _ = obtener_estilo_motivo(motivo)
                        if str_dia in matriz_df.columns: matriz_df.at[nom_ing, str_dia] = f"{emo} {motivo}"
                        dia_aux += timedelta(days=1)
                        
            for asig in lista_asignaciones:
                nom_ing = dict_nombres_ing.get(asig["ingeniero_id"])
                str_fecha = asig["fecha"]
                if nom_ing in matriz_df.index and str_fecha in matriz_df.columns:
                    if "🌴" in matriz_df.at[nom_ing, str_fecha] or "🤒" in matriz_df.at[nom_ing, str_fecha]: 
                        matriz_df.at[nom_ing, str_fecha] = "⚠️ CRÍTICO"
                    else: 
                        tipo = asig.get('tipo_dia', 'DISPONIBLE')
                        rol_mostrar = tipo.split('(')[-1].replace(')', '') if '(' in tipo else tipo
                        icono, _, _ = obtener_estilo_rol(tipo, rol_mostrar)
                        matriz_df.at[nom_ing, str_fecha] = f"{icono} {rol_mostrar}"
            
            matriz_df.columns = nombres_columnas_bonitas
            st.dataframe(matriz_df, use_container_width=True)

        else:
            cal = calendar.Calendar(firstweekday=0)
            semanas = cal.monthdatescalendar(año_sel, mes_sel)
            cols_dias = st.columns(7)
            for i, nombre_dia in enumerate(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]):
                cols_dias[i].markdown(f"<div style='text-align: center; font-weight: bold; background-color: #f0f2f6; padding: 5px; border-radius: 5px;'>{nombre_dia}</div>", unsafe_allow_html=True)
            
            st.write("")
            for semana in semanas:
                cols_semana = st.columns(7)
                for i, dia in enumerate(semana):
                    with cols_semana[i]:
                        if dia.month == mes_sel:
                            str_dia = dia.strftime("%Y-%m-%d")
                            
                            if str_dia in festivos_colombia_lista:
                                st.markdown(f"**{dia.day}** 🎊")
                            else:
                                st.markdown(f"**{dia.day}**")
                                
                            turnos_hoy = [a for a in lista_asignaciones if a["fecha"] == str_dia]
                            vacaciones_hoy = [v for v in lista_vacaciones if datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date() <= dia <= datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date()]
                            
                            for v in vacaciones_hoy:
                                motivo = v.get('motivo', 'Otro')
                                emo, bg_col, txt_col = obtener_estilo_motivo(motivo)
                                st.markdown(f"<div style='background-color: {bg_col}; color: {txt_col}; padding: 4px; border-radius: 4px; font-size: 11px; margin-bottom: 2px;' title='{motivo}'>{emo} {dict_nombres_ing.get(v['ingeniero_id'], '')}</div>", unsafe_allow_html=True)
                            
                            for a in turnos_hoy:
                                tipo = a.get('tipo_dia', '')
                                rol_mostrar = tipo.split('(')[-1].replace(')', '') if '(' in tipo else ''
                                icono, color_bg, color_txt = obtener_estilo_rol(tipo, rol_mostrar)
                                st.markdown(f"<div style='background-color: {color_bg}; color: {color_txt}; padding: 4px; border-radius: 4px; font-size: 11px; margin-bottom: 2px; font-weight: bold;'>{icono} {dict_nombres_ing.get(a['ingeniero_id'], '')} ({rol_mostrar})</div>", unsafe_allow_html=True)
                                
                            st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color: #ccc;'>{dia.day}</span>", unsafe_allow_html=True)
                st.divider()

# ==========================================
# 📩 PESTAÑA PORTAL DE PROPUESTAS DE AUSENTISMOS
# ==========================================
elif "Ausentismos" in pestana_actual:
    st.header("📩 Portal de Propuestas de Vacaciones y Ausentismos")
    st.markdown("Los profesionales envían sus propuestas por aquí. Una vez aprobadas por el administrador, pasan automáticamente al Calendario Operativo y el motor las respeta.")
    
    if len(lista_ingenieros) > 0:
        col_p1, col_p2 = st.columns([1, 2])
        
        with col_p1:
            st.subheader("📤 Enviar Propuesta")
            with st.form("form_nueva_propuesta"):
                ing_propone = st.selectbox("1. Selecciona tu Nombre:", lista_ingenieros, format_func=lambda x: x["nombre"])
                motivo_prop = st.selectbox("2. Motivo de Ausencia:", ["Vacaciones", "Incapacidad Médica", "Permiso Empresa", "Licencia", "Otro"])
                fechas_prop = st.date_input("3. Rango de Fechas deseado:", [], min_value=FECHA_MIN)
                
                if st.form_submit_button("Enviar para Aprobación", use_container_width=True):
                    if len(fechas_prop) == 2:
                        f_inicio, f_fin = fechas_prop[0], fechas_prop[1]
                        
                        turnos_propios = [datetime.strptime(a["fecha"], "%Y-%m-%d").date() for a in lista_asignaciones if a["ingeniero_id"] == ing_propone["id"]]
                        fechas_solicitadas = [f_inicio + timedelta(days=x) for x in range((f_fin - f_inicio).days + 1)]
                        conflictos = [d for d in fechas_solicitadas if d in turnos_propios]
                        
                        if conflictos:
                            fechas_str = ", ".join([d.strftime("%Y-%m-%d") for d in conflictos])
                            st.error(f"⚠️ Operación denegada. Tienes disponibilidad asignada para los días: **{fechas_str}**. Por favor, consigue un relevo primero antes de enviar la propuesta.")
                        else:
                            try:
                                supabase.table("propuestas_ausentismos").insert({
                                    "ingeniero_id": ing_propone["id"],
                                    "fecha_inicio": str(f_inicio),
                                    "fecha_fin": str(f_fin),
                                    "motivo": motivo_prop,
                                    "estado": "Pendiente"
                                }).execute()
                                
                                # Enviar correo al Jefe de notificación
                                config = obtener_config_correo()
                                if config and config.get("correo_jefe"):
                                    html_msg = f"""<div style='font-family: Arial; padding: 20px; border: 1px solid #ddd; border-radius: 10px;'>
                                    <h2 style='color: #ff9800;'>⚡ ENEL - Nueva Solicitud</h2>
                                    <p><b>{ing_propone['nombre']}</b> ha registrado una nueva solicitud.</p>
                                    <ul><li>Desde: {f_inicio}</li><li>Hasta: {f_fin}</li><li>Motivo: {motivo_prop}</li></ul></div>"""
                                    enviar_correo(config["correo_jefe"], f"Nueva Solicitud: {motivo_prop} - {ing_propone['nombre']}", html_msg)

                                st.success("✅ Propuesta enviada al jefe con éxito.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error técnico. Detalle: {e}")
                    else:
                        st.error("⚠️ Debes seleccionar una fecha de inicio y una de fin.")
            
            st.markdown("---")
            st.subheader("🗑️ Anular Propuesta")
            propuestas_retirables = [p for p in lista_propuestas if p.get("estado") == "Pendiente"]
            if propuestas_retirables:
                prop_a_retirar = st.selectbox(
                    "Selecciona la propuesta a cancelar:", 
                    propuestas_retirables, 
                    format_func=lambda x: f"{dict_nombres_ing.get(x['ingeniero_id'])} - {x['motivo']} ({x['fecha_inicio']} a {x['fecha_fin']})",
                    key="sb_retirar"
                )
                if st.button("🗑️ Retirar mi propuesta", use_container_width=True):
                    try:
                        supabase.table("propuestas_ausentismos").delete().eq("id", prop_a_retirar["id"]).execute()
                        st.success("✅ Propuesta cancelada exitosamente.")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
            else:
                st.info("No hay propuestas pendientes que se puedan retirar.")

            if st.session_state.role == "admin":
                st.markdown("---")
                st.subheader("🔐 Panel del Jefe (Aprobaciones)")
                st.caption("Solo visible para administradores.")
                propuestas_pendientes = [p for p in lista_propuestas if p.get("estado") == "Pendiente"]
                
                if propuestas_pendientes:
                    prop_seleccionada = st.selectbox(
                        "Selecciona una propuesta pendiente para evaluar:", 
                        propuestas_pendientes, 
                        format_func=lambda x: f"{dict_nombres_ing.get(x['ingeniero_id'])} - {x['motivo']} ({x['fecha_inicio']} a {x['fecha_fin']})",
                        key="sb_jefe"
                    )
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("✅ Aprobar", use_container_width=True):
                            try:
                                supabase.table("propuestas_ausentismos").update({"estado": "Aprobado"}).eq("id", prop_seleccionada["id"]).execute()
                                supabase.table("vacaciones").insert({
                                    "ingeniero_id": prop_seleccionada["ingeniero_id"],
                                    "fecha_inicio": prop_seleccionada["fecha_inicio"],
                                    "fecha_fin": prop_seleccionada["fecha_fin"],
                                    "motivo": prop_seleccionada["motivo"]
                                }).execute()
                                
                                # Correo de confirmación al trabajador
                                correo_trabajador = dict_correos_ing.get(prop_seleccionada["ingeniero_id"])
                                if correo_trabajador:
                                    html_msg = f"<div style='font-family: Arial; padding: 20px; border: 2px solid #4CAF50; border-radius: 10px;'><h2 style='color:#4CAF50'>¡Aprobado!</h2><p>Tu solicitud de {prop_seleccionada['motivo']} ha sido aprobada oficialmente.</p></div>"
                                    enviar_correo(correo_trabajador, f"✅ APROBADO: {prop_seleccionada['motivo']}", html_msg)
                                    
                                st.success("Aprobada y movida al Calendario Operativo.")
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                    
                    with col_btn2:
                        if st.button("❌ Denegar", use_container_width=True):
                            try:
                                supabase.table("propuestas_ausentismos").update({"estado": "Rechazado"}).eq("id", prop_seleccionada["id"]).execute()
                                
                                # Correo de rechazo al trabajador
                                correo_trabajador = dict_correos_ing.get(prop_seleccionada["ingeniero_id"])
                                if correo_trabajador:
                                    html_msg = f"<div style='font-family: Arial; padding: 20px; border: 2px solid #F44336; border-radius: 10px;'><h2 style='color:#F44336'>Solicitud Denegada</h2><p>Tu solicitud de {prop_seleccionada['motivo']} no fue aprobada por necesidades de servicio.</p></div>"
                                    enviar_correo(correo_trabajador, f"❌ RECHAZADO: {prop_seleccionada['motivo']}", html_msg)
                                    
                                st.success("Propuesta rechazada.")
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                else:
                    st.info("No hay propuestas pendientes por revisar.")

        with col_p2:
            st.subheader("🗓️ Calendario Exclusivo de Propuestas")
            st.caption("Visualiza únicamente el estado de las solicitudes (Aprobadas, Pendientes, Rechazadas).")
            
            col_m1, col_m2 = st.columns(2)
            with col_m1: año_p = st.selectbox("Año (Propuestas):", [2026, 2027, 2028, 2029, 2030], index=0, key="año_p")
            with col_m2: mes_p = st.selectbox("Mes (Propuestas):", list(range(1, 13)), format_func=lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][x - 1], key="mes_p")
            
            st.markdown("---")
            tipo_vista_p = st.radio("Formato de visualización:", ["📅 Vista Calendario", "🗂️ Vista Matriz (Por Persona)"], horizontal=True, key="vista_p")
            
            primer_dia_p = datetime(año_p, mes_p, 1)
            ultimo_dia_p = (datetime(año_p + 1, 1, 1) - timedelta(days=1)) if mes_p == 12 else (datetime(año_p, mes_p + 1, 1) - timedelta(days=1))
            rango_dias_p = [primer_dia_p + timedelta(days=x) for x in range((ultimo_dia_p - primer_dia_p).days + 1)]
            
            if "Matriz" in tipo_vista_p:
                cols_dias_p = [d.strftime("%Y-%m-%d") for d in rango_dias_p]
                nombres_cols_p = [d.strftime("%d-%b") for d in rango_dias_p]

                matriz_prop_df = pd.DataFrame(index=[ing["nombre"] for ing in lista_ingenieros], columns=cols_dias_p)
                matriz_prop_df = matriz_prop_df.fillna("—")
                
                for p in lista_propuestas:
                    nom_ing = dict_nombres_ing.get(p["ingeniero_id"])
                    if nom_ing in matriz_prop_df.index:
                        p_ini = datetime.strptime(p["fecha_inicio"], "%Y-%m-%d")
                        p_fin = datetime.strptime(p["fecha_fin"], "%Y-%m-%d")
                        estado = p.get("estado", "Pendiente")
                        dia_aux = p_ini
                        
                        while dia_aux <= p_fin:
                            str_dia = dia_aux.strftime("%Y-%m-%d")
                            if str_dia in matriz_prop_df.columns:
                                emo, _, _ = obtener_estilo_motivo(p.get("motivo", "Otro"), estado)
                                matriz_prop_df.at[nom_ing, str_dia] = f"{emo} {estado[:4]}."
                            dia_aux += timedelta(days=1)

                matriz_prop_df.columns = nombres_cols_p
                st.dataframe(matriz_prop_df, use_container_width=True)
                
            else:
                cal_p = calendar.Calendar(firstweekday=0)
                semanas_p = cal_p.monthdatescalendar(año_p, mes_p)
                cols_dias_p = st.columns(7)
                for i, nombre_dia in enumerate(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]):
                    cols_dias_p[i].markdown(f"<div style='text-align: center; font-weight: bold; background-color: #f0f2f6; padding: 5px; border-radius: 5px;'>{nombre_dia}</div>", unsafe_allow_html=True)
                
                st.write("")
                for semana in semanas_p:
                    cols_semana = st.columns(7)
                    for i, dia in enumerate(semana):
                        with cols_semana[i]:
                            if dia.month == mes_p:
                                str_dia = dia.strftime("%Y-%m-%d")
                                
                                if str_dia in festivos_colombia_lista:
                                    st.markdown(f"**{dia.day}** 🎊")
                                else:
                                    st.markdown(f"**{dia.day}**")
                                    
                                propuestas_hoy = [
                                    p for p in lista_propuestas 
                                    if datetime.strptime(p["fecha_inicio"], "%Y-%m-%d").date() <= dia <= datetime.strptime(p["fecha_fin"], "%Y-%m-%d").date()
                                ]
                                
                                for p in propuestas_hoy:
                                    motivo = p.get('motivo', 'Otro')
                                    estado = p.get('estado', 'Pendiente')
                                    emo, bg_col, txt_col = obtener_estilo_motivo(motivo, estado)
                                    txt_estado = estado[:4] + "."
                                    st.markdown(f"<div style='background-color: {bg_col}; color: {txt_col}; padding: 4px; border-radius: 4px; font-size: 11px; margin-bottom: 2px;' title='{motivo} - {estado}'>{emo} {dict_nombres_ing.get(p['ingeniero_id'], '')} ({txt_estado})</div>", unsafe_allow_html=True)
                                
                                st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<span style='color: #ccc;'>{dia.day}</span>", unsafe_allow_html=True)
                    st.divider()
            
            st.markdown("<small><b>Leyenda:</b> ⏳ Pendiente | 🌴 Aprobado | ❌ Rechazado</small>", unsafe_allow_html=True)

# ==========================================
# 🛑 BLOQUE ADMINISTRATIVO
# ==========================================
elif "Gestión de Equipo" in pestana_actual and st.session_state.role == "admin":
    st.header("👥 Gestión de Contratos y Equipo")
    col_form, col_tabla = st.columns([1, 2])
    
    with col_form:
        st.subheader("Registrar Profesional")
        nombre = st.text_input("Nombre Completo:").strip().upper()
        correo_nuevo = st.text_input("📧 Correo Corporativo (Para notificaciones):").strip()
        rol = st.selectbox("Rol Fijo:", ["Ingeniero (Líder/Apoyo)", "Supervisor"])
        permite_fds = st.radio("¿Turnos Fin de Semana?", [True, False], format_func=lambda x: "Sí" if x else "No (Restringido)")
        es_nuevo = st.radio("¿Es nuevo? (Prioridad Inducción)", [False, True], format_func=lambda x: "Sí" if x else "No")
        
        st.markdown("---")
        st.markdown("**Participación en Disponibilidades**")
        participa_disp = st.radio("¿Participa de las guardias?", [True, False], format_func=lambda x: "Sí, participa" if x else "No, Exento permanentemente", help="Si marcas No, el motor lo ignorará por completo.")
        
        st.markdown("---")
        st.markdown("**Vigencia en el Equipo**")
        f_ingreso = st.date_input("Fecha de Ingreso", FECHA_MIN, min_value=FECHA_MIN)
        
        tipo_contrato = st.radio("Tipo de Contrato:", ["Término Indefinido", "Caso Especial (Tiene fecha de salida)"])
        str_f_salida = str(st.date_input("Fecha de Salida", max(datetime.now().date() + timedelta(days=30), FECHA_MIN), min_value=FECHA_MIN)) if "Caso" in tipo_contrato else "2099-12-31"
        
        if st.button("💾 Guardar Trabajador", use_container_width=True):
            if nombre:
                try:
                    supabase.table("ingenieros").insert({
                        "nombre": nombre, "correo": correo_nuevo, "rol": rol, "permite_fin_semana": permite_fds, "es_nuevo": es_nuevo,
                        "fecha_ingreso": str(f_ingreso), "fecha_salida": str_f_salida,
                        "exento_disponibilidad": not participa_disp
                    }).execute()
                    st.success("✅ Guardado correctamente.")
                    st.rerun()
                except Exception as e: 
                    st.error(f"Error técnico. Detalle: {e}")
            else:
                st.error("⚠️ Por favor ingresa un nombre.")

    with col_tabla:
        st.subheader("Personal Activo y Vigencias")
        if len(lista_ingenieros) > 0:
            df_ing = pd.DataFrame(lista_ingenieros)
            if 'fecha_ingreso' not in df_ing.columns: df_ing['fecha_ingreso'] = "2026-01-01"
            if 'fecha_salida' not in df_ing.columns: df_ing['fecha_salida'] = "2099-12-31"
            if 'exento_disponibilidad' not in df_ing.columns: df_ing['exento_disponibilidad'] = False
            if 'correo' not in df_ing.columns: df_ing['correo'] = "Sin Correo"
            
            df_ing['Vigencia Hasta'] = df_ing['fecha_salida'].apply(lambda x: "Indefinido" if "2099" in str(x) else x)
            df_ing['Estado Operativo'] = df_ing['exento_disponibilidad'].apply(lambda x: "🚫 EXENTO" if x else "Activo")
            
            df_show = df_ing[["id", "nombre", "correo", "rol", "es_nuevo", "Estado Operativo", "Vigencia Hasta"]].copy()
            df_show.columns = ["ID", "Nombre", "Correo", "Rol", "¿Nuevo?", "Estado", "Salida"]
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            st.subheader("✏️ Actualizar Correo de Profesional")
            st.caption("Modifica el correo de alguien que ya está registrado sin tener que eliminarlo.")
            ing_a_editar = st.selectbox("Selecciona al profesional:", lista_ingenieros, format_func=lambda x: f"{x['id']} - {x['nombre']}", key="edit_correo")
            nuevo_correo = st.text_input("Nuevo Correo:", value=ing_a_editar.get("correo", "") if ing_a_editar else "")
            
            if st.button("🔄 Actualizar Correo"):
                try:
                    supabase.table("ingenieros").update({"correo": nuevo_correo}).eq("id", ing_a_editar["id"]).execute()
                    st.success(f"✅ Correo actualizado para {ing_a_editar['nombre']}.")
                    st.rerun()
                except Exception as e: st.error(f"Error al actualizar: {e}")
                
            st.markdown("---")

            col_b1, col_b2 = st.columns(2)
            
            with col_b1:
                st.subheader("🎓 Quitar estado 'Nuevo'")
                st.caption("Si un trabajador ya superó su inducción, retira su etiqueta aquí.")
                nuevos_lista = [i for i in lista_ingenieros if i.get("es_nuevo", False)]
                if nuevos_lista:
                    ing_a_actualizar = st.selectbox("Selecciona al profesional:", nuevos_lista, format_func=lambda x: f"{x['id']} - {x['nombre']}")
                    if st.button("🔄 Cambiar a Antiguo"):
                        try:
                            supabase.table("ingenieros").update({"es_nuevo": False}).eq("id", ing_a_actualizar["id"]).execute()
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

            with col_b2:
                st.subheader("❌ Eliminar Trabajador")
                st.caption("Borra definitivamente a una persona.")
                ing_a_eliminar = st.selectbox("Selecciona para eliminar:", lista_ingenieros, format_func=lambda x: f"{x['id']} - {x['nombre']}")
                if st.button("🗑️ Eliminar permanentemente"):
                    if ing_a_eliminar:
                        try:
                            supabase.table("vacaciones").delete().eq("ingeniero_id", ing_a_eliminar["id"]).execute()
                            supabase.table("propuestas_ausentismos").delete().eq("ingeniero_id", ing_a_eliminar["id"]).execute()
                            supabase.table("asignaciones").delete().eq("ingeniero_id", ing_a_eliminar["id"]).execute()
                            supabase.table("ingenieros").delete().eq("id", ing_a_eliminar["id"]).execute()
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

elif "Panel RRHH" in pestana_actual and st.session_state.role == "admin":
    st.header("🌴 Panel de RRHH: Ingreso Directo de Ausentismos")
    st.markdown("Usa esta pestaña sólo para subir vacaciones antiguas o incapacidades directas sin pasar por el portal de propuestas.")
    if len(lista_ingenieros) > 0:
        col_v1, col_v2 = st.columns([1, 2])
        with col_v1:
            with st.form("form_vac"):
                ing_ausente = st.selectbox("Profesional:", lista_ingenieros, format_func=lambda x: x["nombre"])
                motivo_ausentismo = st.selectbox("Tipo de Ausentismo:", ["Vacaciones", "Incapacidad Médica", "Permiso Empresa", "Licencia", "Festivo", "Otro"])
                fechas = st.date_input("Rango de Fechas:", [], min_value=FECHA_MIN)
                
                if st.form_submit_button("📅 Bloquear Fechas") and len(fechas) == 2:
                    supabase.table("vacaciones").insert({"ingeniero_id": ing_ausente["id"], "fecha_inicio": str(fechas[0]), "fecha_fin": str(fechas[1]), "motivo": motivo_ausentismo}).execute()
                    st.rerun()
                        
        with col_v2:
            if len(lista_vacaciones) > 0:
                df_vac = pd.DataFrame(lista_vacaciones)
                df_vac['Profesional'] = df_vac['ingeniero_id'].map(dict_nombres_ing)
                df_show_vac = df_vac[["id", "Profesional", "motivo", "fecha_inicio", "fecha_fin"]].sort_values(by="fecha_inicio", ascending=False)
                df_show_vac.columns = ["ID", "Profesional", "Motivo", "Fecha Inicio", "Fecha Fin"]
                
                st.dataframe(df_show_vac, hide_index=True, use_container_width=True)
                
                vac_a_eliminar = st.selectbox("Selecciona registro oficial a eliminar:", lista_vacaciones, format_func=lambda x: f"ID {x['id']} - {dict_nombres_ing.get(x['ingeniero_id'])}")
                if st.button("❌ Eliminar Registro Oficial") and vac_a_eliminar:
                    supabase.table("vacaciones").delete().eq("id", vac_a_eliminar["id"]).execute()
                    st.rerun()

elif "Motor Algorítmico" in pestana_actual and st.session_state.role == "admin":
    st.header("⚙️ Motor Algorítmico de Equidad por Jornadas Operativas")
    
    lista_ingenieros_motor = [i for i in lista_ingenieros if not i.get("exento_disponibilidad", False)]
    
    if len(lista_ingenieros_motor) > 0:
        col_a1, col_a2 = st.columns(2)
        f_inicio_calc = col_a1.date_input("Fecha Inicio Semestre", max(datetime.now().date(), FECHA_MIN), min_value=FECHA_MIN)
        f_fin_calc = col_a2.date_input("Fecha Fin Semestre", max(datetime.now().date() + timedelta(days=180), FECHA_MIN), min_value=FECHA_MIN)

        st.markdown("---")
        st.subheader("🧹 Herramientas de Limpieza (Rango Seleccionado)")
        col_cl1, col_cl2 = st.columns(2)
        with col_cl1:
            if st.button("🗑️ Borrar TODO (Dejar en blanco)", use_container_width=True):
                with st.spinner("Borrando todas las asignaciones..."):
                    try:
                        asigs_todas = supabase.table("asignaciones").select("id, fecha").execute().data
                        ids_a_borrar_todo = [a["id"] for a in asigs_todas if f_inicio_calc <= datetime.strptime(a["fecha"], "%Y-%m-%d").date() <= f_fin_calc]
                        if ids_a_borrar_todo:
                            for i in range(0, len(ids_a_borrar_todo), 100):
                                supabase.table("asignaciones").delete().in_("id", ids_a_borrar_todo[i:i+100]).execute()
                            st.success(f"✅ Se borraron {len(ids_a_borrar_todo)} turnos. El calendario quedó en blanco.")
                            st.rerun()
                    except Exception as e: st.error(f"Error procesando el borrado: {e}")

        with col_cl2:
            if st.button("🧹 Borrar solo Automáticos (Mantener Manuales)", use_container_width=True):
                with st.spinner("Borrando turnos generados automáticamente..."):
                    try:
                        asigs_todas = supabase.table("asignaciones").select("id, fecha, tipo_dia").execute().data
                        ids_a_borrar_auto = [a["id"] for a in asigs_todas if f_inicio_calc <= datetime.strptime(a["fecha"], "%Y-%m-%d").date() <= f_fin_calc and "MANUAL" not in a.get("tipo_dia", "").upper()]
                        if ids_a_borrar_auto:
                            for i in range(0, len(ids_a_borrar_auto), 100):
                                supabase.table("asignaciones").delete().in_("id", ids_a_borrar_auto[i:i+100]).execute()
                            st.success(f"✅ Se borraron {len(ids_a_borrar_auto)} turnos automáticos.")
                            st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

        st.markdown("---")
        st.subheader("Opciones de Ejecución del Algoritmo")
        modo_ejecucion = st.radio(
            "Selecciona qué debe hacer el algoritmo con los turnos existentes en ese rango de fechas:", 
            [
                "🛠️ Mantener Manuales y Recalcular Automáticos (Recomendado)",
                "🧩 Rellenar Huecos (Mantiene TODOS los turnos actuales y solo llena donde falta alguien)",
                "⚠️ Sobrescribir TODO (Borra todos los turnos del rango y calcula desde cero)"
            ]
        )

        if st.button("🚀 Optimizar y Asignar por Jornadas", use_container_width=True):
            with st.spinner("Construyendo jornadas y aplicando reglas..."):
                try:
                    # 1. RECUPERAR HISTORIAL Y FILTRAR
                    asigs_historicas = supabase.table("asignaciones").select("*").execute().data
                    ids_to_delete = []
                    
                    for a in asigs_historicas:
                        fecha_a = datetime.strptime(a["fecha"], "%Y-%m-%d").date()
                        if f_inicio_calc <= fecha_a <= f_fin_calc:
                            if "🧩" in modo_ejecucion: pass
                            elif "🛠️" in modo_ejecucion:
                                if "MANUAL" not in a.get("tipo_dia", "").upper(): ids_to_delete.append(a["id"])
                            elif "⚠️" in modo_ejecucion: ids_to_delete.append(a["id"])
                                
                    if ids_to_delete:
                        for i in range(0, len(ids_to_delete), 100):
                            supabase.table("asignaciones").delete().in_("id", ids_to_delete[i:i+100]).execute()
                    
                    asigs_restantes = [a for a in asigs_historicas if a["id"] not in ids_to_delete]

                    # 2. CALCULAR BLOQUES DEL SEMESTRE
                    lunes_guia = f_inicio_calc - timedelta(days=f_inicio_calc.weekday())
                    bloques_validos = []
                    
                    while lunes_guia <= f_fin_calc:
                        es_lunes_actual_festivo = lunes_guia.strftime("%Y-%m-%d") in festivos_colombia_lista
                        lunes_proximo = lunes_guia + timedelta(days=7)
                        es_lunes_prox_festivo = lunes_proximo.strftime("%Y-%m-%d") in festivos_colombia_lista
                        
                        rango_despacho = [lunes_guia + timedelta(days=i) for i in range(5)]
                        if es_lunes_actual_festivo: 
                            rango_semana = [lunes_guia + timedelta(days=1), lunes_guia + timedelta(days=2), lunes_guia + timedelta(days=3)]
                        else: 
                            rango_semana = [lunes_guia, lunes_guia + timedelta(days=1), lunes_guia + timedelta(days=2), lunes_guia + timedelta(days=3)]
                        
                        rango_fds = [lunes_guia + timedelta(days=4), lunes_guia + timedelta(days=5), lunes_guia + timedelta(days=6)]
                        if es_lunes_prox_festivo: 
                            rango_fds.append(lunes_proximo)
                            
                        dias_d = [d for d in rango_despacho if f_inicio_calc <= d <= f_fin_calc]
                        if dias_d: bloques_validos.append({'tipo': 'DESPACHO', 'fechas': dias_d})
                            
                        dias_s = [d for d in rango_semana if f_inicio_calc <= d <= f_fin_calc]
                        if dias_s: bloques_validos.append({'tipo': 'SEMANA', 'fechas': dias_s})
                        
                        dias_f = [d for d in rango_fds if f_inicio_calc <= d <= f_fin_calc]
                        if dias_f: bloques_validos.append({'tipo': 'FDS', 'fechas': dias_f})
                            
                        lunes_guia = lunes_proximo

                    # 3. PRE-CALCULAR DATOS DE OPTIMIZACIÓN - VARIABLES TOTALMENTE SEPARADAS
                    conteo_disp = {ing["id"]: 0 for ing in lista_ingenieros_motor} 
                    conteo_desp = {ing["id"]: 0 for ing in lista_ingenieros_motor} 
                    conteo_tipo_bloque = {ing["id"]: {"SEMANA": 0, "FDS": 0, "DESPACHO": 0} for ing in lista_ingenieros_motor} 
                    conteo_roles_hist = {ing["id"]: {"Líder": 0, "Apoyo": 0, "Supervisor": 0, "Despacho": 0} for ing in lista_ingenieros_motor}
                    ultimo_tipo_guardia = {ing["id"]: "SEMANA" for ing in lista_ingenieros_motor} 
                    ultimo_rol_guardia = {ing["id"]: None for ing in lista_ingenieros_motor}
                    turnos_por_mes = {ing["id"]: {} for ing in lista_ingenieros_motor}
                    
                    def contar_bloques_fechas(lista_fechas_str):
                        if not lista_fechas_str: return 0
                        fechas_ordenadas = sorted([datetime.strptime(f, "%Y-%m-%d").date() for f in lista_fechas_str])
                        bloques = 1
                        for i in range(1, len(fechas_ordenadas)):
                            if (fechas_ordenadas[i] - fechas_ordenadas[i-1]).days > 1: bloques += 1
                        return bloques

                    for ing in lista_ingenieros_motor:
                        hist_disp = [a["fecha"] for a in asigs_historicas if a["ingeniero_id"] == ing["id"] and datetime.strptime(a["fecha"], "%Y-%m-%d").date() < f_inicio_calc and "DESPACHO" not in a.get("tipo_dia", "").upper()]
                        hist_desp = [a["fecha"] for a in asigs_historicas if a["ingeniero_id"] == ing["id"] and datetime.strptime(a["fecha"], "%Y-%m-%d").date() < f_inicio_calc and "DESPACHO" in a.get("tipo_dia", "").upper()]
                        man_disp = [a["fecha"] for a in asigs_restantes if a["ingeniero_id"] == ing["id"] and "MANUAL" in a.get("tipo_dia", "").upper() and "DESPACHO" not in a.get("tipo_dia", "").upper()]
                        man_desp = [a["fecha"] for a in asigs_restantes if a["ingeniero_id"] == ing["id"] and "MANUAL" in a.get("tipo_dia", "").upper() and "DESPACHO" in a.get("tipo_dia", "").upper()]

                        conteo_disp[ing["id"]] = contar_bloques_fechas(hist_disp) + contar_bloques_fechas(man_disp)
                        conteo_desp[ing["id"]] = contar_bloques_fechas(hist_desp) + contar_bloques_fechas(man_desp)

                        turnos_hist_all = sorted([a for a in asigs_historicas if a["ingeniero_id"] == ing["id"] and datetime.strptime(a["fecha"], "%Y-%m-%d").date() < f_inicio_calc], key=lambda x: datetime.strptime(x["fecha"], "%Y-%m-%d"))
                        turnos_man_futuros = sorted([a for a in asigs_restantes if a["ingeniero_id"] == ing["id"] and "MANUAL" in a.get("tipo_dia","").upper()], key=lambda x: datetime.strptime(x["fecha"], "%Y-%m-%d"))
                        all_relevant = turnos_hist_all + turnos_man_futuros
                        
                        for t in all_relevant:
                            mes_t = datetime.strptime(t["fecha"], "%Y-%m-%d").month
                            turnos_por_mes[ing["id"]][mes_t] = turnos_por_mes[ing["id"]].get(mes_t, 0) + 1
                            
                            tipo_str = t.get("tipo_dia", "").upper()
                            r_l = tipo_str.split("(")[-1].replace(")", "").strip()
                            if "DESPACHO" in r_l or "DESPACHO" in tipo_str:
                                conteo_roles_hist[ing["id"]]["Despacho"] += 1
                                conteo_tipo_bloque[ing["id"]]["DESPACHO"] += 1
                            else:
                                if "APOYO" in r_l: conteo_roles_hist[ing["id"]]["Apoyo"] += 1
                                elif "LÍDER" in r_l or "LIDER" in r_l: conteo_roles_hist[ing["id"]]["Líder"] += 1
                                elif "SUPERVISOR" in r_l: conteo_roles_hist[ing["id"]]["Supervisor"] += 1
                                
                                if "FDS" in tipo_str:
                                    ultimo_tipo_guardia[ing["id"]] = "FDS"
                                    conteo_tipo_bloque[ing["id"]]["FDS"] += 1
                                elif "SEMANA" in tipo_str:
                                    ultimo_tipo_guardia[ing["id"]] = "SEMANA"
                                    conteo_tipo_bloque[ing["id"]]["SEMANA"] += 1
                                    
                        for t in reversed(all_relevant):
                            ultimo_tipo_str = t.get("tipo_dia", "").upper()
                            if "DESPACHO" not in ultimo_tipo_str:
                                if "LÍDER" in ultimo_tipo_str or "LIDER" in ultimo_tipo_str: ultimo_rol_guardia[ing["id"]] = "Líder"
                                elif "APOYO" in ultimo_tipo_str: ultimo_rol_guardia[ing["id"]] = "Apoyo"
                                elif "SUPERVISOR" in ultimo_tipo_str: ultimo_rol_guardia[ing["id"]] = "Supervisor"
                                break
                    
                    vacaciones_por_ing = {ing["id"]: set() for ing in lista_ingenieros_motor}
                    for v in lista_vacaciones:
                        if v["ingeniero_id"] in vacaciones_por_ing:
                            v_ini = datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date()
                            v_fin = datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date()
                            delta = (v_fin - v_ini).days
                            for i in range(delta + 1):
                                vacaciones_por_ing[v["ingeniero_id"]].add(v_ini + timedelta(days=i))

                    registros_nuevos = []
                    
                    # 4. ITERAR SOBRE BLOQUES Y AUTOCOMPLETAR
                    for b in bloques_validos:
                        str_fechas_b = [d.strftime("%Y-%m-%d") for d in b['fechas']]
                        mes_bloque = b['fechas'][0].month
                        manuales_bloque = [a for a in asigs_restantes if a["fecha"] in str_fechas_b]
                        
                        roles_cubiertos_dia = {d: set() for d in b['fechas']}
                        ing_cubiertos = set()
                        
                        for m in manuales_bloque:
                            f_m = datetime.strptime(m["fecha"], "%Y-%m-%d").date()
                            if f_m in roles_cubiertos_dia:
                                if "(" in m["tipo_dia"]:
                                    rol = m["tipo_dia"].split("(")[-1].replace(")", "").strip()
                                    if "Despacho" in rol or "DESPACHO" in m["tipo_dia"]: rol = "Despacho"
                                    if "Apoyo" in rol and "1" not in rol and "2" not in rol: rol = "Apoyo 1"
                                    roles_cubiertos_dia[f_m].add(rol)
                                ing_cubiertos.add(m["ingeniero_id"])
                        
                            ing_m = m["ingeniero_id"]
                            if ing_m in ultimo_tipo_guardia:
                                if "DESPACHO" not in m["tipo_dia"].upper():
                                    ultimo_tipo_guardia[ing_m] = "FDS" if b['tipo'] == 'FDS' else "SEMANA"
                                    tipo_str = m["tipo_dia"].upper()
                                    if "LÍDER" in tipo_str or "LIDER" in tipo_str: ultimo_rol_guardia[ing_m] = "Líder"
                                    elif "APOYO" in tipo_str: ultimo_rol_guardia[ing_m] = "Apoyo"
                                    elif "SUPERVISOR" in tipo_str: ultimo_rol_guardia[ing_m] = "Supervisor"

                        roles_sup_necesarios, roles_ing_necesarios = [], []

                        if b['tipo'] == 'DESPACHO':
                            if any("Despacho" not in roles_cubiertos_dia[d] for d in b['fechas']): roles_ing_necesarios.append("Despacho")
                        elif b['tipo'] == 'SEMANA':
                            if any("Líder" not in roles_cubiertos_dia[d] for d in b['fechas']): roles_ing_necesarios.append("Líder")
                            if any("Apoyo 1" not in roles_cubiertos_dia[d] and "Apoyo 2" not in roles_cubiertos_dia[d] and "Apoyo" not in roles_cubiertos_dia[d] for d in b['fechas']): roles_ing_necesarios.append("Apoyo")
                        elif b['tipo'] == 'FDS':
                            if any("Supervisor" not in roles_cubiertos_dia[d] for d in b['fechas']): roles_sup_necesarios.append("Supervisor")
                            if any("Líder" not in roles_cubiertos_dia[d] for d in b['fechas']): roles_ing_necesarios.append("Líder")
                            
                            apoyos_faltantes_max = 0
                            for d in b['fechas']:
                                apoyos_dia = sum(1 for r in roles_cubiertos_dia[d] if "Apoyo" in r)
                                faltan = max(0, 2 - apoyos_dia)
                                if faltan > apoyos_faltantes_max: apoyos_faltantes_max = faltan
                            
                            if apoyos_faltantes_max == 2: roles_ing_necesarios.extend(["Apoyo 1", "Apoyo 2"])
                            elif apoyos_faltantes_max == 1: roles_ing_necesarios.append("Apoyo 2")

                        if not roles_sup_necesarios and not roles_ing_necesarios: continue

                        es_fds = b['tipo'] == 'FDS'
                        es_critico = any((d.month == 12 and d.day in [24, 25, 31]) or (d.month == 1 and d.day == 1) for d in b['fechas'])
                        
                        elegibles_ing_strict, elegibles_sup_strict = [], []
                        elegibles_ing_backup, elegibles_sup_backup = [], [] 
                        
                        for ing in lista_ingenieros_motor:
                            if ing["id"] in ing_cubiertos: continue 

                            es_supervisor = "SUPERVISOR" in ing.get("rol", "").upper()
                            if b['tipo'] != 'FDS' and es_supervisor: continue

                            ingreso = datetime.strptime(ing.get("fecha_ingreso", "2026-01-01")[:10], "%Y-%m-%d").date()
                            salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                            if not all(ingreso <= d <= salida for d in b['fechas']): continue
                            
                            # Si es FDS y está restringido, se ignora por completo para este bloque.
                            # Pero como filtramos los restringidos de FDS, priorizaremos su asignación en SEMANA y DESPACHO más abajo.
                            if es_fds and not ing.get("permite_fin_semana", True): continue
                            
                            fechas_disp_ing = [
                                datetime.strptime(a["fecha"], "%Y-%m-%d").date() 
                                for a in asigs_restantes if a["ingeniero_id"] == ing["id"] and "DESPACHO" not in a.get("tipo_dia", "").upper()
                            ] + [
                                datetime.strptime(r["fecha"], "%Y-%m-%d").date() 
                                for r in registros_nuevos if r["ingeniero_id"] == ing["id"] and "DESPACHO" not in r.get("tipo_dia", "").upper()
                            ]
                            
                            fechas_desp_ing = [
                                datetime.strptime(a["fecha"], "%Y-%m-%d").date() 
                                for a in asigs_restantes if a["ingeniero_id"] == ing["id"] and "DESPACHO" in a.get("tipo_dia", "").upper()
                            ] + [
                                datetime.strptime(r["fecha"], "%Y-%m-%d").date() 
                                for r in registros_nuevos if r["ingeniero_id"] == ing["id"] and "DESPACHO" in r.get("tipo_dia", "").upper()
                            ]

                            # Fail-safe turnos manuales pisados
                            if any(f_b in fechas_disp_ing or f_b in fechas_desp_ing for f_b in b['fechas']): continue 
                            
                            dias_vac = vacaciones_por_ing[ing["id"]]
                            fechas_bloque = b['fechas']
                            en_vacaciones_directas = any(d in dias_vac for d in fechas_bloque)
                            dia_antes = fechas_bloque[0] - timedelta(days=1)
                            dia_despues = fechas_bloque[-1] + timedelta(days=1)
                            es_sandwich_antes = (dia_antes.strftime("%Y-%m-%d") in festivos_colombia_lista) and ((dia_antes - timedelta(days=1)) in dias_vac)
                            es_sandwich_despues = (dia_despues.strftime("%Y-%m-%d") in festivos_colombia_lista) and ((dia_despues + timedelta(days=1)) in dias_vac)

                            if en_vacaciones_directas or (dia_antes in dias_vac) or (dia_despues in dias_vac) or es_sandwich_antes or es_sandwich_despues:
                                continue 

                            # --- CIERRES ESTRICTOS DE INVIABILIDAD (MUROS INFRANQUEABLES) ---
                            min_dist_disp = min([abs((f_b - f_i).days) for f_b in b['fechas'] for f_i in fechas_disp_ing], default=999)
                            min_dist_desp = min([abs((f_b - f_i).days) for f_b in b['fechas'] for f_i in fechas_desp_ing], default=999)

                            rompe_regla_soft = False
                            es_inviable = False

                            if b['tipo'] == 'DESPACHO':
                                if min_dist_desp <= 7: es_inviable = True # Jamás Despachos seguidos
                                if min_dist_disp <= 7: es_inviable = True # Jamás Despacho pisando Guardia
                            else: # FDS o SEMANA
                                if min_dist_disp <= 7: es_inviable = True # Jamás Guardias seguidas
                                if min_dist_desp <= 7: es_inviable = True # Jamás Guardia pisando Despacho
                                
                                # Si pasa el muro infranqueable, evaluamos el Cooldown suave de Guardia
                                if min_dist_disp <= 20: 
                                    rompe_regla_soft = True

                                # Restricción de No Repetir FDS de seguido (A menos que se deba hacer excepción)
                                if es_fds and ultimo_tipo_guardia.get(ing["id"]) == "FDS" and not es_supervisor:
                                    rompe_regla_soft = True

                            # Exclusión absoluta: Si rompe un muro infranqueable, no entra ni como suplente.
                            if es_inviable: continue 

                            ing_copia = ing.copy()
                            ing_copia['_is_backup'] = rompe_regla_soft

                            if rompe_regla_soft:
                                if es_supervisor: elegibles_sup_backup.append(ing_copia)
                                else: elegibles_ing_backup.append(ing_copia)
                            else:
                                if es_supervisor: elegibles_sup_strict.append(ing_copia)
                                else: elegibles_ing_strict.append(ing_copia)
                                
                        # Unificamos los pools garantizando con la key '_is_backup' que los suplentes queden al final.
                        elegibles_sup = elegibles_sup_strict + elegibles_sup_backup
                        elegibles_para_ing = elegibles_ing_strict + elegibles_ing_backup
                        
                        elegidos_sup = []
                        if es_fds and roles_sup_necesarios:
                            # Los supervisores también respetan su prioridad (Strict primero, luego backup)
                            elegibles_sup.sort(key=lambda x: (x.get('_is_backup', False), conteo_disp[x["id"]]))
                            if elegibles_sup:
                                sup_seleccionado = elegibles_sup.pop(0)
                                elegidos_sup.append(sup_seleccionado)
                                conteo_roles_hist[sup_seleccionado["id"]]["Supervisor"] += 1
                                ultimo_rol_guardia[sup_seleccionado["id"]] = "Supervisor"
                                elegibles_para_ing.extend(elegibles_sup) # El resto de supervisores pueden ir como apoyo si hacen falta

                        asignaciones_finales_bloque = []
                        pool_roles_asignar = roles_ing_necesarios.copy()
                        
                        # --- ASIGNACIÓN 1: DESPACHO ---
                        # Equilibrado puro por conteo de despachos y garantizando 1 al mes para los restringidos
                        if "Despacho" in pool_roles_asignar:
                            elegibles_para_ing.sort(key=lambda x: (
                                x.get('_is_backup', False),
                                conteo_desp[x["id"]], 
                                0 if turnos_por_mes[x["id"]].get(mes_bloque, 0) == 0 and not x.get("permite_fin_semana", True) else 1
                            ))
                            if elegibles_para_ing:
                                ing_seleccionado = elegibles_para_ing.pop(0)
                                conteo_roles_hist[ing_seleccionado["id"]]["Despacho"] += 1
                                asignaciones_finales_bloque.append((ing_seleccionado, "Despacho"))
                                pool_roles_asignar.remove("Despacho")

                        # --- ASIGNACIÓN 2: LÍDER ---
                        # Jamás un líder de seguido. Ni siquiera como backup.
                        if "Líder" in pool_roles_asignar:
                            candidatos_lider = [x for x in elegibles_para_ing if "SUPERVISOR" not in x.get("rol", "").upper() and ultimo_rol_guardia.get(x["id"]) != "Líder"]
                            if candidatos_lider:
                                candidatos_lider.sort(key=lambda x: (
                                    x.get('_is_backup', False),
                                    0 if turnos_por_mes[x["id"]].get(mes_bloque, 0) == 0 and not x.get("permite_fin_semana", True) else 1,
                                    conteo_disp[x["id"]],
                                    1 if x.get("es_nuevo", False) else 0, # Los nuevos son evadidos para ser Líder
                                    conteo_roles_hist[x["id"]]["Líder"]
                                ))
                                ing_seleccionado = candidatos_lider[0]
                                elegibles_para_ing = [x for x in elegibles_para_ing if x["id"] != ing_seleccionado["id"]]
                                conteo_roles_hist[ing_seleccionado["id"]]["Líder"] += 1
                                ultimo_rol_guardia[ing_seleccionado["id"]] = "Líder"
                                asignaciones_finales_bloque.append((ing_seleccionado, "Líder"))
                                pool_roles_asignar.remove("Líder")

                        # --- ASIGNACIÓN 3: APOYOS ---
                        for r_necesario in [r for r in pool_roles_asignar if "Apoyo" in r]:
                            if elegibles_para_ing:
                                elegibles_para_ing.sort(key=lambda x: (
                                    x.get('_is_backup', False),
                                    0 if turnos_por_mes[x["id"]].get(mes_bloque, 0) == 0 and not x.get("permite_fin_semana", True) else 1,
                                    conteo_disp[x["id"]],
                                    0 if x.get("es_nuevo", False) else 1, # Los nuevos son priorizados para Apoyo
                                    conteo_roles_hist[x["id"]]["Apoyo"]
                                ))
                                ing_seleccionado = elegibles_para_ing.pop(0)
                                conteo_roles_hist[ing_seleccionado["id"]]["Apoyo"] += 1
                                ultimo_rol_guardia[ing_seleccionado["id"]] = "Apoyo"
                                asignaciones_finales_bloque.append((ing_seleccionado, r_necesario))
                        
                        # --- GUARDAR BLOQUE EN BBDD ---
                        for sup in elegidos_sup:
                            conteo_disp[sup["id"]] += 1
                            conteo_tipo_bloque[sup["id"]]["FDS"] += 1
                            turnos_por_mes[sup["id"]][mes_bloque] = turnos_por_mes[sup["id"]].get(mes_bloque, 0) + 1
                            ultimo_tipo_guardia[sup["id"]] = "FDS"
                            for dia in b['fechas']: 
                                if "Supervisor" not in roles_cubiertos_dia[dia]:
                                    registros_nuevos.append({"fecha": str(dia), "ingeniero_id": sup["id"], "tipo_dia": f"FDS (Supervisor)"})
                                    roles_cubiertos_dia[dia].add("Supervisor")

                        for ing, rol_asignado in asignaciones_finales_bloque:
                            turnos_por_mes[ing["id"]][mes_bloque] = turnos_por_mes[ing["id"]].get(mes_bloque, 0) + 1
                            
                            if "Despacho" in rol_asignado:
                                conteo_desp[ing["id"]] += 1
                            else:
                                conteo_disp[ing["id"]] += 1
                                ultimo_tipo_guardia[ing["id"]] = "FDS" if b['tipo'] == 'FDS' else "SEMANA" 
                                
                            conteo_tipo_bloque[ing["id"]][b['tipo']] += 1
                            
                            for dia in b['fechas']: 
                                debe_insertar = False
                                if "Despacho" in rol_asignado and "Despacho" not in roles_cubiertos_dia[dia]: debe_insertar = True
                                elif "Líder" in rol_asignado and "Líder" not in roles_cubiertos_dia[dia]: debe_insertar = True
                                elif "Apoyo" in rol_asignado:
                                    apoyos_dia = sum(1 for r in roles_cubiertos_dia[dia] if "Apoyo" in r)
                                    if apoyos_dia < 2: debe_insertar = True
                                
                                if debe_insertar:
                                    registros_nuevos.append({"fecha": str(dia), "ingeniero_id": ing["id"], "tipo_dia": f"{b['tipo']} ({rol_asignado})"})
                                    roles_cubiertos_dia[dia].add(rol_asignado)
                    
                    if registros_nuevos:
                        supabase.table("asignaciones").insert(registros_nuevos).execute()
                        st.success("✅ ¡Optimización completada garantizando reglas fusionadas, equilibrio en despachos y muros infranqueables absolutos!")
                        st.balloons()
                        st.rerun()
                    elif modo_ejecucion != "⚠️ Sobrescribir TODO (Borra todos los turnos del rango y calcula desde cero)":
                        st.info("No se encontraron jornadas vacías para asignar en este rango.")
                        
                except Exception as e:
                    st.error(f"Error procesando el motor: {e}")

elif "Asignaciones Manuales" in pestana_actual and st.session_state.role == "admin":
    st.header("🔄 Asignaciones y Relevos Manuales")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("➕ Agregar Turno Manual")
        rango_manual = st.date_input("Rango de fechas a asignar:", [], min_value=FECHA_MIN)
        ing_manual = st.selectbox("Profesional:", lista_ingenieros, format_func=lambda x: f"{x['nombre']}", key="ing_man")
        rol_manual = st.selectbox("Rol en el turno:", ["Líder", "Apoyo", "Apoyo 1", "Apoyo 2", "Supervisor", "Despacho 6 AM"])
        if st.button("💾 Guardar Asignación Manual", use_container_width=True):
            if len(rango_manual) > 0:
                try:
                    dia_aux = rango_manual[0]
                    while dia_aux <= rango_manual[-1]:
                        str_d = str(dia_aux)
                        existe = supabase.table("asignaciones").select("id").eq("fecha", str_d).eq("ingeniero_id", ing_manual["id"]).execute().data
                        if existe: supabase.table("asignaciones").update({"tipo_dia": f"MANUAL ({rol_manual})"}).eq("id", existe[0]["id"]).execute()
                        else: supabase.table("asignaciones").insert({"fecha": str_d, "ingeniero_id": ing_manual["id"], "tipo_dia": f"MANUAL ({rol_manual})"}).execute()
                        dia_aux += timedelta(days=1)
                    st.success("✅ Turnos manuales gestionados.")
                    st.rerun()
                except Exception as e: st.error(f"Error técnico: {e}")
            else: st.error("⚠️ Selecciona al menos una fecha.")
    
    with col_r2:
        st.subheader("🔄 Relevo o Cancelación por Día")
        if len(lista_asignaciones) > 0:
            fecha_relevo = st.date_input("1. Selecciona la fecha:", min_value=FECHA_MIN)
            turnos_dia = [a for a in lista_asignaciones if a["fecha"] == str(fecha_relevo)]
            if turnos_dia:
                turno_sel = st.selectbox("2. Turno a modificar:", [f"{t['id']} - {dict_nombres_ing.get(t['ingeniero_id'])} ({t['tipo_dia']})" for t in turnos_dia])
                id_asig = int(turno_sel.split("-")[0].strip())
                nuevo_ing = st.selectbox("Quién toma el relevo:", lista_ingenieros, format_func=lambda x: x['nombre'])
                
                if st.button("🔄 Ejecutar Relevo"):
                    try:
                        ocupado = supabase.table("asignaciones").select("id").eq("fecha", str(fecha_relevo)).eq("ingeniero_id", nuevo_ing["id"]).execute().data
                        if ocupado: st.error(f"⚠️ {nuevo_ing['nombre']} ya tiene un turno ese día.")
                        else:
                            supabase.table("asignaciones").update({"ingeniero_id": nuevo_ing["id"]}).eq("id", id_asig).execute()
                            st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
                
                if st.button("❌ Cancelar Turno"):
                    try:
                        supabase.table("asignaciones").delete().eq("id", id_asig).execute()
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader("🌅 Relevo / Cancelación por Rango de Fechas")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        rango_mod = st.date_input("1. Rango de Fechas del bloque:", [], min_value=FECHA_MIN, key="rango_masivo")
        if len(rango_mod) == 2:
            turnos_en_rango = [a for a in lista_asignaciones if rango_mod[0] <= datetime.strptime(a['fecha'], "%Y-%m-%d").date() <= rango_mod[1]]
            if turnos_en_rango:
                ing_a_reemplazar = st.selectbox("2. Profesional a retirar:", list(set([a['ingeniero_id'] for a in turnos_en_rango])), format_func=lambda x: dict_nombres_ing.get(x, 'Desconocido'))
                ids_objetivo = [a['id'] for a in turnos_en_rango if a['ingeniero_id'] == ing_a_reemplazar]
                
    with col_b2:
        if len(rango_mod) == 2 and turnos_en_rango:
            st.info(f"Se detectaron **{len(ids_objetivo)}** días asignados.")
            ing_relevo_masivo = st.selectbox("3. Profesional de relevo:", lista_ingenieros, format_func=lambda x: f"{x['nombre']}")
            if st.button("🔄 Ejecutar Relevo de Bloque", use_container_width=True):
                try:
                    for id_t in ids_objetivo: supabase.table("asignaciones").update({"ingeniero_id": ing_relevo_masivo["id"]}).eq("id", id_t).execute()
                    st.success("✅ ¡Bloque relevado!")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
            if st.button("❌ Eliminar Bloque", use_container_width=True):
                try:
                    for i in range(0, len(ids_objetivo), 100): supabase.table("asignaciones").delete().in_("id", ids_objetivo[i:i+100]).execute()
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
