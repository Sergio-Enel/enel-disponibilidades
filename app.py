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
    res = supabase.table("ingenieros").select("*").execute()
    return res.data

def obtener_vacaciones():
    res = supabase.table("vacaciones").select("*").execute()
    return res.data

def obtener_asignaciones():
    res = supabase.table("asignaciones").select("*").execute()
    return res.data

# ==========================================
# ⚡ INTERFAZ PRINCIPAL
# ==========================================
st.title("⚡ Sistema de Asignación de Disponibilidades - ENEL")
st.markdown("Matriz de control de turnos críticos, ausentismos y equidad operativa.")
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

# Diccionarios rápidos para búsquedas
dict_nombres_ing = {ing["id"]: ing["nombre"] for ing in lista_ingenieros}
dict_ing_completo = {ing["id"]: ing for ing in lista_ingenieros}

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
            
            # Mapear Vacaciones con sus motivos reales
            for vac in lista_vacaciones:
                nom_ing = dict_nombres_ing.get(vac["ingeniero_id"])
                if nom_ing in matriz_df.index:
                    v_ini, v_fin = datetime.strptime(vac["fecha_inicio"], "%Y-%m-%d"), datetime.strptime(vac["fecha_fin"], "%Y-%m-%d")
                    dia_aux = v_ini
                    while dia_aux <= v_fin:
                        str_dia = dia_aux.strftime("%Y-%m-%d")
                        # Muestra el motivo exacto guardado
                        if str_dia in matriz_df.columns: matriz_df.at[nom_ing, str_dia] = f"🌴 {vac.get('motivo', 'Ausente')}"
                        dia_aux += timedelta(days=1)
                        
            # Mapear Asignaciones
            for asig in lista_asignaciones:
                nom_ing = dict_nombres_ing.get(asig["ingeniero_id"])
                str_fecha = asig["fecha"]
                if nom_ing in matriz_df.index and str_fecha in matriz_df.columns:
                    if "🌴" in matriz_df.at[nom_ing, str_fecha]: 
                        matriz_df.at[nom_ing, str_fecha] = "⚠️ CRÍTICO (Solapamiento)"
                    else: 
                        matriz_df.at[nom_ing, str_fecha] = f"⚡ DISPONIBLE"
            
            matriz_df.columns = nombres_columnas_bonitas
            st.dataframe(matriz_df, use_container_width=True)

        else:
            # Vista Calendario interactivo
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
                                st.markdown(f"<div style='background-color: #ffebee; color: #c62828; padding: 4px; border-radius: 4px; font-size: 11px; margin-bottom: 2px;' title='{v.get('motivo', 'Ausente')}'>🌴 {dict_nombres_ing.get(v['ingeniero_id'], '')}</div>", unsafe_allow_html=True)
                            for a in turnos_hoy:
                                st.markdown(f"<div style='background-color: #e8f5e9; color: #2e7d32; padding: 4px; border-radius: 4px; font-size: 11px; margin-bottom: 2px; font-weight: bold;'>⚡ {dict_nombres_ing.get(a['ingeniero_id'], '')}</div>", unsafe_allow_html=True)
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
            rol = st.selectbox("Rol:", ["Lider centro de control", "Ingeniero de apoyo", "Supervisor"])
            permite_fds = st.radio("¿Turnos Fin de Semana?", [True, False], format_func=lambda x: "Sí" if x else "No (Restringido)")
            es_nuevo = st.radio("¿Es nuevo? (Prioridad Diciembre)", [False, True], format_func=lambda x: "Sí" if x else "No")
            
            # --- MANEJO DE CASOS ESPECIALES DE CONTRATO ---
            st.markdown("---")
            st.markdown("**Vigencia en el Equipo**")
            f_ingreso = st.date_input("Fecha de Ingreso al equipo", datetime(2024, 1, 1))
            
            tipo_contrato = st.radio("Tipo de Contrato:", ["Término Indefinido", "Caso Especial (Tiene fecha de salida)"])
            
            if tipo_contrato == "Caso Especial (Tiene fecha de salida)":
                f_salida = st.date_input("Fecha de Salida programada", datetime.now().date() + timedelta(days=30))
                str_f_salida = str(f_salida)
            else:
                str_f_salida = "2099-12-31" # Representa contrato indefinido
            
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
                else:
                    st.error("Por favor ingresa un nombre.")

    with col_tabla:
        st.subheader("Personal Activo y Vigencias")
        if len(lista_ingenieros) > 0:
            df_ing = pd.DataFrame(lista_ingenieros)
            if 'fecha_ingreso' not in df_ing.columns: df_ing['fecha_ingreso'] = "2024-01-01"
            if 'fecha_salida' not in df_ing.columns: df_ing['fecha_salida'] = "2099-12-31"
            
            # Cambiamos el 2099-12-31 por "Indefinido" solo para la visualización visual
            df_ing['Vigencia Hasta'] = df_ing['fecha_salida'].apply(lambda x: "Indefinido" if "2099" in str(x) else x)
            
            df_show = df_ing[["id", "nombre", "rol", "es_nuevo", "fecha_ingreso", "Vigencia Hasta"]].copy()
            df_show.columns = ["ID", "Nombre", "Rol", "¿Nuevo?", "Ingreso", "Salida"]
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
            # --- ELIMINACIÓN POR LISTA DESPLEGABLE ---
            st.markdown("---")
            st.subheader("❌ Eliminar Trabajador")
            ing_a_eliminar = st.selectbox("Selecciona el profesional a eliminar de la base de datos:", lista_ingenieros, format_func=lambda x: f"{x['id']} - {x['nombre']}")
            
            if st.button("🗑️ Eliminar permanentemente"):
                if ing_a_eliminar:
                    id_eliminar = ing_a_eliminar["id"]
                    try:
                        supabase.table("vacaciones").delete().eq("ingeniero_id", id_eliminar).execute()
                        supabase.table("asignaciones").delete().eq("ingeniero_id", id_eliminar).execute()
                        supabase.table("ingenieros").delete().eq("id", id_eliminar).execute()
                        st.success(f"Registro eliminado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar: {e}")
        else:
            st.info("ℹ️ No hay personal registrado.")

# ==========================================
# 🌴 PESTAÑA 3: AUSENTISMOS Y MOTIVOS
# ==========================================
with tab3:
    st.header("🌴 Registro de Vacaciones y Ausentismos")
    
    if len(lista_ingenieros) > 0:
        col_v1, col_v2 = st.columns([1, 2])
        with col_v1:
            st.subheader("Bloquear Fechas")
            with st.form("form_vac"):
                # Lista para seleccionar
                ing_ausente = st.selectbox("Seleccionar Profesional:", lista_ingenieros, format_func=lambda x: x["nombre"])
                # MOTIVO RESTAURADO
                motivo_ausentismo = st.selectbox("Tipo de Ausentismo:", ["Vacaciones", "Incapacidad Médica", "Permiso Empresa", "Licencia", "Otro"])
                
                fechas = st.date_input("Rango de Fechas (Inicio - Fin):", [])
                
                if st.form_submit_button("📅 Bloquear Fechas"):
                    if len(fechas) == 2:
                        try:
                            supabase.table("vacaciones").insert({
                                "ingeniero_id": ing_ausente["id"], 
                                "fecha_inicio": str(fechas[0]), 
                                "fecha_fin": str(fechas[1]), 
                                "motivo": motivo_ausentismo
                            }).execute()
                            st.success(f"Fechas bloqueadas para {ing_ausente['nombre']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.warning("Selecciona una fecha de inicio y una fecha de fin.")
                        
        with col_v2:
            st.subheader("Historial de Ausentismos")
            if len(lista_vacaciones) > 0:
                df_vac = pd.DataFrame(lista_vacaciones)
                df_vac['Profesional'] = df_vac['ingeniero_id'].map(dict_nombres_ing)
                
                # Asegurar que la columna motivo exista si venimos de versiones viejas
                if 'motivo' not in df_vac.columns: df_vac['motivo'] = "Vacaciones"
                
                df_show_vac = df_vac[["id", "Profesional", "motivo", "fecha_inicio", "fecha_fin"]].copy()
                df_show_vac.columns = ["ID", "Profesional", "Motivo", "Fecha Inicio", "Fecha Fin"]
                df_show_vac = df_show_vac.sort_values(by="Fecha Inicio", ascending=False)
                
                st.dataframe(df_show_vac, hide_index=True, use_container_width=True)
                
                # --- ELIMINACIÓN POR LISTA DESPLEGABLE ---
                st.markdown("---")
                vac_a_eliminar = st.selectbox("Selecciona el ausentismo a cancelar:", lista_vacaciones, format_func=lambda x: f"ID {x['id']} - {dict_nombres_ing.get(x['ingeniero_id'])} ({x.get('motivo', '')})")
                if st.button("❌ Cancelar Ausentismo"):
                    if vac_a_eliminar:
                        try:
                            supabase.table("vacaciones").delete().eq("id", vac_a_eliminar["id"]).execute()
                            st.success("Ausentismo cancelado liberando las fechas.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("No hay ausentismos programados.")
    else:
         st.info("⚠️ Primero debes registrar al menos un trabajador.")

# ==========================================
# ⚙️ PESTAÑA 4: MOTOR ALGORÍTMICO PROPORCIONAL
# ==========================================
with tab4:
    st.header("⚙️ Motor Algorítmico de Equidad Proporcional")
    
    if len(lista_ingenieros) > 0:
        col_a1, col_a2 = st.columns(2)
        f_inicio_calc = col_a1.date_input("Fecha Inicio Semestre", datetime.now().date())
        f_fin_calc = col_a2.date_input("Fecha Fin Semestre", datetime.now().date() + timedelta(days=180))
        
        st.info("""**Reglas de Inteligencia Activas:**
        1. **Vigencia Segura:** Ignora a quienes salen de la empresa (casos especiales) o no han entrado.
        2. **Anti-Sobrecarga (Nuevos):** Asigna basado en *Porcentaje de Ocupación*, no en totales absolutos.
        3. **Cooldown:** Asegura mínimo 2 días de descanso entre turnos para evitar fatiga extrema.""")
        
        if st.button("🚀 Ejecutar y Optimizar Matriz"):
            with st.spinner("Balanceando cargas proporcionales..."):
                try:
                    # Limpiar periodo
                    supabase.table("asignaciones").delete().gte("fecha", str(f_inicio_calc)).lte("fecha", str(f_fin_calc)).execute()
                    
                    dias_totales = (f_fin_calc - f_inicio_calc).days + 1
                    lista_fechas = [f_inicio_calc + timedelta(days=x) for x in range(dias_totales)]
                    
                    # Variables de control
                    conteo_turnos = {ing["id"]: 0 for ing in lista_ingenieros}
                    ultimo_turno = {ing["id"]: f_inicio_calc - timedelta(days=10) for ing in lista_ingenieros} # Cooldown inicial
                    
                    # Calcular días activos potenciales (para la proporción)
                    dias_potenciales = {}
                    for ing in lista_ingenieros:
                        ingreso = datetime.strptime(ing.get("fecha_ingreso", "2024-01-01")[:10], "%Y-%m-%d").date()
                        salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                        # Cuántos días del semestre caen en su periodo de vigencia
                        dias_solapados = sum(1 for d in lista_fechas if ingreso <= d <= salida)
                        dias_potenciales[ing["id"]] = max(1, dias_solapados) # Evitar división por cero
                    
                    registros_nuevos = []
                    
                    for f_actual in lista_fechas:
                        es_fds = f_actual.weekday() in [5, 6]
                        es_critico_dic = (f_actual.month == 12 and f_actual.day in [24, 25, 31]) or (f_actual.month == 1 and f_actual.day == 1)
                        
                        ingenieros_elegibles = []
                        
                        for ing in lista_ingenieros:
                            # 1. Vigencia de contrato
                            ingreso = datetime.strptime(ing.get("fecha_ingreso", "2024-01-01")[:10], "%Y-%m-%d").date()
                            salida = datetime.strptime(ing.get("fecha_salida", "2099-12-31")[:10], "%Y-%m-%d").date()
                            if not (ingreso <= f_actual <= salida): continue
                            
                            # 2. Vacaciones y ausentismos
                            en_vac = any(datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date() <= f_actual <= datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date() for v in lista_vacaciones if v["ingeniero_id"] == ing["id"])
                            if en_vac: continue
                            
                            # 3. Restricción FDS
                            if es_fds and not ing.get("permite_fin_semana", True): continue
                            
                            # 4. Cooldown (Descanso de 2 días)
                            if (f_actual - ultimo_turno[ing["id"]]).days <= 2: continue
                                
                            ingenieros_elegibles.append(ing)
                        
                        # Rescate de emergencia
                        if not ingenieros_elegibles:
                            ingenieros_elegibles = [ing for ing in lista_ingenieros if ing.get("permite_fin_semana") or not es_fds]
                        
                        # Selección
                        if es_critico_dic:
                            pool = [i for i in ingenieros_elegibles if i.get("es_nuevo", False)] or ingenieros_elegibles
                        else:
                            pool = ingenieros_elegibles
                        
                        # Selección por MENOR tasa de ocupación
                        seleccionado = min(pool, key=lambda x: conteo_turnos[x["id"]] / dias_potenciales[x["id"]])
                        
                        conteo_turnos[seleccionado["id"]] += 1
                        ultimo_turno[seleccionado["id"]] = f_actual
                        
                        registros_nuevos.append({"fecha": str(f_actual), "ingeniero_id": seleccionado["id"], "tipo_dia": "FDS" if es_fds else "SEMANA"})
                    
                    if registros_nuevos:
                        supabase.table("asignaciones").insert(registros_nuevos).execute()
                        st.success("✅ Matriz de equidad generada y guardada exitosamente.")
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
        
        st.subheader("⚖️ Distribución Total de Turnos por Profesional")
        conteo_df = df_asig.groupby(['Nombre', 'tipo_dia']).size().reset_index(name='Cantidad')
        
        fig_bar = px.bar(
            conteo_df, 
            x='Nombre', y='Cantidad', color='tipo_dia',
            title="Cantidad de Turnos Asignados (Semana vs FDS)",
            labels={"tipo_dia": "Tipo de Día", "Cantidad": "N° Turnos"},
            color_discrete_map={"SEMANA": "#1f77b4", "FDS": "#ff7f0e"},
            text_auto=True
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("🔥 Carga de Fines de Semana")
            df_fds = df_asig[df_asig['tipo_dia'] == 'FDS']
            fig_pie = px.pie(df_fds, names='Nombre', title="¿Quién hace más Fines de Semana?", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_g2:
            st.subheader("📊 Resumen Tabular")
            resumen_pivot = conteo_df.pivot(index='Nombre', columns='tipo_dia', values='Cantidad').fillna(0).astype(int)
            if 'SEMANA' not in resumen_pivot: resumen_pivot['SEMANA'] = 0
            if 'FDS' not in resumen_pivot: resumen_pivot['FDS'] = 0
            
            resumen_pivot['TOTAL'] = resumen_pivot['SEMANA'] + resumen_pivot['FDS']
            st.dataframe(resumen_pivot.sort_values(by="TOTAL", ascending=False), use_container_width=True)
