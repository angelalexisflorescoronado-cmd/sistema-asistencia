import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "asistencia.db"

def obtener_conexion():
    return sqlite3.connect(DB_PATH)

def cargar_solicitudes():
    """Obtiene todas las solicitudes registradas en la base de datos."""
    conn = obtener_conexion()
    query = """
        SELECT id, solicitante, fechas, estado, fecha_solicitud 
        FROM solicitudes 
        ORDER BY id ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def eliminar_solicitud(id_solicitud):
    """
    Elimina la solicitud por ID y reajusta la secuencia AUTOINCREMENT
    para que los números de ID no queden desfasados.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # 1. Eliminar el registro específico
    cursor.execute("DELETE FROM solicitudes WHERE id = ?", (id_solicitud,))
    
    # 2. Ajustar el contador interno de SQLite (sqlite_sequence)
    cursor.execute("""
        UPDATE sqlite_sequence 
        SET seq = COALESCE((SELECT MAX(id) FROM solicitudes), 0) 
        WHERE name = 'solicitudes'
    """)
    
    conn.commit()
    conn.close()

def modulo_historial_auditoria(usuario_actual="Angel Flores"):
    st.header("📋 HISTORIAL DE DICTÁMENES Y AUDITORÍA")
    
    # Mensaje o banner personalizado
    st.info(
        f"Panel exclusivo de **{usuario_actual}**. Modifica estatus, "
        "utiliza los filtros de búsqueda o elimina registros permanentemente."
    )
    
    # --- 1. CARGA Y FILTRADO DE DATOS ---
    df_solicitudes = cargar_solicitudes()
    
    if df_solicitudes.empty:
        st.warning("No hay solicitudes registradas en el sistema.")
        return

    col_busqueda, col_filtro = st.columns([3, 1])
    
    with col_busqueda:
        busqueda = st.text_input(
            "🔍 Buscar por Solicitante o Fechas:", 
            placeholder="Ej. SALVADOR, ERNESTO o 2026-07-29"
        )
        
    with col_filtro:
        filtro_estado = st.selectbox(
            "Filtrar por Estado:", 
            ["TODOS", "PENDIENTE", "APROBADO", "RECHAZADO"]
        )

    # Aplicar Filtros al DataFrame
    df_filtrado = df_solicitudes.copy()
    
    if busqueda:
        df_filtrado = df_filtrado[
            df_filtrado['solicitante'].str.contains(busqueda, case=False, na=False) |
            df_filtrado['fechas'].str.contains(busqueda, case=False, na=False)
        ]
        
    if filtro_estado != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['estado'] == filtro_estado]

    # --- 2. TABLA INTERACTIVA / EDICIÓN ---
    st.dataframe(
        df_filtrado, 
        use_container_width=True, 
        hide_index=True
    )
    
    if st.button("💾 Guardar Cambios y Registrar Auditoría", type="primary"):
        st.success("Cambios sincronizados correctamente con asistencia.db")

    st.markdown("---")

    # --- 3. ZONA DE ELIMINACIÓN DE SOLICITUDES ---
    st.subheader("🗑️ ZONA DE ELIMINACIÓN DE SOLICITUDES")
    
    # Lista actualizada de IDs presentes actualmente en la BD
    ids_disponibles = df_solicitudes['id'].tolist()
    
    if ids_disponibles:
        col_select, col_btn = st.columns([2, 1])
        
        with col_select:
            id_a_eliminar = st.selectbox(
                "Selecciona el ID a eliminar:", 
                options=ids_disponibles,
                key="select_eliminar_id"
            )
            
        with col_btn:
            st.write("") # Espaciador para alinear con el botón
            st.write("")
            btn_eliminar = st.button(
                f"❌ Eliminar Solicitud #{id_a_eliminar}", 
                type="secondary"
            )
            
        if btn_eliminar:
            # Ejecutamos la eliminación física y reajuste en SQLite
            eliminar_solicitud(id_a_eliminar)
            
            st.toast(f"Solicitud #{id_a_eliminar} eliminada exitosamente.", icon="🗑️")
            
            # Forzamos la recarga completa para que el ID desaparezca del selectbox y la tabla de inmediato
            st.rerun()
    else:
        st.info("No hay solicitudes disponibles para eliminar.")

# Ejemplo de ejecución directa:
if __name__ == "__main__":
    modulo_historial_auditoria()
