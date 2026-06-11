import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
    
    # Lista de festivos proyectada hasta 2030 (Lunes Festivos Colombia)
    with st.expander("📆 Configuración de Festivos", expanded=False):
        st.caption("Estos lunes festivos se usarán visualmente y en el motor de jornadas.")
        str_festivos_default = (
            "2024-01-01, 2024-01-08, 2024-03-25, 2024-05-13, 2024-06-03, 2024-06-10, 2024-07-01, 2024-08-19, 2024-10-14, 2024-11-04, 2024-11-11, "
            "2025-01-06, 2025-03-24, 2025-06-02, 2025-06-23, 2025-06-30, 2025-08-18, 2025-10-13, 2025-11-03, 2025-11-17, "
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
    st.markdown("📧 *sergiocutivam@gmail.com*")
    st.markdown("---")
    st.caption("Versión 2.1 | Motor Proporcional")

# ==========================================
# 🛠️ FUNCIONES DE BASE DE DATOS
# ==========================================
def obtener_ingenieros():
    return supabase.table("ingenieros").select("*").execute().data

def obtener_vacaciones():
    return supabase.table("vacaciones").select("*").execute().data

def obtener_asignaciones():
    return supabase.table("asignaciones").select("*").execute().data

# ==========================================
# ⚡ INTERFAZ PRINCIPAL
# ==========================================
st.title("⚡ Sistema de Asignación de Disponibilidades")
st.markdown("Matriz de control por jornadas, ausentismos y equidad operativa.")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📅 Calendario Operativo", 
    "👥 Gestión de Equipo", 
    "🌴 Ausentismos", 
    "⚙️ Motor Algorítmico",
    "📊 Dashboard",
    "🔄 Relevos Manuales"
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
        * **Jornadas Bloqueadas:** No se asigna por día individual. Se asigna un bloque de *Lunes a Jueves (SEMANA)* o de *Viernes a Domingo (FDS)*. Si el lunes es festivo, la jornada FDS se alarga hasta el Lunes, y la de Semana acorta de Martes a Jueves.
        * **Roles por Jornada:** En Semana operan 2 ingenieros (1 Líder y 1 Apoyo). En FDS operan 4 personas (1 Líder, 2 Apoyos y 1 Supervisor).
        * **Equidad Proporcional:** El sistema busca siempre a la persona que tenga la **menor carga porcentual** (Turnos asignados / Días de contrato vigente). Así, si alguien es nuevo y lleva 1 mes, se le asigna carga equivalente a 1 mes y no se le satura intentando igualar a los antiguos.
        * **Descanso (Cooldown):** Nadie puede recibir un nuevo turno si no han pasado al menos 2 días desde que terminó su última guardia.
        * **Excepciones Absolutas:** El motor jamás asigna turnos a personal en sus fechas de vacaciones/incapacidad, ni asigna FDS a roles restringidos.
        
        """)
    st.markdown("---")

    if len(lista_ingenieros) == 0:
        st.info("ℹ️ Comienza registrando al equipo en la pestaña 'Gestión de Equipo'.")
    else:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            año_sel = st.selectbox("Seleccionar Año:", [2024, 2025, 2026, 2027, 2028, 2029, 2030], index=0)
        with col_m2:
            mes_sel = st.selectbox("Seleccionar Mes:", list(range(1, 13)), format_func=lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][x - 1])
            
        st.markdown("---")
        tipo_vista = st.radio("Formato de visualización:", ["🗂️ Vista Matriz (Por Persona)", "📅 Vista Calendario (Tipo Google Calendar)"], horizontal=True)
        
        primer_dia = datetime(año_sel, mes_sel, 1)
        if mes_sel == 12: ultimo_dia = datetime(año_sel + 1, 1, 1) - timedelta(days=1)
        else: ultimo_dia = datetime(año_sel, mes_sel + 1, 1) - timedelta(days=1)
        rango_dias = [primer_dia + timedelta(days=x) for x in range((ultimo_dia - primer_dia).days + 1)]

        if "Matriz" in tipo_vista:
            columnas_dias = [d.strftime("%Y-%m-%d") for d in rango_dias]
            
            # --- AGREGAR ÍCONO DE FESTIVO EN LOS ENCABEZADOS DE LA MATRIZ ---
            nombres_columnas_bonitas = []
            for d in rango_dias:
                str_fecha = d.strftime("%Y-%m-%d")
                nombre_base = d.strftime("%d-%b (%a)")
                if str_fecha in festivos_lunes_lista:
                    nombres_columnas_bonitas.append(f"🎊 {nombre_base}")
                else:
                    nombres_columnas_bonitas.append(nombre_base)

            matriz_df = pd.DataFrame(index=[ing["nombre"] for ing in lista_ingenieros], columns=columnas_dias)
            matriz_df = matriz_df.fillna("—")
            
            for vac in lista_vacaciones:
                nom_ing = dict_nombres_ing.get(vac["ingeniero_id"])
                if nom_ing in matriz_df.index:
                    v_ini, v_fin = datetime.strptime(vac["fecha_inicio"], "%Y-%m-%d"), datetime.strptime(vac["fecha_fin"], "%Y-%m-%d")
                    dia_aux = v_ini
                    while dia_aux <= v_fin:
                        str_dia = dia_aux.strftime("%Y-%m-%d")
                        if str_dia in matriz_df.columns: matriz_df.at[nom_ing, str_dia] = f"🌴 {vac.get('motivo', 'Ausente')}"
                        dia_aux += timedelta(days=1)
                        
            for asig in lista_asignaciones:
                nom_ing = dict_nombres_ing.get(asig["ingeniero_id"])
                str_fecha = asig["fecha"]
                if nom_ing in matriz_df.index and str_fecha in matriz_df.columns:
                    if "🌴" in matriz_df.at[nom_ing, str_fecha]: 
                        matriz_df.at[nom_ing, str_fecha] = "⚠️ CRÍTICO"
                    else: 
                        tipo = asig.get('tipo_dia', 'DISPONIBLE')
                        rol_mostrar = tipo.split('(')[-1].replace(')', '') if '(' in tipo else tipo
                        matriz_df.at[nom_ing, str_fecha] = f"⚡ {rol_mostrar}"
            
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
                            
                            # --- MOSTRAR ÍCONO DE FESTIVO AL LADO DEL NÚMERO ---
                            if str_dia in festivos_lunes_lista:
                                st.markdown(f"**{dia.day}** 🎊 *(Festivo)*")
                            else:
                                st.markdown(f"**{dia.day}**")
                                
                            turnos_hoy = [a for a in lista_asignaciones if a["fecha"] == str_dia]
                            vacaciones_hoy = [v for v in lista_vacaciones if datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date() <= dia <= datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date()]
                            
                            for v in vacaciones_hoy:
                                st.markdown(f"<div style='background-color: #ffebee; color: #c62828; padding: 4px; border-radius: 4px; font-size: 11px; margin-bottom: 2px;' title='{v.get('motivo', '')}'>🌴 {dict_nombres_ing.get(v['ingeniero_id'], '')}</div>", unsafe_allow_html=True)
                            for a in turnos_hoy:
                                tipo = a.get('tipo_dia', '')
                                rol_mostrar = tipo.split('(')[-1].replace(')', '') if '(' in tipo else ''
                                st.markdown(f"<div style='background-color: #e8f5e9; color: #2e7d32; padding: 4px; border-radius: 4px; font-size: 11px; margin-bottom: 2px; font-weight: bold;'>⚡ {dict_nombres_ing.get(a['ingeniero_id'], '')} ({rol_mostrar})</div>", unsafe_allow_html=True)
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
        f_ingreso = st.date_input("Fecha de Ingreso", datetime(2024, 1, 1))
        
        tipo_contrato = st.radio("Tipo de Contrato:", ["Término Indefinido", "Caso Especial (Tiene fecha de salida)"])
        if tipo_contrato == "Caso Especial (Tiene fecha de salida)":
            f_salida = st.date_input("Selecciona la Fecha de Salida programada", datetime.now().date() + timedelta(days=30))
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
            if 'fecha_ingreso' not in df_ing.columns: df_ing['fecha_ingreso'] = "2024-01-01"
            if 'fecha_salida' not in df_ing.columns: df_ing['fecha_salida'] = "2099-12-31"
            
            df_ing['Vigencia Hasta'] = df_ing['fecha_salida'].apply(lambda x: "Indefinido" if "2099" in str(x) else x)
            df_show = df_ing[["id", "nombre", "rol", "es_nuevo", "fecha_ingreso", "Vigencia Hasta"]].copy()
            df_show.columns = ["ID", "Nombre", "Rol", "¿Nuevo?", "Ingreso", "Salida"]
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
            # --- NUEVO: TRANSICIÓN DE NUEVO A ANTIGUO ---
            st.markdown("---")
            col_b1, col_b2 = st.columns(2)
            
            with col_b1:
                st.subheader("🎓 Quitar estado 'Nuevo'")
                st.caption("Si un trabajador ya superó su etapa de inducción, retira su etiqueta aquí sin borrar sus datos.")
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
                st.caption("Borra definitivamente a una persona de la base de datos (se perderá su historial).")
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
                fechas = st.date_input("Rango de Fechas:", [])
                
                if st.form_submit_button("📅 Bloquear Fechas") and len(fechas) == 2:
                    supabase.table("vacaciones").insert({"ingeniero_id": ing_ausente["id"], "fecha_inicio": str(fechas[0]), "fecha_fin": str(fechas[1]), "motivo": motivo_ausentismo}).execute()
                    st.rerun()
                        
        with col_v2:
            if len(lista_vacaciones) > 0:
                df_vac = pd.DataFrame(lista_vacaciones)
                df_vac['Profesional'] = df_vac['ingeniero_id'].map(dict_nombres_ing)
                df_show_vac = df_vac[["id", "Profesional", "motivo", "fecha_inicio", "fecha_fin"]].sort_values(by="Fecha Inicio", ascending=False)
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
        f_inicio_calc = col_a1.date_input("Fecha Inicio Semestre", datetime.now().date())
        f_fin_calc = col_a2.date_input("Fecha Fin Semestre", datetime.now().date() + timedelta(days=180))
        
        st.info("ℹ️ El motor está leyendo automáticamente los Lunes Festivos configurados en el panel lateral (Sidebar) para calcular las jornadas.")

        if st.button("🚀 Optimizar y Asignar por Jornadas"):
            with st.spinner("Construyendo jornadas y seleccionando personal..."):
                try:
                    supabase.table("asignaciones").delete().gte("fecha", str(f_inicio_calc)).lte("fecha", str(f_fin_calc)).execute()
                    
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
                        
                    conteo_turnos = {ing["id"]: 0 for ing in lista_ingenieros}
                    ultimo_turno = {ing["id"]: f_inicio_calc - timedelta(days=10) for ing in lista_ingenieros}
                    
                    dias_potenciales = {}
                    for ing in lista_ingenieros:
                        ingreso = datetime.strptime(ing.get("fecha_ingreso", "2024-01-01")[:10], "%Y-%m-%d").date()
                        salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                        dias_potenciales[ing["id"]] = max(1, sum(1 for d in [f_inicio_calc + timedelta(days=x) for x in range((f_fin_calc - f_inicio_calc).days + 1)] if ingreso <= d <= salida))
                    
                    registros_nuevos = []
                    
                    for b in bloques:
                        es_fds = b['tipo'] == 'FDS'
                        es_critico = any((d.month == 12 and d.day in [24, 25, 31]) or (d.month == 1 and d.day == 1) for d in b['fechas'])
                        
                        elegibles_ing = []
                        elegibles_sup = []
                        
                        for ing in lista_ingenieros:
                            ingreso = datetime.strptime(ing.get("fecha_ingreso", "2024-01-01")[:10], "%Y-%m-%d").date()
                            salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                            
                            if not all(ingreso <= d <= salida for d in b['fechas']): continue
                            if any(any(datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date() <= d <= datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date() for v in lista_vacaciones if v["ingeniero_id"] == ing["id"]) for d in b['fechas']): continue
                            if es_fds and not ing.get("permite_fin_semana", True): continue
                            if (b['fechas'][0] - ultimo_turno[ing["id"]]).days <= 2: continue
                            
                            if "Supervisor" in ing.get("rol", ""): elegibles_sup.append(ing)
                            else: elegibles_ing.append(ing)
                                
                        def seleccionar_mejores(pool, cantidad):
                            if es_critico: pool.sort(key=lambda x: (not x.get("es_nuevo", False), conteo_turnos[x["id"]] / dias_potenciales[x["id"]]))
                            else: pool.sort(key=lambda x: conteo_turnos[x["id"]] / dias_potenciales[x["id"]])
                            return pool[:cantidad]

                        if b['tipo'] == 'SEMANA':
                            elegidos_ing = seleccionar_mejores(elegibles_ing, 2)
                            roles_asignar = ["Líder", "Apoyo"]
                        else:
                            elegidos_ing = seleccionar_mejores(elegibles_ing, 3)
                            roles_asignar = ["Líder", "Apoyo 1", "Apoyo 2"]
                            elegidos_sup = seleccionar_mejores(elegibles_sup, 1)
                            
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
                        st.success(f"✅ ¡Se han procesado {len(bloques)} Jornadas Operativas exitosamente!")
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
        st.warning("No hay turnos asignados para analizar. Ejecuta el Motor primero.")
    else:
        df_asig = pd.DataFrame(lista_asignaciones)
        df_asig['Nombre'] = df_asig['ingeniero_id'].map(dict_nombres_ing)
        df_asig['Categoria'] = df_asig['tipo_dia'].apply(lambda x: "FDS" if "FDS" in x else "SEMANA")
        
        st.subheader("⚖️ Distribución Total de Turnos por Profesional")
        conteo_df = df_asig.groupby(['Nombre', 'Categoria']).size().reset_index(name='Cantidad')
        
        fig_bar = px.bar(
            conteo_df, x='Nombre', y='Cantidad', color='Categoria',
            title="Días Trabajados Asignados (Semana vs FDS)",
            color_discrete_map={"SEMANA": "#1f77b4", "FDS": "#ff7f0e"}, text_auto=True
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
            resumen_pivot['TOTAL DÍAS'] = resumen_pivot['SEMANA'] + resumen_pivot['FDS']
            st.dataframe(resumen_pivot.sort_values(by="TOTAL DÍAS", ascending=False), use_container_width=True)

# ==========================================
# 🔄 PESTAÑA 6: RELEVOS MANUALES
# ==========================================
with tab6:
    st.header("🔄 Relevos y Ajustes Manuales")
    st.markdown("Utiliza esta herramienta cuando un ingeniero requiera ser reemplazado temporalmente (por eventualidad, intercambio voluntario, etc.), sin necesidad de recalcular todo el algoritmo semestral.")
    
    if len(lista_asignaciones) == 0:
        st.info("ℹ️ No hay asignaciones programadas actualmente en la base de datos.")
    else:
        col_r1, col_r2 = st.columns([1, 1])
        
        with col_r1:
            fecha_relevo = st.date_input("1. Selecciona la fecha del turno a modificar:")
            str_fecha_rel = str(fecha_relevo)
            
            turnos_dia = [a for a in lista_asignaciones if a["fecha"] == str_fecha_rel]
            
            if not turnos_dia:
                st.warning("⚠️ No hay personal asignado en la fecha seleccionada.")
            else:
                opciones_turno = []
                for t in turnos_dia:
                    nom = dict_nombres_ing.get(t['ingeniero_id'], 'Ingeniero Eliminado/Desconocido')
                    rol_t = t.get('tipo_dia', 'DISPONIBLE')
                    opciones_turno.append(f"{t['id']} - {nom} ({rol_t})")
                
                turno_sel = st.selectbox("2. Selecciona quién entrega el turno:", opciones_turno)
                id_asig_cambiar = int(turno_sel.split("-")[0].strip())
                
                nuevo_ing = st.selectbox("3. Selecciona quién toma el relevo:", lista_ingenieros, format_func=lambda x: f"{x['nombre']} ({x['rol']})")
                
                if st.button("🔄 Confirmar y Ejecutar Relevo", use_container_width=True):
                    try:
                        supabase.table("asignaciones").update({"ingeniero_id": nuevo_ing["id"]}).eq("id", id_asig_cambiar).execute()
                        st.success(f"✅ ¡Relevo exitoso! {nuevo_ing['nombre']} ha tomado el turno.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ocurrió un error al intentar hacer el relevo: {e}")
        
        with col_r2:
            st.info("💡 **Nota Operativa:** Este cambio aplica únicamente al día seleccionado. Si la persona que entrega el turno iba a trabajar toda la jornada (ej. Viernes a Domingo), deberás hacer el relevo manualmente para cada uno de esos días en este módulo.")
