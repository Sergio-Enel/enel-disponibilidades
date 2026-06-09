import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y CONEXIÓN
# ==========================================
st.set_page_config(page_title="Disponibilidades ENEL", page_icon="⚡", layout="wide")

# Conectar a Supabase de forma segura y rápida
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ==========================================
# INTERFAZ DE USUARIO (STREAMLIT)
# ==========================================
st.title("⚡ Sistema de Asignación de Disponibilidades - ENEL")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📅 Calendario Actual", 
    "👥 Gestión de Ingenieros", 
    "🌴 Registro de Vacaciones", 
    "⚙️ Motor de Asignación"
])

# --- PESTAÑA 1: CALENDARIO ---
with tab1:
    st.header("Calendario de Disponibilidades Semestral")
    st.info("🚧 Próximamente: Aquí se visualizará el calendario interactivo generado y el módulo de intercambios (Swaps).")

# --- PESTAÑA 2: INGENIEROS ---
with tab2:
    st.header("Base de Datos del Equipo de Ingenieros")
    
    col_form, col_tabla = st.columns([1, 2])
    
    with col_form:
        st.subheader("Registrar Nuevo Ingeniero")
        with st.form("form_ingeniero", clear_on_submit=True):
            nombre = st.text_input("Nombre Completo del Ingeniero:").strip().upper()
            rol = st.selectbox("Rol en la Empresa:", ["Ingeniero de Terreno", "Coordinador de Operaciones", "Especialista Técnico", "Supervisor"])
            
            permite_fds_opcion = st.radio("¿Se le pueden asignar Fines de Semana?", ["Sí", "No (Restricción por Rol)"])
            es_nuevo_opcion = st.radio("¿Es personal nuevo? (Aplica para turnos críticos de Diciembre)", ["No", "Sí (Asignación prioritaria en festivos duros)"])
            
            # Conversión a booleanos para Supabase
            permite_fds = True if permite_fds_opcion == "Sí" else False
            es_nuevo = True if es_nuevo_opcion == "Sí" else False
            
            btn_guardar = st.form_submit_button("💾 Guardar Ingeniero")
            
            if btn_guardar:
                if nombre:
                    # Comprobar si ya existe en Supabase
                    existe = supabase.table("ingenieros").select("id").eq("nombre", nombre).execute()
                    if len(existe.data) > 0:
                        st.warning(f"⚠️ El ingeniero '{nombre}' ya se encuentra registrado.")
                    else:
                        # Insertar en la nube
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
        
        # Leer datos de Supabase
        respuesta = supabase.table("ingenieros").select("id, nombre, rol, permite_fin_semana, es_nuevo").execute()
        datos = respuesta.data
        
        if len(datos) > 0:
            df_ingenieros = pd.DataFrame(datos)
            
            # Mapear los True/False a texto visual amigable
            df_ingenieros['permite_fin_semana'] = df_ingenieros['permite_fin_semana'].map({True: "✅ Permitido", False: "❌ Restringido"})
            df_ingenieros['es_nuevo'] = df_ingenieros['es_nuevo'].map({True: "⭐ Sí (Prioridad Diciembre)", False: "No"})
            
            # Renombrar columnas para mostrar
            df_ingenieros = df_ingenieros.rename(columns={
                'id': 'ID', 'nombre': 'Nombre', 'rol': 'Rol', 
                'permite_fin_semana': 'Fin de Semana', 'es_nuevo': 'Es Nuevo'
            })
            
            st.dataframe(df_ingenieros, use_container_width=True, hide_index=True)
            
            # Opción para eliminar
            st.markdown("---")
            id_eliminar = st.number_input("Para eliminar un registro, ingresa su ID:", min_value=1, step=1)
            if st.button("❌ Eliminar Ingeniero"):
                try:
                    supabase.table("ingenieros").delete().eq("id", id_eliminar).execute()
                    st.success(f"Ingeniero con ID {id_eliminar} eliminado de la nube.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
        else:
            st.info("ℹ️ No hay ingenieros registrados todavía. Utiliza el formulario de la izquierda.")

# --- PESTAÑA 3: VACACIONES ---
with tab3:
    st.header("Bloqueo Preventivo por Vacaciones")
    st.info("🚧 Próximamente: Módulo conectado a Supabase para vincular fechas libres.")

# --- PESTAÑA 4: ALGORITMO ---
with tab4:
    st.header("Generación de Turnos (Motor de Equidad)")
    st.warning("🚧 Próximamente: Aquí programaremos el algoritmo matemático rotativo semestral.")
