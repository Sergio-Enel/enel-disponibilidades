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
        st.caption("Festivos Colombianos (Incluye Ley Emiliani, Fijos y Semana Santa)")
        str_festivos_default = (
            "2026-01-01, 2026-01-12, 2026-03-23, 2026-04-02, 2026-04-03, 2026-05-01, 2026-05-18, 2026-06-08, 2026-06-15, 2026-06-29, 2026-07-20, 2026-08-07, 2026-08-17, 2026-10-12, 2026-11-02, 2026-11-16, 2026-12-08, 2026-12-25, "
            "2027-01-01, 2027-01-11, 2027-03-22, 2027-03-25, 2027-03-26, 2027-05-01, 2027-05-10, 2027-05-31, 2027-06-07, 2027-07-05, 2027-07-20, 2027-08-07, 2027-08-16, 2027-10-18, 2027-11-01, 2027-11-15, 2027-12-08, 2027-12-25, "
            "2028-01-01, 2028-01-10, 2028-03-20, 2028-04-13, 2028-04-14, 2028-05-01, 2028-05-29, 2028-06-19, 2028-06-26, 2028-07-03, 2028-07-20, 2028-08-07, 2028-08-21, 2028-10-16, 2028-11-06, 2028-11-13, 2028-12-08, 2028-12-25, "
            "2029-01-01, 2029-01-08, 2029-03-19, 2029-03-29, 2029-03-30, 2029-05-01, 2029-05-14, 2029-06-04, 2029-06-11, 2029-07-02, 2029-07-20, 2029-08-07, 2029-08-20, 2029-10-15, 2029-11-05, 2029-11-12, 2029-12-08, 2029-12-25, "
            "2030-01-01, 2030-01-07, 2030-03-25, 2030-04-18, 2030-04-19, 2030-05-01, 2030-06-03, 2030-06-24, 2030-07-01, 2030-07-20, 2030-08-07, 2030-08-19, 2030-10-14, 2030-11-04, 2030-11-11, 2030-12-08, 2030-12-25"
        )
        str_festivos = st.text_area("Lista de Festivos (AAAA-MM-DD)", str_festivos_default, height=150)
        festivos_colombia_lista = [f.strip() for f in str_festivos.split(",") if f.strip()]

    st.markdown("---")
    st.markdown("**Desarrollado y mantenido por:**")
    st.markdown("👨‍💻 **Sergio Cutiva**")
    st.markdown("📧 *sergio.cutiva@enel.com*")
    st.markdown("---")
    st.caption("Versión 4.9 | Supervisores solo FDS y Métricas por Turno")

# ==========================================
# 🛠️ FUNCIONES AUXILIARES Y ESTÉTICA
# ==========================================
def obtener_ingenieros(): return supabase.table("ingenieros").select("*").execute().data
def obtener_vacaciones(): return supabase.table("vacaciones").select("*").execute().data
def obtener_asignaciones(): return supabase.table("asignaciones").select("*").execute().data

def obtener_estilo_motivo(motivo):
    estilos = {
        "Vacaciones": ("🌴", "#e0f7fa", "#006064"),
        "Incapacidad Médica": ("🤒", "#ffebee", "#c62828"),
        "Permiso Empresa": ("🏢", "#f3e5f5", "#6a1b9a"),
        "Licencia": ("📜", "#e8f5e9", "#2e7d32"),
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
    "📊 Dashboard Ejecutivo",
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
        * **Jornadas Bloqueadas:** Se manejan bloques de *Despacho (Lun-Vie)*, *Semana (Lun-Jue)* o *Fin de Semana (Vie-Dom)*.
        * **Roles por Jornada:** En Semana operan 2 ingenieros (1 Líder y 1 Apoyo). En FDS operan 4 personas (1 Líder, 2 Apoyos y 1 Supervisor). Despacho toma 1 Ingeniero exclusivo.
        * **Restricción Supervisores:** Operan SÓLO fines de semana. Jamás entre semana. Tratan de no repetir fines de semana seguidos, pero pueden hacerlo como última opción si es necesario.
        * **Alternancia Estricta de Ingenieros:** 🔄 Los ingenieros están bloqueados matemáticamente para repetir FDS hasta que hayan cumplido un turno entre semana o despacho.
        * **Aislamiento de Despacho:** 🌅 Quien hace despacho a las 6 AM no puede tener guardia la semana en curso, ni los fines de semana adyacentes.
        * **Descanso (Cooldown de 3 semanas):** ⏳ Nadie recibe un turno si no han pasado al menos **20 días** desde su última guardia.
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
        col_a1, col_a2 = st.columns(2)
        f_inicio_calc = col_a1.date_input("Fecha Inicio Semestre", max(datetime.now().date(), FECHA_MIN), min_value=FECHA_MIN)
        f_fin_calc = col_a2.date_input("Fecha Fin Semestre", max(datetime.now().date() + timedelta(days=180), FECHA_MIN), min_value=FECHA_MIN)

        st.markdown("---")
        st.subheader("Opciones de Ejecución del Algoritmo")
        modo_ejecucion = st.radio(
            "Selecciona qué debe hacer el algoritmo con los turnos que ya existen en ese rango de fechas:", 
            [
                "🛠️ Mantener Manuales y Recalcular Automáticos (Recomendado)",
                "🧩 Rellenar Huecos (Mantiene TODOS los turnos actuales y solo llena donde falta alguien)",
                "⚠️ Sobrescribir TODO (Borra todos los turnos del rango, incluyendo los manuales, y calcula desde cero)"
            ],
            index=0
        )

        if st.button("🚀 Optimizar y Asignar por Jornadas", use_container_width=True):
            with st.spinner("Construyendo jornadas, despachos y aplicando reglas de alternancia..."):
                try:
                    # 1. RECUPERAR TODO EL HISTORIAL Y FILTRAR SEGÚN EL MODO DE EJECUCIÓN
                    asigs_historicas = supabase.table("asignaciones").select("*").execute().data
                    ids_to_delete = []
                    
                    for a in asigs_historicas:
                        fecha_a = datetime.strptime(a["fecha"], "%Y-%m-%d").date()
                        if f_inicio_calc <= fecha_a <= f_fin_calc:
                            if "🧩" in modo_ejecucion:
                                pass
                            elif "🛠️" in modo_ejecucion:
                                if "MANUAL" not in a.get("tipo_dia", "").upper():
                                    ids_to_delete.append(a["id"])
                            elif "⚠️" in modo_ejecucion:
                                ids_to_delete.append(a["id"])
                                
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
                        
                        rango_despacho = [lunes_guia + timedelta(days=i) for i in range(5)] # Lunes a Viernes
                        
                        if es_lunes_actual_festivo: rango_semana = [lunes_guia + timedelta(days=1), lunes_guia + timedelta(days=2), lunes_guia + timedelta(days=3)]
                        else: rango_semana = [lunes_guia, lunes_guia + timedelta(days=1), lunes_guia + timedelta(days=2), lunes_guia + timedelta(days=3)]
                        
                        rango_fds = [lunes_guia + timedelta(days=4), lunes_guia + timedelta(days=5), lunes_guia + timedelta(days=6)]
                        if es_lunes_prox_festivo: rango_fds.append(lunes_proximo)
                            
                        dias_d = [d for d in rango_despacho if f_inicio_calc <= d <= f_fin_calc]
                        if dias_d: bloques_validos.append({'tipo': 'DESPACHO', 'fechas': dias_d})
                            
                        dias_s = [d for d in rango_semana if f_inicio_calc <= d <= f_fin_calc]
                        if dias_s: bloques_validos.append({'tipo': 'SEMANA', 'fechas': dias_s})
                        
                        dias_f = [d for d in rango_fds if f_inicio_calc <= d <= f_fin_calc]
                        if dias_f: bloques_validos.append({'tipo': 'FDS', 'fechas': dias_f})
                            
                        lunes_guia = lunes_proximo

                    # 3. PRE-CALCULAR DATOS DE OPTIMIZACIÓN
                    conteo_turnos = {ing["id"]: 0 for ing in lista_ingenieros}
                    conteo_roles_hist = {ing["id"]: {"Líder": 0, "Apoyo": 0, "Supervisor": 0, "Despacho": 0} for ing in lista_ingenieros}
                    ultimo_tipo_guardia = {ing["id"]: "SEMANA" for ing in lista_ingenieros} 
                    
                    asigs_historicas_sorted = sorted(asigs_restantes, key=lambda x: datetime.strptime(x["fecha"], "%Y-%m-%d"))
                    for a in asigs_historicas_sorted:
                        ing_id = a["ingeniero_id"]
                        tipo = a.get("tipo_dia", "").upper()
                        
                        if "FDS" in tipo: ultimo_tipo_guardia[ing_id] = "FDS"
                        elif "SEMANA" in tipo or "DESPACHO" in tipo: ultimo_tipo_guardia[ing_id] = "SEMANA"
                        
                        if ing_id in conteo_turnos:
                            conteo_turnos[ing_id] += 1
                            rol_limpio = tipo.split("(")[-1].replace(")", "").strip()
                            if "APOYO" in rol_limpio: rol_limpio = "Apoyo"
                            elif "LÍDER" in rol_limpio or "LIDER" in rol_limpio: rol_limpio = "Líder"
                            elif "SUPERVISOR" in rol_limpio: rol_limpio = "Supervisor"
                            elif "DESPACHO" in rol_limpio or "DESPACHO" in tipo: rol_limpio = "Despacho"
                            
                            if rol_limpio in conteo_roles_hist[ing_id]:
                                conteo_roles_hist[ing_id][rol_limpio] += 1
                            
                    ultimo_turno = {ing["id"]: f_inicio_calc - timedelta(days=50) for ing in lista_ingenieros}
                    for ing in lista_ingenieros:
                        turnos_ing = [datetime.strptime(a["fecha"], "%Y-%m-%d").date() for a in asigs_restantes if a["ingeniero_id"] == ing["id"]]
                        if turnos_ing: ultimo_turno[ing["id"]] = max(turnos_ing)
                    
                    dias_potenciales = {}
                    for ing in lista_ingenieros:
                        ingreso = datetime.strptime(ing.get("fecha_ingreso", "2026-01-01")[:10], "%Y-%m-%d").date()
                        salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                        dias_potenciales[ing["id"]] = max(1, sum(1 for d in [f_inicio_calc + timedelta(days=x) for x in range((f_fin_calc - f_inicio_calc).days + 1)] if ingreso <= d <= salida))
                    
                    vacaciones_por_ing = {ing["id"]: set() for ing in lista_ingenieros}
                    for v in lista_vacaciones:
                        v_ini = datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date()
                        v_fin = datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date()
                        delta = (v_fin - v_ini).days
                        for i in range(delta + 1):
                            vacaciones_por_ing[v["ingeniero_id"]].add(v_ini + timedelta(days=i))

                    registros_nuevos = []
                    
                    # 4. ITERAR SOBRE BLOQUES Y AUTOCOMPLETAR
                    for b in bloques_validos:
                        str_fechas_b = [d.strftime("%Y-%m-%d") for d in b['fechas']]
                        
                        manuales_bloque = [a for a in asigs_restantes if a["fecha"] in str_fechas_b]
                        roles_cubiertos = set()
                        ing_cubiertos = set()
                        for m in manuales_bloque:
                            if "(" in m["tipo_dia"]:
                                rol = m["tipo_dia"].split("(")[-1].replace(")", "").strip()
                                if "Despacho" in rol or "DESPACHO" in m["tipo_dia"]: rol = "Despacho"
                                roles_cubiertos.add(rol)
                            ing_cubiertos.add(m["ingeniero_id"])

                        roles_sup_necesarios = []
                        roles_ing_necesarios = []

                        if b['tipo'] == 'DESPACHO':
                            if "Despacho" not in roles_cubiertos: roles_ing_necesarios.append("Despacho")
                        elif b['tipo'] == 'SEMANA':
                            if "Líder" not in roles_cubiertos: roles_ing_necesarios.append("Líder")
                            if "Apoyo" not in roles_cubiertos: roles_ing_necesarios.append("Apoyo")
                        elif b['tipo'] == 'FDS':
                            if "Supervisor" not in roles_cubiertos: roles_sup_necesarios.append("Supervisor")
                            if "Líder" not in roles_cubiertos: roles_ing_necesarios.append("Líder")
                            
                            apoyos_manuales = sum(1 for r in roles_cubiertos if "Apoyo" in r)
                            if apoyos_manuales == 0: roles_ing_necesarios.extend(["Apoyo 1", "Apoyo 2"])
                            elif apoyos_manuales == 1:
                                if "Apoyo 1" in roles_cubiertos: roles_ing_necesarios.append("Apoyo 2")
                                else: roles_ing_necesarios.append("Apoyo 1")

                        if not roles_sup_necesarios and not roles_ing_necesarios:
                            continue

                        es_fds = b['tipo'] == 'FDS'
                        es_critico = any((d.month == 12 and d.day in [24, 25, 31]) or (d.month == 1 and d.day == 1) for d in b['fechas'])
                        
                        elegibles_ing = []
                        elegibles_sup = []
                        
                        for ing in lista_ingenieros:
                            if ing["id"] in ing_cubiertos: continue 

                            es_supervisor = "Supervisor" in ing.get("rol", "")
                            
                            # REGLA: Supervisores ESTRICTAMENTE PROHIBIDOS en turnos de Despacho o Semana
                            if b['tipo'] in ['DESPACHO', 'SEMANA'] and es_supervisor: continue
                            
                            # REGLA DE ALTERNANCIA ESTRICTA SÓLO PARA INGENIEROS
                            if es_fds and ultimo_tipo_guardia[ing["id"]] == "FDS" and not es_supervisor: continue

                            ingreso = datetime.strptime(ing.get("fecha_ingreso", "2026-01-01")[:10], "%Y-%m-%d").date()
                            salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                            
                            if not all(ingreso <= d <= salida for d in b['fechas']): continue
                            if es_fds and not ing.get("permite_fin_semana", True): continue
                            
                            if (b['fechas'][0] - ultimo_turno[ing["id"]]).days <= 20: continue

                            dias_vac = vacaciones_por_ing[ing["id"]]
                            fechas_bloque = b['fechas']
                            
                            en_vacaciones_directas = any(d in dias_vac for d in fechas_bloque)
                            dia_antes = fechas_bloque[0] - timedelta(days=1)
                            dia_despues = fechas_bloque[-1] + timedelta(days=1)
                            
                            dia_antes_2 = dia_antes - timedelta(days=1)
                            es_sandwich_antes = (dia_antes.strftime("%Y-%m-%d") in festivos_colombia_lista) and (dia_antes_2 in dias_vac)
                            
                            dia_despues_2 = dia_despues + timedelta(days=1)
                            es_sandwich_despues = (dia_despues.strftime("%Y-%m-%d") in festivos_colombia_lista) and (dia_despues_2 in dias_vac)

                            if en_vacaciones_directas or (dia_antes in dias_vac) or (dia_despues in dias_vac) or es_sandwich_antes or es_sandwich_despues:
                                continue 
                            
                            if es_supervisor: elegibles_sup.append(ing)
                            else: elegibles_ing.append(ing)
                                
                        def seleccionar_mejores(pool, cantidad):
                            if cantidad == 0: return []
                            # Para el orden, si ya hizo FDS (aplica para Sups), se penaliza enviándolo al final de la cola (True > False)
                            if es_critico: pool.sort(key=lambda x: (not x.get("es_nuevo", False), ultimo_tipo_guardia[x["id"]] == "FDS", conteo_turnos[x["id"]] / dias_potenciales[x["id"]]))
                            else: pool.sort(key=lambda x: (ultimo_tipo_guardia[x["id"]] == "FDS", conteo_turnos[x["id"]] / dias_potenciales[x["id"]]))
                            return pool[:cantidad]

                        elegidos_sup = []
                        elegibles_para_ing = elegibles_ing.copy()
                        
                        if es_fds:
                            cant_apoyos_necesarios = sum(1 for r in roles_ing_necesarios if "Apoyo" in r)
                            if roles_sup_necesarios:
                                sups_ordenados_turnos = seleccionar_mejores(elegibles_sup, len(elegibles_sup))
                                if cant_apoyos_necesarios > 0 and len(sups_ordenados_turnos) >= 2:
                                    top_2_sups = sups_ordenados_turnos[:2]
                                    top_2_sups.sort(key=lambda x: conteo_roles_hist[x["id"]]["Supervisor"] / max(1, conteo_turnos[x["id"]]))
                                    elegidos_sup = [top_2_sups[0]]
                                    conteo_roles_hist[top_2_sups[0]["id"]]["Supervisor"] += 1
                                    elegibles_para_ing.append(top_2_sups[1])
                                elif len(sups_ordenados_turnos) > 0:
                                    elegidos_sup = [sups_ordenados_turnos[0]]
                                    conteo_roles_hist[sups_ordenados_turnos[0]["id"]]["Supervisor"] += 1

                        cant_ing_necesarios = len([r for r in roles_ing_necesarios if "Líder" in r or "Apoyo" in r or "Despacho" in r])
                        elegidos_ing_crudos = seleccionar_mejores(elegibles_para_ing, cant_ing_necesarios)
                        
                        asignaciones_finales_bloque = []
                        pool_roles_asignar = roles_ing_necesarios.copy()
                        
                        candidatos_lider = [x for x in elegidos_ing_crudos if "Supervisor" not in x.get("rol", "")]
                        candidatos_apoyo = [x for x in elegidos_ing_crudos]
                        
                        # Asignar Despacho
                        for r_necesario in list(pool_roles_asignar):
                            if "Despacho" in r_necesario:
                                if candidatos_apoyo:
                                    candidatos_apoyo.sort(key=lambda x: conteo_roles_hist[x["id"]]["Despacho"] / max(1, conteo_turnos[x["id"]]))
                                    ing_seleccionado = candidatos_apoyo.pop(0)
                                    candidatos_lider = [x for x in candidatos_lider if x["id"] != ing_seleccionado["id"]]
                                    conteo_roles_hist[ing_seleccionado["id"]]["Despacho"] += 1
                                    asignaciones_finales_bloque.append((ing_seleccionado, "Despacho"))
                                    pool_roles_asignar.remove(r_necesario)

                        # Asignar Líderes
                        for r_necesario in list(pool_roles_asignar):
                            if "Líder" in r_necesario:
                                if candidatos_lider:
                                    candidatos_lider.sort(key=lambda x: (x.get("es_nuevo", False), conteo_roles_hist[x["id"]]["Líder"] / max(1, conteo_turnos[x["id"]])))
                                    ing_seleccionado = candidatos_lider.pop(0)
                                    candidatos_apoyo = [x for x in candidatos_apoyo if x["id"] != ing_seleccionado["id"]]
                                    conteo_roles_hist[ing_seleccionado["id"]]["Líder"] += 1
                                    asignaciones_finales_bloque.append((ing_seleccionado, r_necesario))
                                    pool_roles_asignar.remove(r_necesario)

                        # Asignar Apoyos
                        for r_necesario in list(pool_roles_asignar):
                            if "Apoyo" in r_necesario:
                                if candidatos_apoyo:
                                    candidatos_apoyo.sort(key=lambda x: conteo_roles_hist[x["id"]]["Apoyo"] / max(1, conteo_turnos[x["id"]]))
                                    ing_seleccionado = candidatos_apoyo.pop(0)
                                    conteo_roles_hist[ing_seleccionado["id"]]["Apoyo"] += 1
                                    asignaciones_finales_bloque.append((ing_seleccionado, r_necesario))
                            
                        # Guardar resultados
                        for sup in elegidos_sup:
                            conteo_turnos[sup["id"]] += len(b['fechas'])
                            ultimo_turno[sup["id"]] = b['fechas'][-1]
                            ultimo_tipo_guardia[sup["id"]] = "FDS"
                            for dia in b['fechas']:
                                registros_nuevos.append({"fecha": str(dia), "ingeniero_id": sup["id"], "tipo_dia": f"FDS (Supervisor)"})

                        for ing, rol_asignado in asignaciones_finales_bloque:
                            conteo_turnos[ing["id"]] += len(b['fechas'])
                            ultimo_turno[ing["id"]] = b['fechas'][-1] 
                            
                            if b['tipo'] == 'FDS': ultimo_tipo_guardia[ing["id"]] = "FDS"
                            else: ultimo_tipo_guardia[ing["id"]] = "SEMANA" 
                            
                            for dia in b['fechas']:
                                registros_nuevos.append({"fecha": str(dia), "ingeniero_id": ing["id"], "tipo_dia": f"{b['tipo']} ({rol_asignado})"})
                    
                    if registros_nuevos:
                        supabase.table("asignaciones").insert(registros_nuevos).execute()
                        st.success("✅ ¡Jornadas y Despachos procesados! Se respetó el bloqueo estricto de Supervisores en semana.")
                        st.balloons()
                        st.rerun()
                    elif modo_ejecucion != "⚠️ Sobrescribir TODO (Borra todos los turnos del rango, incluyendo los manuales, y calcula desde cero)":
                        st.info("No se encontraron jornadas vacías para asignar en este rango.")
                        
                except Exception as e:
                    st.error(f"Error procesando el motor: {e}")

# ==========================================
# 📊 PESTAÑA 5: DASHBOARD DE EQUIDAD
# ==========================================
with tab5:
    st.header("📈 Panel Ejecutivo de Análisis y Equidad Operativa")
    
    if len(lista_asignaciones) == 0:
        st.warning("No hay turnos asignados para analizar.")
    else:
        df_asig = pd.DataFrame(lista_asignaciones)
        df_asig['Nombre'] = df_asig['ingeniero_id'].map(dict_nombres_ing)
        
        # Categorización inteligente (Reemplaza "MANUAL" por su día real)
        def categorizar_turno(row):
            tipo = row['tipo_dia'].upper()
            fecha_dt = pd.to_datetime(row['fecha'])
            if "DESPACHO" in tipo: return "DESPACHO"
            if "FDS" in tipo: return "FDS"
            if "SEMANA" in tipo: return "SEMANA"
            if "MANUAL" in tipo:
                if fecha_dt.weekday() >= 4: return "FDS"
                else: return "SEMANA"
            return "SEMANA"
            
        df_asig['Categoria'] = df_asig.apply(categorizar_turno, axis=1)
        df_asig['Fecha_dt'] = pd.to_datetime(df_asig['fecha'])
        df_asig = df_asig.sort_values(['Nombre', 'Categoria', 'Fecha_dt'])
        
        df_asig['Dias_Dif'] = df_asig.groupby(['Nombre', 'Categoria'])['Fecha_dt'].diff().dt.days
        df_asig['Nuevo_Turno'] = (df_asig['Dias_Dif'] > 1).astype(int)
        df_asig['Nuevo_Turno'] = df_asig['Nuevo_Turno'].fillna(1) 
        df_asig['ID_Bloque'] = df_asig.groupby(['Nombre', 'Categoria'])['Nuevo_Turno'].cumsum()
        
        df_turnos_agrupados = df_asig.groupby(['Nombre', 'Categoria', 'ID_Bloque']).size().reset_index(name='Dias_en_Turno')
        conteo_turnos_reales = df_turnos_agrupados.groupby(['Nombre', 'Categoria']).size().reset_index(name='Cantidad_Turnos')

        st.markdown("### ⚖️ 1. Distribución de Carga Operativa (Por Turnos)")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            fig_turnos = px.bar(
                conteo_turnos_reales, x='Nombre', y='Cantidad_Turnos', color='Categoria',
                title="Conteo por TURNOS COMPLETOS (Bloques)",
                color_discrete_map={"SEMANA": "#1f77b4", "FDS": "#ff7f0e", "DESPACHO": "#8e24aa"}, text_auto=True,
                labels={'Cantidad_Turnos': 'Cant. de Turnos (Bloques)'}
            )
            st.plotly_chart(fig_turnos, use_container_width=True)
            
        with col_g2:
            conteo_dias = df_asig.groupby(['Nombre', 'Categoria']).size().reset_index(name='Cantidad_Dias')
            fig_dias = px.bar(
                conteo_dias, x='Nombre', y='Cantidad_Dias', color='Categoria',
                title="Visualización Referencial por Días",
                color_discrete_map={"SEMANA": "#1f77b4", "FDS": "#ff7f0e", "DESPACHO": "#8e24aa"}, text_auto=True,
                labels={'Cantidad_Dias': 'Días Trabajados'}
            )
            st.plotly_chart(fig_dias, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🌴 2. Impacto de Ausentismos")
        if len(lista_vacaciones) > 0:
            vac_records = []
            for v in lista_vacaciones:
                nom = dict_nombres_ing.get(v['ingeniero_id'], 'Desconocido')
                start = datetime.strptime(v['fecha_inicio'], "%Y-%m-%d")
                end = datetime.strptime(v['fecha_fin'], "%Y-%m-%d")
                motivo = v.get('motivo', 'Otro')
                dias_fuera = (end - start).days + 1
                vac_records.append({'Nombre': nom, 'Motivo': motivo, 'Dias_Ausente': dias_fuera})
                
            df_vac_stats = pd.DataFrame(vac_records).groupby(['Nombre', 'Motivo'])['Dias_Ausente'].sum().reset_index()
            
            col_v1, col_v2 = st.columns([2, 1])
            with col_v1:
                fig_vac_bar = px.bar(
                    df_vac_stats, x='Nombre', y='Dias_Ausente', color='Motivo',
                    title="Días Totales de Ausencia por Profesional", text_auto=True,
                    color_discrete_map={"Vacaciones": "#00bcd4", "Incapacidad Médica": "#f44336", "Permiso Empresa": "#9c27b0", "Licencia": "#4caf50", "Otro": "#ff9800"},
                    labels={'Dias_Ausente': 'Días Fuera'}
                )
                st.plotly_chart(fig_vac_bar, use_container_width=True)
            with col_v2:
                fig_vac_pie = px.pie(df_vac_stats, names='Motivo', values='Dias_Ausente', title="Motivos Generales", hole=0.4)
                st.plotly_chart(fig_vac_pie, use_container_width=True)
        else:
            st.info("No hay registros de ausentismos para analizar en este momento.")

        st.markdown("---")
        st.markdown("### 📊 3. Resumen de Carga (Turnos Asignados)")
        col_t1, col_t2 = st.columns([1, 2])

        with col_t1:
            df_fds_turnos = conteo_turnos_reales[conteo_turnos_reales['Categoria'] == 'FDS']
            fig_pie_fds = px.pie(df_fds_turnos, names='Nombre', values='Cantidad_Turnos', title="¿Quién hace más Turnos de FDS?", hole=0.4)
            st.plotly_chart(fig_pie_fds, use_container_width=True)

        with col_t2:
            st.caption("Matriz Exacta de Turnos (Bloques Completados)")
            resumen_pivot = conteo_turnos_reales.pivot(index='Nombre', columns='Categoria', values='Cantidad_Turnos').fillna(0).astype(int)
            for col in ['SEMANA', 'FDS', 'DESPACHO']:
                if col not in resumen_pivot.columns: resumen_pivot[col] = 0
            resumen_pivot['TOTAL TURNOS'] = resumen_pivot['SEMANA'] + resumen_pivot['FDS'] + resumen_pivot['DESPACHO']
            st.dataframe(resumen_pivot.sort_values(by="TOTAL TURNOS", ascending=False), use_container_width=True)
            
        st.markdown("---")
        st.markdown("### 🎭 4. Distribución por Rol Específico (Conteo por Turno)")
        st.caption("Aquí puedes auditar equidad de funciones (Cada bloque de guardia suma 1 función).")
        
        df_asig['Rol_Limpio'] = df_asig['tipo_dia'].apply(lambda x: x.split('(')[-1].replace(')', '').strip() if '(' in x else x)
        df_asig['Rol_Limpio'] = df_asig['Rol_Limpio'].replace({"Apoyo 1": "Apoyo", "Apoyo 2": "Apoyo", "Despacho 6 AM": "Despacho"})
        
        roles_por_turno = df_asig.groupby(['Nombre', 'Rol_Limpio', 'ID_Bloque']).size().reset_index(name='Dias_En_Rol')
        conteo_roles = roles_por_turno.groupby(['Nombre', 'Rol_Limpio']).size().reset_index(name='Cantidad_Turnos')
        
        col_r1, col_r2 = st.columns([2, 1])
        with col_r1:
            fig_roles = px.bar(
                conteo_roles, x='Nombre', y='Cantidad_Turnos', color='Rol_Limpio',
                title="Gráfica de Participación por Rol (Por Turno)",
                color_discrete_map={"Líder": "#1565c0", "Apoyo": "#2e7d32", "Supervisor": "#e65100", "Despacho": "#8e24aa"},
                barmode='group', text_auto=True,
                labels={'Cantidad_Turnos': 'Turnos Cumplidos'}
            )
            st.plotly_chart(fig_roles, use_container_width=True)
            
        with col_r2:
            st.caption("Matriz Exacta de Funciones (Turnos)")
            pivot_roles = conteo_roles.pivot(index='Nombre', columns='Rol_Limpio', values='Cantidad_Turnos').fillna(0).astype(int)
            pivot_roles['TOTAL FUNCIONES'] = pivot_roles.sum(axis=1)
            st.dataframe(pivot_roles.sort_values(by="TOTAL FUNCIONES", ascending=False), use_container_width=True)

        st.markdown("---")
        st.markdown("### 🌅 5. Control de Despachos (6 AM)")
        df_despacho_turnos = conteo_turnos_reales[conteo_turnos_reales['Categoria'] == 'DESPACHO']
        if not df_despacho_turnos.empty:
            fig_desp = px.bar(
                df_despacho_turnos, x='Nombre', y='Cantidad_Turnos', 
                title="Semanas completas asignadas a Despacho 6 AM", 
                text_auto=True, color_discrete_sequence=["#ab47bc"],
                labels={'Cantidad_Turnos': 'Semanas Asignadas (Turnos)'}
            )
            st.plotly_chart(fig_desp, use_container_width=True)
        else:
            st.info("Aún no hay turnos de Despacho 6 AM asignados para visualizar.")

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
        rol_manual = st.selectbox("Rol en el turno:", ["Líder", "Apoyo", "Apoyo 1", "Apoyo 2", "Supervisor", "Despacho 6 AM"])
        
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
        st.subheader("🔄 Relevo o Cancelación por Día")
        st.markdown("Modifica la disponibilidad de una persona en un día específico.")
        if len(lista_asignaciones) == 0:
            st.info("ℹ️ No hay turnos asignados aún.")
        else:
            fecha_relevo = st.date_input("1. Selecciona la fecha:", min_value=FECHA_MIN)
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
                
                turno_sel = st.selectbox("2. Turno objetivo (a modificar o cancelar):", opciones_turno)
                id_asig_cambiar = int(turno_sel.split("-")[0].strip())
                
                st.markdown("---")
                
                nuevo_ing = st.selectbox("Quién toma el relevo:", lista_ingenieros, format_func=lambda x: f"{x['nombre']} ({x['rol']})")
                if st.button("🔄 Ejecutar Relevo Diariio", use_container_width=True):
                    try:
                        supabase.table("asignaciones").update({"ingeniero_id": nuevo_ing["id"]}).eq("id", id_asig_cambiar).execute()
                        st.success(f"✅ ¡Relevo exitoso! {nuevo_ing['nombre']} ha tomado el turno.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("❌ Cancelar Turno Seleccionado", use_container_width=True):
                    try:
                        supabase.table("asignaciones").delete().eq("id", id_asig_cambiar).execute()
                        st.success("✅ Turno cancelado y eliminado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ===== SECCIÓN EXCLUSIVA PARA RELEVOS EN BLOQUE (IDEAL DESPACHOS) =====
    st.markdown("---")
    st.subheader("🌅 Relevo / Cancelación por Rango de Fechas (Ideal para Despachos)")
    st.markdown("Utiliza esta opción para reemplazar o cancelar toda una semana de Despacho (Lunes a Viernes) o un bloque de FDS a la vez.")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        rango_mod = st.date_input("1. Rango de Fechas del bloque:", [], min_value=FECHA_MIN, key="rango_masivo")
        
        if len(rango_mod) == 2:
            start_mod, end_mod = rango_mod[0], rango_mod[1]
            turnos_en_rango = [a for a in lista_asignaciones if start_mod <= datetime.strptime(a['fecha'], "%Y-%m-%d").date() <= end_mod]
            
            if turnos_en_rango:
                profesionales_en_rango = list(set([a['ingeniero_id'] for a in turnos_en_rango]))
                ing_a_reemplazar = st.selectbox("2. Profesional a retirar del bloque:", profesionales_en_rango, format_func=lambda x: dict_nombres_ing.get(x, 'Desconocido'))
                
                turnos_objetivo = [a for a in turnos_en_rango if a['ingeniero_id'] == ing_a_reemplazar]
                ids_objetivo = [a['id'] for a in turnos_objetivo]
                
    with col_b2:
        if len(rango_mod) == 2 and turnos_en_rango:
            st.info(f"Se detectaron **{len(ids_objetivo)}** días para {dict_nombres_ing.get(ing_a_reemplazar)} en este rango.")
            
            ing_relevo_masivo = st.selectbox("3. Quién toma el relevo de este bloque completo:", lista_ingenieros, format_func=lambda x: f"{x['nombre']} ({x['rol']})", key="ing_rel_masivo")
            
            if st.button("🔄 Ejecutar Relevo de Bloque Completo", use_container_width=True):
                try:
                    for id_t in ids_objetivo:
                        supabase.table("asignaciones").update({"ingeniero_id": ing_relevo_masivo["id"]}).eq("id", id_t).execute()
                    st.success(f"✅ ¡Bloque relevado exitosamente por {ing_relevo_masivo['nombre']}!")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
                
            if st.button("❌ Cancelar Bloque Completo", use_container_width=True):
                try:
                    for i in range(0, len(ids_objetivo), 100):
                        supabase.table("asignaciones").delete().in_("id", ids_objetivo[i:i+100]).execute()
                    st.success("✅ Bloque cancelado y eliminado correctamente.")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
