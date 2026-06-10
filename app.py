import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import plotly.express as px
from supabase import create_client, Client

# ==========================================
# ⚡ CONFIGURACIÓN DE PÁGINA Y CONEXIÓN
# ==========================================
st.set_page_config(page_title="Disponibilidades ENEL", page_icon="⚡", layout="wide")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

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
st.title("⚡ Sistema de Asignación de Disponibilidades - ENEL")
st.markdown("Matriz de control por jornadas, ausentismos y equidad operativa.")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📅 Calendario Operativo", 
    "👥 Gestión de Equipo", 
    "🌴 Ausentismos", 
    "⚙️ Motor Algorítmico",
    "📊 Dashboard de Equidad"
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
    
    if len(lista_ingenieros) == 0:
        st.info("ℹ️ Comienza registrando al equipo en la pestaña 'Gestión de Equipo'.")
    else:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            año_sel = st.selectbox("Seleccionar Año:", [2024, 2025, 2026, 2027], index=1)
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
            nombres_columnas_bonitas = [d.strftime("%d-%b (%a)") for d in rango_dias]
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
                        # Extraer el rol dinámico asignado por el motor ej: "SEMANA (Líder)" -> "Líder"
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
                            st.markdown(f"**{dia.day}**")
                            str_dia = dia.strftime("%Y-%m-%d")
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
        with st.form("form_ingeniero", clear_on_submit=True):
            nombre = st.text_input("Nombre Completo:").strip().upper()
            
            # --- ROLES FIJOS CORREGIDOS ---
            rol = st.selectbox("Rol Fijo:", ["Ingeniero (Líder/Apoyo)", "Supervisor"])
            
            permite_fds = st.radio("¿Turnos Fin de Semana?", [True, False], format_func=lambda x: "Sí" if x else "No (Restringido)")
            es_nuevo = st.radio("¿Es nuevo? (Prioridad Diciembre)", [False, True], format_func=lambda x: "Sí" if x else "No")
            
            st.markdown("---")
            st.markdown("**Vigencia en el Equipo**")
            f_ingreso = st.date_input("Fecha de Ingreso", datetime(2024, 1, 1))
            
            tipo_contrato = st.radio("Tipo de Contrato:", ["Término Indefinido", "Caso Especial (Tiene fecha de salida)"])
            str_f_salida = str(st.date_input("Fecha de Salida programada", datetime.now().date() + timedelta(days=30))) if tipo_contrato == "Caso Especial (Tiene fecha de salida)" else "2099-12-31"
            
            if st.form_submit_button("💾 Guardar Trabajador"):
                if nombre:
                    try:
                        supabase.table("ingenieros").insert({
                            "nombre": nombre, "rol": rol, "permite_fin_semana": permite_fds, "es_nuevo": es_nuevo,
                            "fecha_ingreso": str(f_ingreso), "fecha_salida": str_f_salida
                        }).execute()
                        st.success("✅ Guardado correctamente.")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

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
            
            st.markdown("---")
            st.subheader("❌ Eliminar Trabajador")
            ing_a_eliminar = st.selectbox("Selecciona el profesional:", lista_ingenieros, format_func=lambda x: f"{x['id']} - {x['nombre']}")
            
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
        
        st.markdown("**📅 Días Críticos: Lunes Festivos (Colombia)**")
        st.caption("Añade los lunes festivos. Si el motor detecta que un lunes está en esta lista, lo fusionará con la jornada de FDS y el turno entre semana iniciará el martes.")
        str_festivos = st.text_area("Listado de Lunes Festivos (Formato YYYY-MM-DD, separados por coma)", 
                     "2024-01-01, 2024-01-08, 2024-03-25, 2024-05-13, 2024-06-03, 2024-06-10, 2024-07-01, 2024-08-19, 2024-10-14, 2024-11-04, 2024-11-11, 2025-01-06, 2025-03-24, 2025-06-02, 2025-06-23, 2025-06-30, 2025-08-18, 2025-10-13, 2025-11-03, 2025-11-17, 2026-01-12, 2026-03-23, 2026-05-18, 2026-06-08, 2026-06-15, 2026-06-29, 2026-07-20, 2026-08-17, 2026-10-12, 2026-11-02, 2026-11-16")
        
        festivos_lunes_lista = [f.strip() for f in str_festivos.split(",") if f.strip()]

        if st.button("🚀 Optimizar y Asignar por Jornadas"):
            with st.spinner("Construyendo jornadas y seleccionando personal..."):
                try:
                    # Limpiar periodo
                    supabase.table("asignaciones").delete().gte("fecha", str(f_inicio_calc)).lte("fecha", str(f_fin_calc)).execute()
                    
                    # 1. Agrupar todas las fechas en "Bloques/Jornadas" (Respetando el lunes festivo)
                    lunes_guia = f_inicio_calc - timedelta(days=f_inicio_calc.weekday())
                    bloques = []
                    
                    while lunes_guia <= f_fin_calc:
                        es_lunes_actual_festivo = lunes_guia.strftime("%Y-%m-%d") in festivos_lunes_lista
                        lunes_proximo = lunes_guia + timedelta(days=7)
                        es_lunes_prox_festivo = lunes_proximo.strftime("%Y-%m-%d") in festivos_lunes_lista
                        
                        # --- JORNADA ENTRE SEMANA ---
                        if es_lunes_actual_festivo:
                            rango_semana = [lunes_guia + timedelta(days=1), lunes_guia + timedelta(days=2), lunes_guia + timedelta(days=3)] # Mar-Jue
                        else:
                            rango_semana = [lunes_guia, lunes_guia + timedelta(days=1), lunes_guia + timedelta(days=2), lunes_guia + timedelta(days=3)] # Lun-Jue
                        
                        # --- JORNADA FIN DE SEMANA ---
                        rango_fds = [lunes_guia + timedelta(days=4), lunes_guia + timedelta(days=5), lunes_guia + timedelta(days=6)] # Vie-Dom
                        if es_lunes_prox_festivo:
                            rango_fds.append(lunes_proximo) # Vie-LunFestivo
                            
                        # Guardar bloques si caen en el rango de usuario
                        dias_s = [d for d in rango_semana if f_inicio_calc <= d <= f_fin_calc]
                        if dias_s: bloques.append({'tipo': 'SEMANA', 'fechas': dias_s})
                        
                        dias_f = [d for d in rango_fds if f_inicio_calc <= d <= f_fin_calc]
                        if dias_f: bloques.append({'tipo': 'FDS', 'fechas': dias_f})
                            
                        lunes_guia = lunes_proximo
                        
                    # 2. Control de Ocupación
                    conteo_turnos = {ing["id"]: 0 for ing in lista_ingenieros}
                    ultimo_turno = {ing["id"]: f_inicio_calc - timedelta(days=10) for ing in lista_ingenieros}
                    
                    dias_potenciales = {}
                    for ing in lista_ingenieros:
                        ingreso = datetime.strptime(ing.get("fecha_ingreso", "2024-01-01")[:10], "%Y-%m-%d").date()
                        salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                        dias_potenciales[ing["id"]] = max(1, sum(1 for d in [f_inicio_calc + timedelta(days=x) for x in range((f_fin_calc - f_inicio_calc).days + 1)] if ingreso <= d <= salida))
                    
                    registros_nuevos = []
                    
                    # 3. Asignar personal a cada bloque/jornada completa
                    for b in bloques:
                        es_fds = b['tipo'] == 'FDS'
                        # Es diciembre duro si algún día de la jornada es festivo duro
                        es_critico = any((d.month == 12 and d.day in [24, 25, 31]) or (d.month == 1 and d.day == 1) for d in b['fechas'])
                        
                        # -- Filtro de Candidatos Elegibles para TODA la jornada --
                        elegibles_ing = []
                        elegibles_sup = []
                        
                        for ing in lista_ingenieros:
                            ingreso = datetime.strptime(ing.get("fecha_ingreso", "2024-01-01")[:10], "%Y-%m-%d").date()
                            salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                            
                            # Debe estar activo todo el bloque
                            if not all(ingreso <= d <= salida for d in b['fechas']): continue
                            # No debe estar en vacaciones en ningún día del bloque
                            if any(any(datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date() <= d <= datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date() for v in lista_vacaciones if v["ingeniero_id"] == ing["id"]) for d in b['fechas']): continue
                            # FDS Check
                            if es_fds and not ing.get("permite_fin_semana", True): continue
                            # Cooldown: Han pasado 2 días desde su última asignación?
                            if (b['fechas'][0] - ultimo_turno[ing["id"]]).days <= 2: continue
                            
                            if "Supervisor" in ing.get("rol", ""): elegibles_sup.append(ing)
                            else: elegibles_ing.append(ing)
                                
                        # Función auxiliar para elegir a los mejores N
                        def seleccionar_mejores(pool, cantidad):
                            if es_critico:
                                pool.sort(key=lambda x: (not x.get("es_nuevo", False), conteo_turnos[x["id"]] / dias_potenciales[x["id"]]))
                            else:
                                pool.sort(key=lambda x: conteo_turnos[x["id"]] / dias_potenciales[x["id"]])
                            return pool[:cantidad]

                        # REGLA DE ROLES: Semana (1 Lider, 1 Apoyo), FDS (1 Lider, 2 Apoyos, 1 Supervisor)
                        if b['tipo'] == 'SEMANA':
                            elegidos_ing = seleccionar_mejores(elegibles_ing, 2)
                            roles_asignar = ["Líder", "Apoyo"]
                        else:
                            elegidos_ing = seleccionar_mejores(elegibles_ing, 3)
                            roles_asignar = ["Líder", "Apoyo 1", "Apoyo 2"]
                            elegidos_sup = seleccionar_mejores(elegibles_sup, 1)
                            
                            # Añadir el supervisor a la escritura final
                            for sup in elegidos_sup:
                                conteo_turnos[sup["id"]] += len(b['fechas'])
                                ultimo_turno[sup["id"]] = b['fechas'][-1]
                                for dia in b['fechas']:
                                    registros_nuevos.append({"fecha": str(dia), "ingeniero_id": sup["id"], "tipo_dia": f"FDS (Supervisor)"})

                        # Añadir los ingenieros con su respectivo rol interno
                        for i, ing in enumerate(elegidos_ing):
                            rol_asignado = roles_asignar[i] if i < len(roles_asignar) else "Apoyo"
                            conteo_turnos[ing["id"]] += len(b['fechas'])
                            ultimo_turno[ing["id"]] = b['fechas'][-1] # Su último turno es el último día de esta jornada
                            
                            for dia in b['fechas']:
                                registros_nuevos.append({"fecha": str(dia), "ingeniero_id": ing["id"], "tipo_dia": f"{b['tipo']} ({rol_asignado})"})
                    
                    if registros_nuevos:
                        supabase.table("asignaciones").insert(registros_nuevos).execute()
                        st.success(f"✅ ¡Se han procesado {len(bloques)} Jornadas Operativas exitosamente!")
                        st.balloons()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error procesando el motor: {e}")
    else:
        st.warning("No hay equipo registrado.")

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
        # Limpiar categoría base para las gráficas
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
