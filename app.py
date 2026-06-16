import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar
import plotly.express as px
from supabase import create_client, Client

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
# 👨‍💻 BARRA LATERAL (CRÉDITOS Y FESTIVOS GLOBALES)
# ==========================================
with st.sidebar:
    st.markdown("### ⚡ ENEL Colombia")
    st.markdown("Sistema de Gestión de Disponibilidades y Equidad Operativa.")
    st.markdown("---")
    
    with st.expander("📆 Configuración de Festivos", expanded=False):
        st.caption("Estos lunes festivos se usarán visualmente y en el motor de jornadas.")
        str_festivos_default = (
            "2026-01-12, 2026-03-23, 2026-05-18, 2026-06-08, 2026-06-15, 2026-06-29, 2026-07-20, 2026-08-17, 2026-10-12, 2026-11-02, 2026-11-16, "
            "2027-01-11, 2027-03-22, 2027-05-10, 2027-05-31, 2027-06-07, 2027-07-05, 2027-08-16, 2027-10-18, 2027-11-01, 2027-11-15, "
            "2028-01-10, 2028-03-20, 2028-05-29, 2028-06-19, 2028-06-26, 2028-07-03, 2028-08-21, 2028-10-16, 2028-11-06, 2028-11-13, "
            "2029-01-08, 2029-03-19, 2029-05-14, 2029-06-04, 2029-06-11, 2029-07-02, 2029-08-20, 2029-10-15, 2029-11-05, 2029-11-12, "
            "2030-01-07, 2030-03-25, 2030-06-03, 2030-06-24, 2030-07-01, 2030-08-19, 2030-10-14, 2030-11-04, 2030-11-11"
        )
        str_festivos = st.text_area("Lista de Lunes Festivos (AAAA-MM-DD)", str_festivos_default, height=150)
        festivos_lunes_lista = [f.strip() for f in str_festivos.split(",") if f.strip()]

    st.markdown("---")
    st.markdown("**Desarrollado y mantenido por:**")
    st.markdown("👨‍💻 **Sergio Cutiva**")
    st.markdown("📧 *sergio.cutiva@enel.com*")
    st.markdown("---")
    st.caption("Versión 3.0 | Estética y Lógica Avanzada")

# ==========================================
# 🛠️ FUNCIONES AUXILIARES Y ESTÉTICA
# ==========================================
def obtener_ingenieros(): return supabase.table("ingenieros").select("*").execute().data
def obtener_vacaciones(): return supabase.table("vacaciones").select("*").execute().data
def obtener_asignaciones(): return supabase.table("asignaciones").select("*").execute().data

def obtener_estilo_motivo(motivo):
    # Devuelve: (Emoji, Color_Fondo, Color_Texto)
    estilos = {
        "Vacaciones": ("🌴", "#e0f7fa", "#006064"),
        "Incapacidad Médica": ("🤒", "#ffebee", "#c62828"),
        "Permiso Empresa": ("🏢", "#f3e5f5", "#6a1b9a"),
        "Licencia": ("📜", "#e8f5e9", "#2e7d32"),
        "Otro": ("⚠️", "#fff8e1", "#ff8f00")
    }
    return estilos.get(motivo, ("⚠️", "#fff8e1", "#ff8f00"))

def obtener_estilo_rol(tipo_dia, rol_mostrar):
    # Devuelve: (Emoji, Color_Fondo, Color_Texto)
    if "MANUAL" in tipo_dia.upper(): return ("📌", "#ffe0b2", "#e65100")
    if "Líder" in rol_mostrar: return ("👑", "#e3f2fd", "#1565c0")
    if "Apoyo" in rol_mostrar: return ("🤝", "#e8f5e9", "#2e7d32")
    if "Supervisor" in rol_mostrar: return ("🛡️", "#fff3e0", "#e65100")
    return ("⚡", "#f3e5f5", "#6a1b9a")

# ==========================================
# ⚡ INTERFAZ PRINCIPAL
# ==========================================
FECHA_MIN = date(2026, 1, 1)

st.title("⚡ Sistema de Asignación de Disponibilidades")
st.markdown("Matriz de control por jornadas, ausentismos y equidad operativa.")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📅 Calendario Operativo", 
    "👥 Gestión de Equipo", 
    "🌴 Ausentismos", 
    "⚙️ Motor Algorítmico",
    "📊 Dashboard",
    "🔄 Asignaciones Manuales"
])

lista_ingenieros = obtener_ingenieros()
lista_vacaciones = obtener_vacaciones()
lista_asignaciones = obtener_asignaciones()

dict_nombres_ing = {ing["id"]: ing["nombre"] for ing in lista_ingenieros}

# ==========================================
# 📅 PESTAÑA 1: CALENDARIO MATRIZ E INTERACTIVO
# ==========================================
with tab1:
    st.header("🗓️ Visualización de Disponibilidad")
    
    with st.expander("📖 **¿Cómo se asignan los turnos? (Reglas de Transparencia)**"):
        st.markdown("""
        El motor algorítmico asigna los turnos automáticamente basándose en las siguientes reglas para garantizar total equidad:
        * **Jornadas Bloqueadas:** No se asigna por día individual. Se asigna un bloque de *Lunes a Jueves (SEMANA)* o de *Viernes a Domingo (FDS)*. Si el lunes es festivo, la jornada FDS se alarga hasta el Lunes.
        * **Roles por Jornada:** En Semana operan 2 ingenieros (1 Líder y 1 Apoyo). En FDS operan 4 personas (1 Líder, 2 Apoyos y 1 Supervisor).
        * **Flexibilidad FDS:** 🌟 Un Supervisor principal asume el rol de Supervisor, pero los Supervisores que no fueron elegidos en ese puesto entran a competir como "Apoyo" para blindar la operación.
        * **Equidad Proporcional:** El sistema busca siempre a la persona que tenga la **menor carga porcentual** (Turnos / Días de contrato).
        * **Descanso (Cooldown de 3 semanas):** ⏳ Nadie recibe un turno si no han pasado al menos **20 días** desde su última guardia (garantizando un descanso de mínimo 3 semanas completas).
        * **Excepciones Absolutas:** El motor jamás asigna turnos a personal en sus fechas de ausentismo.
        """)
    st.markdown("---")

    if len(lista_ingenieros) == 0:
        st.info("ℹ️ Comienza registrando al equipo en la pestaña 'Gestión de Equipo'.")
    else:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            año_sel = st.selectbox("Seleccionar Año:", [2026, 2027, 2028, 2029, 2030], index=0)
        with col_m2:
            mes_sel = st.selectbox("Seleccionar Mes:", list(range(1, 13)), format_func=lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][x - 1])
            
        st.markdown("---")
        tipo_vista = st.radio("Formato de visualización:", ["📅 Vista Calendario (Tipo Google Calendar)", "🗂️ Vista Matriz (Por Persona)"], horizontal=True)
        
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
                if str_fecha in festivos_lunes_lista: nombres_columnas_bonitas.append(f"🎊 {nombre_base}")
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
                            
                            if str_dia in festivos_lunes_lista:
                                st.markdown(f"**{dia.day}** 🎊 *(Festivo)*")
                            else:
                                st.markdown(f"**{dia.day}**")
                                
                            turnos_hoy = [a for a in lista_asignaciones if a["fecha"] == str_dia]
                            vacaciones_hoy = [v for v in lista_vacaciones if datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date() <= dia <= datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date()]
                            
                            # Cajas de Ausentismo
                            for v in vacaciones_hoy:
                                motivo = v.get('motivo', 'Otro')
                                emo, bg_col, txt_col = obtener_estilo_motivo(motivo)
                                st.markdown(f"<div style='background-color: {bg_col}; color: {txt_col}; padding: 4px; border-radius: 4px; font-size: 11px; margin-bottom: 2px;' title='{motivo}'>{emo} {dict_nombres_ing.get(v['ingeniero_id'], '')}</div>", unsafe_allow_html=True)
                            
                            # Cajas de Turno
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
# 👥 PESTAÑA 2: GESTIÓN DE EQUIPO
# ==========================================
with tab2:
    st.header("👥 Gestión de Contratos y Equipo")
    col_form, col_tabla = st.columns([1, 2])
    
    with col_form:
        st.subheader("Registrar Profesional")
        nombre = st.text_input("Nombre Completo:").strip().upper()
        rol = st.selectbox("Rol Fijo:", ["Ingeniero (Líder/Apoyo)", "Supervisor"])
        permite_fds = st.radio("¿Turnos Fin de Semana?", [True, False], format_func=lambda x: "Sí" if x else "No (Restringido)")
        es_nuevo = st.radio("¿Es nuevo? (Prioridad Diciembre)", [False, True], format_func=lambda x: "Sí" if x else "No")
        
        st.markdown("---")
        st.markdown("**Vigencia en el Equipo**")
        f_ingreso = st.date_input("Fecha de Ingreso", FECHA_MIN, min_value=FECHA_MIN)
        
        tipo_contrato = st.radio("Tipo de Contrato:", ["Término Indefinido", "Caso Especial (Tiene fecha de salida)"])
        if tipo_contrato == "Caso Especial (Tiene fecha de salida)":
            f_salida = st.date_input("Selecciona la Fecha de Salida programada", max(datetime.now().date() + timedelta(days=30), FECHA_MIN), min_value=FECHA_MIN)
            str_f_salida = str(f_salida)
        else:
            str_f_salida = "2099-12-31"
        
        if st.button("💾 Guardar Trabajador", use_container_width=True):
            if nombre:
                try:
                    supabase.table("ingenieros").insert({
                        "nombre": nombre, "rol": rol, "permite_fin_semana": permite_fds, "es_nuevo": es_nuevo,
                        "fecha_ingreso": str(f_ingreso), "fecha_salida": str_f_salida
                    }).execute()
                    st.success("✅ Guardado correctamente.")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
            else:
                st.error("⚠️ Por favor ingresa un nombre para el trabajador.")

    with col_tabla:
        st.subheader("Personal Activo y Vigencias")
        if len(lista_ingenieros) > 0:
            df_ing = pd.DataFrame(lista_ingenieros)
            if 'fecha_ingreso' not in df_ing.columns: df_ing['fecha_ingreso'] = "2026-01-01"
            if 'fecha_salida' not in df_ing.columns: df_ing['fecha_salida'] = "2099-12-31"
            
            df_ing['Vigencia Hasta'] = df_ing['fecha_salida'].apply(lambda x: "Indefinido" if "2099" in str(x) else x)
            df_show = df_ing[["id", "nombre", "rol", "es_nuevo", "fecha_ingreso", "Vigencia Hasta"]].copy()
            df_show.columns = ["ID", "Nombre", "Rol", "¿Nuevo?", "Ingreso", "Salida"]
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
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
                            st.success(f"✅ {ing_a_actualizar['nombre']} ahora es personal antiguo.")
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                else:
                    st.info("No hay personal con etiqueta de 'Nuevo'.")

            with col_b2:
                st.subheader("❌ Eliminar Trabajador")
                st.caption("Borra definitivamente a una persona de la base de datos.")
                ing_a_eliminar = st.selectbox("Selecciona para eliminar:", lista_ingenieros, format_func=lambda x: f"{x['id']} - {x['nombre']}")
                if st.button("🗑️ Eliminar permanentemente"):
                    if ing_a_eliminar:
                        try:
                            supabase.table("vacaciones").delete().eq("ingeniero_id", ing_a_eliminar["id"]).execute()
                            supabase.table("asignaciones").delete().eq("ingeniero_id", ing_a_eliminar["id"]).execute()
                            supabase.table("ingenieros").delete().eq("id", ing_a_eliminar["id"]).execute()
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 🌴 PESTAÑA 3: AUSENTISMOS Y MOTIVOS
# ==========================================
with tab3:
    st.header("🌴 Registro de Vacaciones y Ausentismos")
    if len(lista_ingenieros) > 0:
        col_v1, col_v2 = st.columns([1, 2])
        with col_v1:
            with st.form("form_vac"):
                ing_ausente = st.selectbox("Profesional:", lista_ingenieros, format_func=lambda x: x["nombre"])
                motivo_ausentismo = st.selectbox("Tipo de Ausentismo:", ["Vacaciones", "Incapacidad Médica", "Permiso Empresa", "Licencia", "Otro"])
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
                
                vac_a_eliminar = st.selectbox("Selecciona ausentismo a cancelar:", lista_vacaciones, format_func=lambda x: f"ID {x['id']} - {dict_nombres_ing.get(x['ingeniero_id'])}")
                if st.button("❌ Cancelar Ausentismo") and vac_a_eliminar:
                    supabase.table("vacaciones").delete().eq("id", vac_a_eliminar["id"]).execute()
                    st.rerun()

# ==========================================
# ⚙️ PESTAÑA 4: MOTOR ALGORÍTMICO POR JORNADAS
# ==========================================
with tab4:
    st.header("⚙️ Motor Algorítmico de Equidad por Jornadas Operativas")
    
    if len(lista_ingenieros) > 0:
        st.info("💡 **Inteligencia de Datos:** El motor respetará el Cooldown estricto de 3 semanas (20 días de gap) y las asignaciones manuales previas.")
        
        col_a1, col_a2 = st.columns(2)
        f_inicio_calc = col_a1.date_input("Fecha Inicio Semestre", max(datetime.now().date(), FECHA_MIN), min_value=FECHA_MIN)
        f_fin_calc = col_a2.date_input("Fecha Fin Semestre", max(datetime.now().date() + timedelta(days=180), FECHA_MIN), min_value=FECHA_MIN)

        if st.button("🚀 Optimizar y Asignar por Jornadas"):
            with st.spinner("Construyendo jornadas y seleccionando personal..."):
                try:
                    # 1. RECUPERAR TODO EL HISTORIAL PARA RESPETAR MANUALES
                    asigs_historicas = supabase.table("asignaciones").select("*").execute().data
                    
                    ids_to_delete = []
                    fechas_manuales_en_rango = set()
                    
                    for a in asigs_historicas:
                        fecha_a = datetime.strptime(a["fecha"], "%Y-%m-%d").date()
                        if f_inicio_calc <= fecha_a <= f_fin_calc:
                            if "MANUAL" in a.get("tipo_dia", "").upper():
                                fechas_manuales_en_rango.add(a["fecha"])
                            else:
                                ids_to_delete.append(a["id"])

                    # Borrar solo las automáticas previas en el rango
                    for i in range(0, len(ids_to_delete), 100):
                        supabase.table("asignaciones").delete().in_("id", ids_to_delete[i:i+100]).execute()
                    
                    asigs_restantes = [a for a in asigs_historicas if a["id"] not in ids_to_delete]

                    lunes_guia = f_inicio_calc - timedelta(days=f_inicio_calc.weekday())
                    bloques = []
                    
                    while lunes_guia <= f_fin_calc:
                        es_lunes_actual_festivo = lunes_guia.strftime("%Y-%m-%d") in festivos_lunes_lista
                        lunes_proximo = lunes_guia + timedelta(days=7)
                        es_lunes_prox_festivo = lunes_proximo.strftime("%Y-%m-%d") in festivos_lunes_lista
                        
                        if es_lunes_actual_festivo: rango_semana = [lunes_guia + timedelta(days=1), lunes_guia + timedelta(days=2), lunes_guia + timedelta(days=3)]
                        else: rango_semana = [lunes_guia, lunes_guia + timedelta(days=1), lunes_guia + timedelta(days=2), lunes_guia + timedelta(days=3)]
                        
                        rango_fds = [lunes_guia + timedelta(days=4), lunes_guia + timedelta(days=5), lunes_guia + timedelta(days=6)]
                        if es_lunes_prox_festivo: rango_fds.append(lunes_proximo)
                            
                        dias_s = [d for d in rango_semana if f_inicio_calc <= d <= f_fin_calc]
                        if dias_s: bloques.append({'tipo': 'SEMANA', 'fechas': dias_s})
                        
                        dias_f = [d for d in rango_fds if f_inicio_calc <= d <= f_fin_calc]
                        if dias_f: bloques.append({'tipo': 'FDS', 'fechas': dias_f})
                            
                        lunes_guia = lunes_proximo
                        
                    bloques_validos = []
                    for b in bloques:
                        str_fechas_b = [d.strftime("%Y-%m-%d") for d in b['fechas']]
                        if any(f in fechas_manuales_en_rango for f in str_fechas_b): continue
                        bloques_validos.append(b)

                    # 2. CALCULAR HISTORIAL REAL
                    conteo_turnos = {ing["id"]: 0 for ing in lista_ingenieros}
                    for a in asigs_restantes:
                        if a["ingeniero_id"] in conteo_turnos:
                            conteo_turnos[a["ingeniero_id"]] += 1
                            
                    # Fecha ficticia para que todos puedan trabajar la primera vez
                    ultimo_turno = {ing["id"]: f_inicio_calc - timedelta(days=50) for ing in lista_ingenieros}
                    for ing in lista_ingenieros:
                        turnos_ing = [datetime.strptime(a["fecha"], "%Y-%m-%d").date() for a in asigs_restantes if a["ingeniero_id"] == ing["id"]]
                        if turnos_ing: ultimo_turno[ing["id"]] = max(turnos_ing)
                    
                    dias_potenciales = {}
                    for ing in lista_ingenieros:
                        ingreso = datetime.strptime(ing.get("fecha_ingreso", "2026-01-01")[:10], "%Y-%m-%d").date()
                        salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                        dias_potenciales[ing["id"]] = max(1, sum(1 for d in [f_inicio_calc + timedelta(days=x) for x in range((f_fin_calc - f_inicio_calc).days + 1)] if ingreso <= d <= salida))
                    
                    registros_nuevos = []
                    
                    for b in bloques_validos:
                        es_fds = b['tipo'] == 'FDS'
                        es_critico = any((d.month == 12 and d.day in [24, 25, 31]) or (d.month == 1 and d.day == 1) for d in b['fechas'])
                        
                        elegibles_ing = []
                        elegibles_sup = []
                        
                        for ing in lista_ingenieros:
                            ingreso = datetime.strptime(ing.get("fecha_ingreso", "2026-01-01")[:10], "%Y-%m-%d").date()
                            salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                            
                            if not all(ingreso <= d <= salida for d in b['fechas']): continue
                            if any(any(datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date() <= d <= datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date() for v in lista_vacaciones if v["ingeniero_id"] == ing["id"]) for d in b['fechas']): continue
                            if es_fds and not ing.get("permite_fin_semana", True): continue
                            
                            # ✨ COOLDOWN ESTRICTO: 3 Semanas (~20 días)
                            if (b['fechas'][0] - ultimo_turno[ing["id"]]).days <= 20: continue
                            
                            if "Supervisor" in ing.get("rol", ""): elegibles_sup.append(ing)
                            else: elegibles_ing.append(ing)
                                
                        def seleccionar_mejores(pool, cantidad):
                            if es_critico: pool.sort(key=lambda x: (not x.get("es_nuevo", False), conteo_turnos[x["id"]] / dias_potenciales[x["id"]]))
                            else: pool.sort(key=lambda x: conteo_turnos[x["id"]] / dias_potenciales[x["id"]])
                            return pool[:cantidad]

                        if b['tipo'] == 'SEMANA':
                            elegidos_ing = seleccionar_mejores(elegibles_ing, 2)
                            roles_asignar = ["Líder", "Apoyo"]
                            elegidos_sup = []
                        else:
                            # 🌟 LOGICA FDS CON SUPERVISORES COMO APOYO
                            # 1. Asignar el Supervisor Principal Oficial
                            elegidos_sup = seleccionar_mejores(elegibles_sup, 1)
                            sup_id = elegidos_sup[0]["id"] if elegidos_sup else None
                            
                            # 2. Asignar el Líder (del pool normal de ingenieros)
                            elegidos_lider = seleccionar_mejores(elegibles_ing, 1)
                            lider_id = elegidos_lider[0]["id"] if elegidos_lider else None
                            
                            # 3. Unir Ingenieros Sobrantes y Supervisores Sobrantes para ser "Apoyos"
                            pool_apoyos = [x for x in elegibles_ing if x["id"] != lider_id] + \
                                          [x for x in elegibles_sup if x["id"] != sup_id]
                            
                            elegidos_apoyos = seleccionar_mejores(pool_apoyos, 2)
                            
                            elegidos_ing = elegidos_lider + elegidos_apoyos
                            roles_asignar = ["Líder", "Apoyo 1", "Apoyo 2"]
                            
                        # Guardar en registros y actualizar memorias de tiempo (para cooldown)
                        for sup in elegidos_sup:
                            conteo_turnos[sup["id"]] += len(b['fechas'])
                            ultimo_turno[sup["id"]] = b['fechas'][-1]
                            for dia in b['fechas']:
                                registros_nuevos.append({"fecha": str(dia), "ingeniero_id": sup["id"], "tipo_dia": f"FDS (Supervisor)"})

                        for i, ing in enumerate(elegidos_ing):
                            rol_asignado = roles_asignar[i] if i < len(roles_asignar) else "Apoyo"
                            conteo_turnos[ing["id"]] += len(b['fechas'])
                            ultimo_turno[ing["id"]] = b['fechas'][-1] 
                            for dia in b['fechas']:
                                registros_nuevos.append({"fecha": str(dia), "ingeniero_id": ing["id"], "tipo_dia": f"{b['tipo']} ({rol_asignado})"})
                    
                    if registros_nuevos:
                        supabase.table("asignaciones").insert(registros_nuevos).execute()
                        st.success(f"✅ ¡Se han procesado {len(bloques_validos)} Jornadas exitosamente respetando el Cooldown de 3 Semanas!")
                        st.balloons()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error procesando el motor: {e}")

# ==========================================
# 📊 PESTAÑA 5: DASHBOARD DE EQUIDAD
# ==========================================
with tab5:
    st.header("📈 Panel de Análisis y Carga Laboral")
    if len(lista_asignaciones) == 0:
        st.warning("No hay turnos asignados para analizar.")
    else:
        df_asig = pd.DataFrame(lista_asignaciones)
        df_asig['Nombre'] = df_asig['ingeniero_id'].map(dict_nombres_ing)
        df_asig['Categoria'] = df_asig['tipo_dia'].apply(lambda x: "FDS" if "FDS" in x else ("MANUAL" if "MANUAL" in x else "SEMANA"))
        
        st.subheader("⚖️ Distribución Total de Turnos por Profesional")
        conteo_df = df_asig.groupby(['Nombre', 'Categoria']).size().reset_index(name='Cantidad')
        
        fig_bar = px.bar(
            conteo_df, x='Nombre', y='Cantidad', color='Categoria',
            title="Días Trabajados Asignados (Semana vs FDS vs Manuales)",
            color_discrete_map={"SEMANA": "#1f77b4", "FDS": "#ff7f0e", "MANUAL": "#2ca02c"}, text_auto=True
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("🔥 Carga de Fines de Semana")
            df_fds = df_asig[df_asig['Categoria'] == 'FDS']
            fig_pie = px.pie(df_fds, names='Nombre', title="¿Quién hace más Fines de Semana?", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_g2:
            st.subheader("📊 Resumen Tabular de Días")
            resumen_pivot = conteo_df.pivot(index='Nombre', columns='Categoria', values='Cantidad').fillna(0).astype(int)
            if 'SEMANA' not in resumen_pivot: resumen_pivot['SEMANA'] = 0
            if 'FDS' not in resumen_pivot: resumen_pivot['FDS'] = 0
            if 'MANUAL' not in resumen_pivot: resumen_pivot['MANUAL'] = 0
            resumen_pivot['TOTAL DÍAS'] = resumen_pivot['SEMANA'] + resumen_pivot['FDS'] + resumen_pivot['MANUAL']
            st.dataframe(resumen_pivot.sort_values(by="TOTAL DÍAS", ascending=False), use_container_width=True)

# ==========================================
# 🔄 PESTAÑA 6: RELEVOS Y ASIGNACIÓN MANUAL
# ==========================================
with tab6:
    st.header("🔄 Asignaciones y Relevos Manuales")
    
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        st.subheader("➕ Agregar Turno Manual")
        st.markdown("Usa esta opción si quieres fijar fechas **antes** de correr el motor automático.")
        rango_manual = st.date_input("Rango de fechas a asignar (o un solo día):", [], min_value=FECHA_MIN)
        ing_manual = st.selectbox("Profesional:", lista_ingenieros, format_func=lambda x: f"{x['nombre']} ({x['rol']})", key="ing_man")
        rol_manual = st.selectbox("Rol en el turno:", ["Líder", "Apoyo", "Apoyo 1", "Apoyo 2", "Supervisor"])
        
        if st.button("💾 Guardar Asignación Manual", use_container_width=True):
            if len(rango_manual) > 0:
                start_d = rango_manual[0]
                end_d = rango_manual[-1] if len(rango_manual) > 1 else rango_manual[0]
                
                dia_aux = start_d
                nuevos_registros = []
                while dia_aux <= end_d:
                    nuevos_registros.append({
                        "fecha": str(dia_aux),
                        "ingeniero_id": ing_manual["id"],
                        "tipo_dia": f"MANUAL ({rol_manual})"
                    })
                    dia_aux += timedelta(days=1)
                
                try:
                    supabase.table("asignaciones").insert(nuevos_registros).execute()
                    st.success("✅ Turnos manuales agregados correctamente.")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
            else:
                st.error("⚠️ Selecciona al menos una fecha.")
    
    with col_r2:
        st.subheader("🔄 Modificar / Relevo de Turno")
        st.markdown("Modifica quién asiste a un turno que **ya existe** en el calendario.")
        if len(lista_asignaciones) == 0:
            st.info("ℹ️ No hay turnos asignados aún.")
        else:
            fecha_relevo = st.date_input("1. Selecciona la fecha a modificar:", min_value=FECHA_MIN)
            str_fecha_rel = str(fecha_relevo)
            
            turnos_dia = [a for a in lista_asignaciones if a["fecha"] == str_fecha_rel]
            
            if not turnos_dia:
                st.warning("⚠️ No hay personal programado en esa fecha.")
            else:
                opciones_turno = []
                for t in turnos_dia:
                    nom = dict_nombres_ing.get(t['ingeniero_id'], 'Desconocido')
                    rol_t = t.get('tipo_dia', 'DISPONIBLE')
                    opciones_turno.append(f"{t['id']} - {nom} ({rol_t})")
                
                turno_sel = st.selectbox("2. Quién entrega el turno:", opciones_turno)
                id_asig_cambiar = int(turno_sel.split("-")[0].strip())
                nuevo_ing = st.selectbox("3. Quién toma el relevo:", lista_ingenieros, format_func=lambda x: f"{x['nombre']} ({x['rol']})")
                
                if st.button("🔄 Ejecutar Relevo", use_container_width=True):
                    try:
                        supabase.table("asignaciones").update({"ingeniero_id": nuevo_ing["id"]}).eq("id", id_asig_cambiar).execute()
                        st.success(f"✅ ¡Relevo exitoso! {nuevo_ing['nombre']} ha tomado el turno.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
