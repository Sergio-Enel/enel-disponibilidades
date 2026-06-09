import streamlit as st
import pandas as pd

# 1. Configuración principal de la página
st.set_page_config(page_title="Disponibilidades ENEL", page_icon="⚡", layout="wide")

# 2. Título Principal
st.title("⚡ Sistema de Asignación de Disponibilidades - ENEL")
st.markdown("---")

# 3. Creación de las Pestañas de Navegación
tab1, tab2, tab3, tab4 = st.tabs([
    "📅 Calendario Actual", 
    "👥 Gestión de Ingenieros", 
    "🌴 Registro de Vacaciones", 
    "⚙️ Motor de Asignación"
])

# --- PESTAÑA 1: CALENDARIO ---
with tab1:
    st.header("Calendario de Disponibilidades")
    st.info("🚧 Aquí mostraremos la tabla final con los turnos asignados de los 6 meses. También pondremos el botón para hacer intercambios (Swaps).")

# --- PESTAÑA 2: INGENIEROS ---
with tab2:
    st.header("Base de Datos del Equipo")
    st.info("🚧 Aquí pondremos el formulario para agregar ingenieros, definir su rol, si permiten fin de semana y si son nuevos (para los turnos de diciembre).")

# --- PESTAÑA 3: VACACIONES ---
with tab3:
    st.header("Bloqueo por Vacaciones")
    st.info("🚧 Aquí registraremos las fechas en las que un ingeniero tiene vacaciones aprobadas para que el sistema no le asigne turnos en esos días.")

# --- PESTAÑA 4: ALGORITMO ---
with tab4:
    st.header("Generación de Semestre")
    st.write("Presiona el botón para que el código asigne los turnos equitativamente respetando las reglas.")
    st.button("Generar Turnos (En construcción...)")
    st.warning("El algoritmo matemático de equidad se programará aquí.")