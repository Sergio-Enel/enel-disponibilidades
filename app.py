import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar # <-- Nuevo import para armar la vista tipo Google Calendar
from supabase import create_client, Client

# ==========================================
# ⚡ CONFIGURACIÓN DE PÁGINA Y CONEXIÓN
# ==========================================
st.set_page_config(page_title="Disponibilidades ENEL", page_icon="⚡", layout="wide")

# Inicializar conexión a Supabase con Cache
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ==========================================
# 🛠️ FUNCIONES AUXILIARES DE BASE DE DATOS
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
# ⚡ INTERFAZ PRINCIPAL DE USUARIO
# ==========================================
st.title("⚡ Sistema de Asignación de Disponibilidades - ENEL")
st.markdown("Matriz de control de turnos críticos, ausentismos y equidad operativa.")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📅 Calendario Matriz", 
    "👥 Gestión de Ingenieros", 
    "🌴 Registro de Vacaciones", 
    "⚙️ Motor de Asignación"
])

# Obtener datos globales en cada refresco
lista_ingenieros = obtener_ingenieros()
lista_vacaciones = obtener_vacaciones()
lista_asignaciones = obtener_asignaciones()

# Dict de ingenieros para consultas rápidas
dict_nombres_ing = {ing["id"]: ing["nombre"] for ing in lista_ingenieros}

# ==========================================
# 📅 PESTAÑA 1: CALENDARIO MATRIZ E INTERACTIVO
# ==========================================
with tab1:
    st.header("🗓️ Visualización de Disponibilidad y Ausentismos")
    
    if len(lista_ingenieros) == 0:
        st.info("ℹ️ No hay datos para mostrar. Comienza registrando al equipo en la pestaña 'Gestión de Ingenieros'.")
    else:
        # Selectores de fecha para la visualización del calendario
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            año_sel = st.selectbox("Seleccionar Año:", [2025, 2026, 2027], index=1)
        with col_m2:
            mes_sel = st.selectbox(
                "Seleccionar Mes:", 
                list(range(1, 13)), 
                format_func=lambda x: [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ][x - 1]
            )
            
        st.markdown("---")
        
        # --- SELECTOR DE VISTAS ---
        tipo_vista = st.radio("Selecciona el formato de visualización:", ["🗂️ Vista Matriz (Por Persona)", "📅 Vista Calendario (Tipo Google Calendar)"], horizontal=True)
        
        # VARIABLES COMUNES DE FECHA
        primer_dia = datetime(año_sel, mes_sel, 1)
        if mes_sel == 12:
            ultimo_dia = datetime(año_sel + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = datetime(año_sel, mes_sel + 1, 1) - timedelta(days=1)
            
        rango_dias = [primer_dia + timedelta(days=x) for x in range((ultimo_dia - primer_dia).days + 1)]

        # ==========================================
        # VISTA 1: MATRIZ
        # ==========================================
        if "Matriz" in tipo_vista:
            columnas_dias = [d.strftime("%Y-%m-%d") for d in rango_dias]
            nombres_columnas_bonitas = [d.strftime("%d-%b (%a)") for d in rango_dias]
            
            matriz_df = pd.DataFrame(index=[ing["nombre"] for ing in lista_ingenieros], columns=columnas_dias)
            matriz_df = matriz_df.fillna("—") # Inicializar vacío libre
            
            # 1. Mapear las Vacaciones/Ausentismos
            for vac in lista_vacaciones:
                nom_ing = dict_nombres_ing.get(vac["ingeniero_id"])
                if nom_ing in matriz_df.index:
                    v_ini = datetime.strptime(vac["fecha_inicio"], "%Y-%m-%d")
                    v_fin = datetime.strptime(vac["fecha_fin"], "%Y-%m-%d")
                    
                    dia_aux = v_ini
                    while dia_aux <= v_fin:
                        str_dia = dia_aux.strftime("%Y-%m-%d")
                        if str_dia in matriz_df.columns:
                            matriz_df.at[nom_ing, str_dia] = f"🌴 {vac['motivo']}"
                        dia_aux += timedelta(days=1)
                        
            # 2. Mapear las Asignaciones
            for asig in lista_asignaciones:
                nom_ing = dict_nombres_ing.get(asig["ingeniero_id"])
                str_fecha = asig["fecha"]
                if nom_ing in matriz_df.index and str_fecha in matriz_df.columns:
                    if "🌴" in matriz_df.at[nom_ing, str_fecha]:
                        matriz_df.at[nom_ing, str_fecha] = f"⚠️ CRÍTICO: Turno en {matriz_df.at[nom_ing, str_fecha]}"
                    else:
                        matriz_df.at[nom_ing, str_fecha] = f"⚡ DISPONIBLE ({asig['tipo_dia']})"
            
            matriz_df.columns = nombres_columnas_bonitas
            
            st.markdown("### Vista de Cuadrícula Operativa")
            st.dataframe(matriz_df, use_container_width=True)

        # ==========================================
        # VISTA 2: CALENDARIO (TIPO GOOGLE CALENDAR)
        # ==========================================
        else:
            st.markdown("### Vista Mensual Interactiva")
            
            cal = calendar.Calendar(firstweekday=0) # 0 es Lunes
            semanas = cal.monthdatescalendar(año_sel, mes_sel)
            dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            
            # Dibujar los encabezados de los días
            cols_dias = st.columns(7)
            for i, nombre_dia in enumerate(dias_semana):
                cols_dias[i].markdown(f"<div style='text-align: center; font-weight: bold; background-color: #f0f2f6; padding: 5px; border-radius: 5px;'>{nombre_dia}</div>", unsafe_allow_html=True)
            
            st.write("") # Espaciador
            
            # Dibujar las semanas y sus días
            for semana in semanas:
                cols_semana = st.columns(7)
                for i, dia in enumerate(semana):
                    with cols_semana[i]:
                        if dia.month == mes_sel:
                            # Contenedor visual del día
                            st.markdown(f"**{dia.day}**")
                            
                            # Buscar turnos en este día
                            str_dia = dia.strftime("%Y-%m-%d")
                            turnos_hoy = [a for a in lista_asignaciones if a["fecha"] == str_dia]
                            
                            # Buscar vacaciones en este día
                            vacaciones_hoy = []
                            for v in lista_vacaciones:
                                v_ini = datetime.strptime(v["fecha_inicio"], "%Y-%m-%d").date()
                                v_fin = datetime.strptime(v["fecha_fin"], "%Y-%m-%d").date()
                                if v_ini <= dia <= v_fin:
                                    vacaciones_hoy.append(v)
                            
                            # Mostrar "Eventos" (Vacaciones primero, luego disponibilidades)
                            for v in vacaciones_hoy:
                                nom_ing = dict_nombres_ing.get(v["ingeniero_id"], "Desconocido")
                                # Etiqueta roja pastel para vacaciones
                                st.markdown(f"<div style='background-color: #ffebee; color: #c62828; padding: 4px; border-radius: 4px; font-size: 11px; margin-bottom: 2px;'>🌴 {nom_ing}</div>", unsafe_allow_html=True)
                                
                            for a in turnos_hoy:
                                nom_ing = dict_nombres_ing.get(a["ingeniero_id"], "Desconocido")
                                # Etiqueta verde pastel para disponibilidades
                                st.markdown(f"<div style='background-color: #e8f5e9; color: #2e7d32; padding: 4px; border-radius: 4px; font-size: 11px; margin-bottom: 2px; font-weight: bold;'>⚡ {nom_ing}</div>", unsafe_allow_html=True)
                            
                            st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True) # Espacio para días vacíos
                        else:
                            # Días que pertenecen al mes anterior o siguiente
                            st.markdown(f"<span style='color: #ccc;'>{dia.day}</span>", unsafe_allow_html=True)
                st.divider()

        # Leyenda de estados común para ambas vistas
        st.markdown("""
        **Leyenda de Estados:** * `—` : Personal Libre de turno / Operativo Normal.
        * 🟢 **DISPONIBLE** : Ingeniero asignado a la guardia de emergencias de Enel.
        * 🔴 **Vacaciones / Incapacidad** : Periodo bloqueado.
        """)

# ==========================================
# 👥 PESTAÑA 2: GESTIÓN DE INGENIEROS
# ==========================================
with tab2:
    st.header("👥 Base de Datos del Equipo de Ingenieros")
    
    col_form, col_tabla = st.columns([1, 2])
    
    with col_form:
        st.subheader("Registrar Nuevo Ingeniero")
        with st.form("form_ingeniero", clear_on_submit=True):
            nombre = st.text_input("Nombre Completo del Trabajador:").strip().upper()
            # ROLES ACTUALIZADOS SEGÚN SOLICITUD
            rol = st.selectbox("Rol en la Empresa:", ["lider centro de control", "Ingeniero de apoyo", "supervisor"])
            
            permite_fds_opcion = st.radio("¿Se le pueden asignar Fines de Semana?", ["Sí", "No (Restricción por Rol)"])
            es_nuevo_opcion = st.radio("¿Es personal nuevo? (Aplica para turnos críticos de Diciembre)", ["No", "Sí (Asignación prioritaria en festivos duros)"])
            
            permite_fds = True if permite_fds_opcion == "Sí" else False
            es_nuevo = True if es_nuevo_opcion == "Sí" else False
            
            btn_guardar = st.form_submit_button("💾 Guardar Trabajador")
            
            if btn_guardar:
                if nombre:
                    existe = any(ing["nombre"] == nombre for ing in lista_ingenieros)
                    if existe:
                        st.warning(f"⚠️ El ingeniero '{nombre}' ya se encuentra registrado.")
                    else:
                        try:
                            supabase.table("ingenieros").insert({
                                "nombre": nombre,
                                "rol": rol,
                                "permite_fin_semana": permite_fds,
                                "es_nuevo": es_nuevo
                            }).execute()
                            st.success(f"✅ ¡{nombre} registrado con éxito en la nube!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                else:
                    st.error("❌ Por favor escribe un nombre válido.")
                    
    with col_tabla:
        st.subheader("Equipo Registrado Actualmente")
        
        if len(lista_ingenieros) > 0:
            df_ingenieros = pd.DataFrame(lista_ingenieros)
            
            # Formatear visualmente columnas booleanas
            df_ingenieros['permite_fin_semana'] = df_ingenieros['permite_fin_semana'].map({True: "✅ Permitido", False: "❌ Restringido"})
            df_ingenieros['es_nuevo'] = df_ingenieros['es_nuevo'].map({True: "⭐ Sí", False: "No"})
            
            df_show_ing = df_ingenieros[["id", "nombre", "rol", "permite_fin_semana", "es_nuevo"]].copy()
            df_show_ing.columns = ["ID", "Nombre", "Rol", "Fin de Semana", "Es Nuevo"]
            
            st.dataframe(df_show_ing, use_container_width=True, hide_index=True)
            
            # Módulo de eliminación directa solicitado
            st.markdown("---")
            st.subheader("❌ Eliminar Trabajador de la Base de Datos")
            id_eliminar = st.number_input("Ingresa el ID a borrar:", min_value=1, step=1, key="del_ing")
            if st.button("🗑️ Eliminar permanentemente"):
                try:
                    # Al eliminar, se eliminan en cascada sus asignaciones/vacaciones correspondientes
                    supabase.table("vacaciones").delete().eq("ingeniero_id", id_eliminar).execute()
                    supabase.table("asignaciones").delete().eq("ingeniero_id", id_eliminar).execute()
                    supabase.table("ingenieros").delete().eq("id", id_eliminar).execute()
                    st.success(f"✅ Registro e historial del ID {id_eliminar} eliminados correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
        else:
            st.info("ℹ️ No hay personal registrado todavía.")

# ==========================================
# 🌴 PESTAÑA 3: REGISTRO DE VACACIONES
# ==========================================
with tab3:
    st.header("🌴 Registro de Vacaciones y Ausentismos")
    
    if len(lista_ingenieros) == 0:
        st.info("⚠️ Primero debes registrar al menos un ingeniero en la pestaña 'Gestión de Ingenieros'.")
    else:
        dict_id_ingenieros = {ing["nombre"]: ing["id"] for ing in lista_ingenieros}
        
        col_v1, col_v2 = st.columns([1, 2])
        
        with col_v1:
            st.subheader("Bloquear Fechas Preventivas")
            with st.form("form_vacaciones", clear_on_submit=True):
                nombre_sel = st.selectbox("Seleccionar Profesional:", list(dict_id_ingenieros.keys()))
                motivo = st.selectbox("Tipo de Ausentismo:", ["Vacaciones", "Incapacidad Médica", "Permiso Empresa", "Licencia", "Otro"])
                
                fechas = st.date_input("Rango de Fechas (Inicio - Fin):", [])
                btn_guardar_vac = st.form_submit_button("📅 Bloquear Fechas")
                
                if btn_guardar_vac:
                    if len(fechas) == 2:
                        id_ing = dict_id_ingenieros[nombre_sel]
                        fecha_ini = fechas[0].strftime("%Y-%m-%d")
                        fecha_fin = fechas[1].strftime("%Y-%m-%d")
                        
                        try:
                            supabase.table("vacaciones").insert({
                                "ingeniero_id": id_ing,
                                "fecha_inicio": fecha_ini,
                                "fecha_fin": fecha_fin,
                                "motivo": motivo
                            }).execute()
                            st.success(f"✅ Fechas bloqueadas para {nombre_sel} con éxito.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                    else:
                        st.warning("⚠️ Por favor selecciona una fecha de INICIO y una fecha de FIN en el calendario.")
                        
        with col_v2:
            st.subheader("Historial de Ausentismos Programados")
            
            if len(lista_vacaciones) > 0:
                df_vac = pd.DataFrame(lista_vacaciones)
                df_ing_base = pd.DataFrame(lista_ingenieros)[["id", "nombre"]]
                
                df_merge = pd.merge(df_vac, df_ing_base, left_on="ingeniero_id", right_on="id")
                df_show_vac = df_merge[["id_x", "nombre", "motivo", "fecha_inicio", "fecha_fin"]].copy()
                df_show_vac.columns = ["ID Registro", "Profesional", "Motivo", "Fecha Inicio", "Fecha Fin"]
                df_show_vac = df_show_vac.sort_values(by="Fecha Inicio")
                
                st.dataframe(df_show_vac, use_container_width=True, hide_index=True)
                
                # Módulo de eliminación para vacaciones
                st.markdown("---")
                id_eliminar_vac = st.number_input("Ingresa el ID Registro para liberar fechas:", min_value=1, step=1, key="del_vac")
                if st.button("❌ Cancelar Ausentismo"):
                    try:
                        supabase.table("vacaciones").delete().eq("id", id_eliminar_vac).execute()
                        st.success(f"✅ Fechas liberadas correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.info("ℹ️ No hay vacaciones o ausentismos registrados por el momento.")

# ==========================================
# ⚙️ PESTAÑA 4: MOTOR DE ASIGNACIÓN (ALGORITMO)
# ==========================================
with tab4:
    st.header("⚙️ Motor Algorítmico Rotativo Semestral")
    st.markdown("Este motor distribuye de manera equitativa la disponibilidad diaria, cruzando las reglas de negocio de Enel.")
    
    if len(lista_ingenieros) == 0:
        st.info("⚠️ Se requieren ingenieros registrados para ejecutar el algoritmo.")
    else:
        st.subheader("Configuración del Periodo de Guardias")
        
        col_alg1, col_alg2 = st.columns(2)
        with col_alg1:
            f_inicio_calc = st.date_input("Fecha Inicio Semestre:", datetime.now().date())
        with col_alg2:
            f_fin_calc = st.date_input("Fecha Fin Semestre:", datetime.now().date() + timedelta(days=180))
            
        st.info("💡 **Reglas Aplicadas por el Algoritmo:**\n"
                "1. Respeta rígidamente ausentismos e incapacidades cargadas.\n"
                "2. Omite fines de semana para roles administrativos o técnicos restringidos.\n"
                "3. Balancea la carga total asignando al ingeniero elegible con menos turnos acumulados en el semestre.\n"
                "4. Detecta festivos críticos de Diciembre (Navidad y Año Nuevo) y prioriza al personal con etiqueta 'Es Nuevo'.")
        
        if st.button("🚀 Ejecutar Algoritmo de Equidad (Cargar a la Nube)"):
            if f_inicio_calc > f_fin_calc:
                st.error("❌ La fecha de inicio no puede ser posterior a la fecha de finalización.")
            else:
                with st.spinner("Procesando histórico de datos y optimizando rotación..."):
                    try:
                        supabase.table("asignaciones").delete().gte("fecha", f_inicio_calc.strftime("%Y-%m-%d")).lte("fecha", f_fin_calc.strftime("%Y-%m-%d")).execute()
                    except Exception as e:
                        st.error(f"Error al limpiar datos temporales: {e}")
                    
                    dias_totales = (f_fin_calc - f_inicio_calc).days + 1
                    lista_fechas = [f_inicio_calc + timedelta(days=x) for x in range(dias_totales)]
                    
                    conteo_turnos = {ing["id"]: 0 for ing in lista_ingenieros}
                    registros_nuevos = []
                    
                    for f_actual in lista_fechas:
                        str_f_actual = f_actual.strftime("%Y-%m-%d")
                        es_fds = f_actual.weekday() in [5, 6]
                        tipo_dia = "FDS" if es_fds else "SEMANA"
                        
                        es_critico_diciembre = (f_actual.month == 12 and f_actual.day in [24, 25, 31]) or (f_actual.month == 1 and f_actual.day == 1)
                        
                        ingenieros_elegibles = []
                        
                        for ing in lista_ingenieros:
                            en_vacaciones = False
                            for vac in lista_vacaciones:
                                if vac["ingeniero_id"] == ing["id"]:
                                    v_ini = datetime.strptime(vac["fecha_inicio"], "%Y-%m-%d").date()
                                    v_fin = datetime.strptime(vac["fecha_fin"], "%Y-%m-%d").date()
                                    if v_ini <= f_actual <= v_fin:
                                        en_vacaciones = True
                                        break
                            if en_vacaciones:
                                continue
                            
                            if es_fds and not ing["permite_fin_semana"]:
                                continue
                                
                            ingenieros_elegibles.append(ing)
                        
                        if not ingenieros_elegibles:
                            ingenieros_elegibles = lista_ingenieros
                        
                        if es_critico_diciembre:
                            nuevos_elegibles = [i for i in ingenieros_elegibles if i["es_nuevo"]]
                            cand_pool = nuevos_elegibles if nuevos_elegibles else ingenieros_elegibles
                        else:
                            cand_pool = ingenieros_elegibles
                        
                        seleccionado = min(cand_pool, key=lambda x: conteo_turnos[x["id"]])
                        
                        conteo_turnos[seleccionado["id"]] += 1
                        
                        registros_nuevos.append({
                            "fecha": str_f_actual,
                            "ingeniero_id": seleccionado["id"],
                            "tipo_dia": tipo_dia
                        })
                    
                    if registros_nuevos:
                        try:
                            supabase.table("asignaciones").insert(registros_nuevos).execute()
                            st.success(f"🚀 ¡Algoritmo completado! Se han procesado y cargado {len(registros_nuevos)} guardias exitosamente.")
                            st.balloons()
                            st.rerun()
                        except Exception as err:
                            st.error(f"Error al subir asignaciones a la base de datos: {err}")
