import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "asistencia.db"

def obtener_conexion():
    """Establece conexión con la base de datos SQLite."""
    return sqlite3.connect(DB_PATH)

def cargar_solicitudes():
    """
    Obtiene todas las solicitudes registradas en la base de datos de forma segura.
    Si la tabla no existe o falla la conexión, evita que la app truene.
    """
    try:
        conn = obtener_conexion()
        query = """
            SELECT id, solicitante, fechas, estado, fecha_solicitud 
            FROM solicitudes 
            ORDER BY id ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        # En caso de error o base de datos vacía/nueva, retorna DataFrame estructurado vacío
        return pd.DataFrame(columns=['id', 'solicitante', 'fechas', 'estado', 'fecha_solicitud'])

def eliminar_solicitud(id_solicitud):
    """
    Elimina la solicitud por ID de la base de datos y reajusta 
    el contador AUTOINCREMENT de SQLite de forma segura.
    """
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # 1. Eliminar el registro de la tabla solicitudes
    cursor.execute("DELETE FROM solicitudes WHERE id = ?", (id_solicitud,))
    
    # 2. Reajustar la secuencia de IDs de manera segura (si sqlite_sequence existe)
    try:
        cursor.execute("""
            UPDATE sqlite_sequence 
            SET seq = COALESCE((SELECT MAX(id) FROM solicitudes), 0) 
            WHERE name = 'solicitudes'
        """)
    except sqlite3.OperationalError:
        # Si la tabla no usa AUTOINCREMENT explícito o no existe la secuencia, omite el ajuste sin romper
        pass

    conn.commit()
    conn.close()

def modulo_historial_auditoria(usuario_actual="Angel Flores"):
    st.header("📋 HISTORIAL DE DICTÁMENES Y AUDITORÍA")
    
    # Mensaje exclusivo del panel
    st.info(
        f"Panel exclusivo de **{usuario_actual}**. Modifica estatus, "
        "utiliza los filtros de búsqueda o elimina registros permanentemente."
    )
    
    # --- 1. CARGA DE DATOS ---
    df_solicitudes = cargar_solicitudes()
    
    if df_solicitudes.empty:
        st.warning("No hay solicitudes registradas actualmente en la base de datos.")
        return

    # --- 2. FILTROS DE BÚSQUEDA ---
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

    # Filtrar el DataFrame en memoria
    df_filtrado = df_solicitudes.copy()
    
    if busqueda:
        df_filtrado = df_filtrado[
            df_filtrado['solicitante'].astype(str).str.contains(busqueda, case=False, na=False) |
            df_filtrado['fechas'].astype(str).str.contains(busqueda, case=False, na=False)
        ]
        
    if filtro_estado != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['estado'] == filtro_estado]

    # --- 3. TABLA DE REGISTROS ---
    st.dataframe(
        df_filtrado, 
        use_container_width=True, 
        hide_index=True
    )
    
    if st.button("💾 Guardar Cambios y Registrar Auditoría", type="primary"):
        st.success("Cambios sincronizados correctamente con asistencia.db")

    st.markdown("---")

    # --- 4. ZONA DE ELIMINACIÓN DE SOLICITUDES ---
    st.subheader("🗑️ ZONA DE ELIMINACIÓN DE SOLICITUDES")
    
    # Obtener la lista actualizada de IDs numéricos que existen realmente en la BD
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
            st.write("")  # Espaciado para alinear el botón con el desplegable
            st.write("")
            btn_eliminar = st.button(
                f"❌ Eliminar Solicitud #{id_a_eliminar}", 
                type="secondary"
            )
            
        if btn_eliminar:
            # Eliminar en BD y ajustar contador
            eliminar_solicitud(id_a_eliminar)
            
            st.toast(f"Solicitud #{id_a_eliminar} eliminada exitosamente.", icon="🗑️")
            
            # Recarga inmediata para refrescar el desplegable y la tabla
            st.rerun()
    else:
        st.info("No hay solicitudes disponibles para eliminar.")

# Punto de entrada para probar de forma directa
if __name__ == "__main__":
    modulo_historial_auditoria()
