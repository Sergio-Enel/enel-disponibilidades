import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import holidays # <-- NUEVO: Librería de festivos
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

# Inicializar festivos de Colombia
festivos_colombia = holidays.Colombia(years=[2025, 2026, 2027])

# ==========================================
# ⚡ INTERFAZ PRINCIPAL DE USUARIO
# ==========================================
st.title("⚡ Sistema de Asignación de Disponibilidades - ENEL")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📅 Calendario Matriz", 
    "👥 Gestión del Equipo", 
    "🌴 Vacaciones", 
    "⚙️ Motor Automático",
    "✏️ Ajustes Manuales" # <-- NUEVA PESTAÑA
])

lista_ingenieros = obtener_ingenieros()
lista_vacaciones = obtener_vacaciones()
lista_asignaciones = obtener_asignaciones()
dict_nombres_ing = {ing["id"]: ing["nombre"] for ing in lista_ingenieros}
dict_ids_ing = {ing["nombre"]: ing["id"] for ing in lista_ingenieros}

# ==========================================
# 📅 PESTAÑA 1: CALENDARIO MATRIZ E INTERACTIVO
# ==========================================
with tab1:
    st.header("🗓️ Visualización de Disponibilidad")
    
    if len(lista_ingenieros) == 0:
        st.info("ℹ️ Comienza registrando al equipo en 'Gestión del Equipo'.")
    else:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            año_sel = st.selectbox("Seleccionar Año:", [2025, 2026, 2027], index=0)
        with col_m2:
            mes_sel = st.selectbox("Seleccionar Mes:", list(range(1, 13)), format_func=lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][x - 1])
            
        tipo_vista = st.radio("Formato de visualización:", ["📅 Vista Calendario (Tipo Google)", "🗂️ Vista Matriz (Por Persona)"], horizontal=True)
        
        # VISTA CALENDARIO GOOGLE
        if "Calendario" in tipo_vista:
            cal = calendar.Calendar(firstweekday=0)
            semanas = cal.monthdatescalendar(año_sel, mes_sel)
            dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            
            cols_dias = st.columns(7)
            for i, nombre_dia in enumerate(dias_semana):
                cols_dias[i].markdown(f"<div style='text-align: center; font-weight: bold; background-color: #f0f2f6; padding: 5px; border-radius: 5px;'>{nombre_dia}</div>", unsafe_allow_html=True)
            
            for semana in semanas:
                cols_semana = st.columns(7)
                for i, dia in enumerate(semana):
                    with cols_semana[i]:
                        if dia.month == mes_sel:
                            es_festivo = dia in festivos_colombia
                            color_dia = "red" if es_festivo else "black"
                            st.markdown(f"**<span style='color:{color_dia}'>{dia.day}{' (Festivo)' if es_festivo else ''}</span>**", unsafe_allow_html=True)
                            
                            str_dia = dia.strftime("%Y-%m-%d")
                            turnos_hoy = [a for a in lista_asignaciones if a["fecha"] == str_dia]
                            
                            for v in lista_vacaciones:
                                v_ini = datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date()
                                v_fin = datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date()
                                if v_ini <= dia <= v_fin:
                                    nom_ing = dict_nombres_ing.get(v["ingeniero_id"], "")
                                    st.markdown(f"<div style='background-color: #ffebee; color: #c62828; padding: 3px; border-radius: 3px; font-size: 10px; margin-bottom: 2px;'>🌴 {nom_ing}</div>", unsafe_allow_html=True)
                            
                            for a in turnos_hoy:
                                nom_ing = dict_nombres_ing.get(a["ingeniero_id"], "")
                                rol_str = a.get("rol_turno", "Asignado")
                                st.markdown(f"<div style='background-color: #e8f5e9; color: #2e7d32; padding: 3px; border-radius: 3px; font-size: 10px; margin-bottom: 2px;'>⚡ {nom_ing} ({rol_str})</div>", unsafe_allow_html=True)
                            
                            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color: #ccc;'>{dia.day}</span>", unsafe_allow_html=True)
                st.divider()

        # VISTA MATRIZ
        else:
            primer_dia = datetime(año_sel, mes_sel, 1)
            ultimo_dia = datetime(año_sel, mes_sel+1, 1) - timedelta(days=1) if mes_sel < 12 else datetime(año_sel+1, 1, 1) - timedelta(days=1)
            rango_dias = [primer_dia + timedelta(days=x) for x in range((ultimo_dia - primer_dia).days + 1)]
            
            matriz_df = pd.DataFrame(index=[ing["nombre"] for ing in lista_ingenieros], columns=[d.strftime("%Y-%m-%d") for d in rango_dias]).fillna("—")
            
            for vac in lista_vacaciones:
                nom_ing = dict_nombres_ing.get(vac["ingeniero_id"])
                if nom_ing in matriz_df.index:
                    v_ini = datetime.strptime(vac["fecha_inicio"], "%Y-%m-%d")
                    v_fin = datetime.strptime(vac["fecha_fin"], "%Y-%m-%d")
                    dia_aux = v_ini
                    while dia_aux <= v_fin:
                        if dia_aux.strftime("%Y-%m-%d") in matriz_df.columns:
                            matriz_df.at[nom_ing, dia_aux.strftime("%Y-%m-%d")] = f"🌴 Vacaciones"
                        dia_aux += timedelta(days=1)
                        
            for asig in lista_asignaciones:
                nom_ing = dict_nombres_ing.get(asig["ingeniero_id"])
                if nom_ing in matriz_df.index and asig["fecha"] in matriz_df.columns:
                    matriz_df.at[nom_ing, asig["fecha"]] = f"⚡ {asig.get('rol_turno', 'Turno')}"
            
            matriz_df.columns = [d.strftime("%d-%b") for d in rango_dias]
            st.dataframe(matriz_df, use_container_width=True)

# ==========================================
# 👥 PESTAÑA 2: GESTIÓN DE EQUIPO
# ==========================================
with tab2:
    col_form, col_tabla = st.columns([1, 2])
    with col_form:
        st.subheader("Registrar Personal")
        with st.form("form_ingeniero"):
            nombre = st.text_input("Nombre Completo:").strip().upper()
            # ROLES SIMPLIFICADOS PARA LA LÓGICA
            rol = st.selectbox("Rol Principal:", ["Ingeniero (Líder/Apoyo)", "Supervisor"])
            permite_fds = st.checkbox("¿Permitir Fines de Semana?", value=True)
            es_nuevo = st.checkbox("¿Es personal nuevo? (Prioridad dic/ene)")
            
            if st.form_submit_button("💾 Guardar"):
                if nombre and not any(ing["nombre"] == nombre for ing in lista_ingenieros):
                    supabase.table("ingenieros").insert({"nombre": nombre, "rol": rol, "permite_fin_semana": permite_fds, "es_nuevo": es_nuevo}).execute()
                    st.success("Guardado!")
                    st.rerun()

    with col_tabla:
        st.subheader("Personal Registrado")
        if lista_ingenieros:
            st.dataframe(pd.DataFrame(lista_ingenieros)[["id", "nombre", "rol", "permite_fin_semana"]], hide_index=True)
            
            st.markdown("---")
            st.subheader("❌ Eliminar Personal")
            # MEJORA: Lista desplegable para eliminar
            nom_borrar = st.selectbox("Selecciona la persona a eliminar:", [ing["nombre"] for ing in lista_ingenieros])
            if st.button("🗑️ Eliminar permanentemente"):
                id_borrar = dict_ids_ing[nom_borrar]
                supabase.table("vacaciones").delete().eq("ingeniero_id", id_borrar).execute()
                supabase.table("asignaciones").delete().eq("ingeniero_id", id_borrar).execute()
                supabase.table("ingenieros").delete().eq("id", id_borrar).execute()
                st.success("Eliminado correctamente.")
                st.rerun()

# ==========================================
# 🌴 PESTAÑA 3: VACACIONES
# ==========================================
with tab3:
    if lista_ingenieros:
        with st.form("form_vac"):
            nom_sel = st.selectbox("Profesional:", list(dict_ids_ing.keys()))
            fechas = st.date_input("Rango (Inicio - Fin):", [])
            if st.form_submit_button("Bloquear Fechas") and len(fechas) == 2:
                supabase.table("vacaciones").insert({"ingeniero_id": dict_ids_ing[nom_sel], "fecha_inicio": str(fechas[0]), "fecha_fin": str(fechas[1]), "motivo": "Ausentismo"}).execute()
                st.success("Guardado")
                st.rerun()

# ==========================================
# ⚙️ PESTAÑA 4: MOTOR AUTOMÁTICO
# ==========================================
with tab4:
    st.markdown("### 🚀 Generación de Turnos (Aplica Reglas de Enel y Festivos)")
    col1, col2 = st.columns(2)
    with col1: f_inicio = st.date_input("Inicio de periodo:")
    with col2: f_fin = st.date_input("Fin de periodo:")
    
    if st.button("Generar Malla Automática"):
        with st.spinner("Calculando malla..."):
            supabase.table("asignaciones").delete().gte("fecha", str(f_inicio)).lte("fecha", str(f_fin)).execute()
            
            dias_totales = (f_fin - f_inicio).days + 1
            conteo_turnos = {ing["id"]: 0 for ing in lista_ingenieros}
            registros = []
            
            for i in range(dias_totales):
                f_act = f_inicio + timedelta(days=i)
                str_f_act = str(f_act)
                
                # Regla: Fines de semana (Viernes=4, Sab=5, Dom=6) o Festivos
                es_dia_fuerte = f_act.weekday() >= 4 or f_act in festivos_colombia
                es_diciembre = f_act.month == 12 or (f_act.month == 1 and f_act.day == 1)
                
                # Filtrar disponibles
                elegibles = []
                for ing in lista_ingenieros:
                    en_vac = any((datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date() <= f_act <= datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date()) and v["ingeniero_id"] == ing["id"] for v in lista_vacaciones)
                    if not en_vac and (not es_dia_fuerte or ing["permite_fin_semana"]):
                        elegibles.append(ing)
                        
                # Dividir pools
                pool_sup = [i for i in elegibles if "Supervisor" in i["rol"]]
                pool_ing = [i for i in elegibles if "Ingeniero" in i["rol"]]
                
                # Ordenar por el que menos turnos tenga (Prioridad nuevos en dic)
                if es_diciembre:
                    pool_ing.sort(key=lambda x: (not x["es_nuevo"], conteo_turnos[x["id"]]))
                else:
                    pool_ing.sort(key=lambda x: conteo_turnos[x["id"]])
                pool_sup.sort(key=lambda x: conteo_turnos[x["id"]])
                
                # ASIGNAR SEGÚN EL DÍA
                if es_dia_fuerte:
                    # 1 Lider, 2 Apoyos, 1 Supervisor
                    if len(pool_ing) >= 3:
                        lider = pool_ing[0]
                        apoyos = [pool_ing[1], pool_ing[2]]
                        registros.append({"fecha": str_f_act, "ingeniero_id": lider["id"], "tipo_dia": "FDS/FESTIVO", "rol_turno": "Líder"})
                        for ap in apoyos: registros.append({"fecha": str_f_act, "ingeniero_id": ap["id"], "tipo_dia": "FDS/FESTIVO", "rol_turno": "Apoyo"})
                        conteo_turnos[lider["id"]] += 1
                        for ap in apoyos: conteo_turnos[ap["id"]] += 1
                    
                    if len(pool_sup) >= 1:
                        sup = pool_sup[0]
                        registros.append({"fecha": str_f_act, "ingeniero_id": sup["id"], "tipo_dia": "FDS/FESTIVO", "rol_turno": "Supervisor"})
                        conteo_turnos[sup["id"]] += 1
                else:
                    # 1 Lider, 1 Apoyo
                    if len(pool_ing) >= 2:
                        lider = pool_ing[0]
                        apoyo = pool_ing[1]
                        registros.append({"fecha": str_f_act, "ingeniero_id": lider["id"], "tipo_dia": "SEMANA", "rol_turno": "Líder"})
                        registros.append({"fecha": str_f_act, "ingeniero_id": apoyo["id"], "tipo_dia": "SEMANA", "rol_turno": "Apoyo"})
                        conteo_turnos[lider["id"]] += 1
                        conteo_turnos[apoyo["id"]] += 1

            if registros:
                supabase.table("asignaciones").insert(registros).execute()
                st.success("Malla generada con éxito!")
                st.rerun()

# ==========================================
# ✏️ PESTAÑA 5: AJUSTES MANUALES (NUEVO)
# ==========================================
with tab5:
    st.header("✏️ Modificaciones Manuales y Relevos")
    st.markdown("Útil para casos imprevistos o cambios de turno uno a uno.")
    
    if not lista_ingenieros:
        st.warning("No hay ingenieros registrados.")
    else:
        fecha_ajuste = st.date_input("1. Selecciona el día a modificar:")
        str_fecha = str(fecha_ajuste)
        
        turnos_dia = [a for a in lista_asignaciones if a["fecha"] == str_fecha]
        
        st.subheader(f"Turnos actuales para el {str_fecha}")
        if not turnos_dia:
            st.info("No hay turnos asignados este día.")
        else:
            for t in turnos_dia:
                nom = dict_nombres_ing.get(t["ingeniero_id"], "Desconocido")
                colA, colB = st.columns([3, 1])
                colA.markdown(f"**{nom}** - Rol: *{t.get('rol_turno', 'N/A')}*")
                if colB.button("❌ Quitar", key=f"del_{t['id']}"):
                    supabase.table("asignaciones").delete().eq("id", t["id"]).execute()
                    st.rerun()
                    
        st.markdown("---")
        st.subheader("2. Agregar suplente o nuevo turno")
        with st.form("form_manual"):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                nuevo_nom = st.selectbox("Seleccionar Trabajador:", list(dict_ids_ing.keys()))
            with col_m2:
                nuevo_rol = st.selectbox("Rol a cubrir:", ["Líder", "Apoyo", "Supervisor"])
            
            if st.form_submit_button("➕ Agregar a este día"):
                supabase.table("asignaciones").insert({
                    "fecha": str_fecha,
                    "ingeniero_id": dict_ids_ing[nuevo_nom],
                    "tipo_dia": "MANUAL",
                    "rol_turno": nuevo_rol
                }).execute()
                st.success("Turno agregado manualmente.")
                st.rerun()
