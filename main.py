import datetime as dt
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Sistema de Control de Asistencia y Turnos",
    page_icon="📅",
    layout="wide",
)

DB_NAME = "asistencia_turnos.db"


# --- INICIALIZACIÓN DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabla de Usuarios
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nomina TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """
    )

    # Tabla de Rol de Asistencia
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rol_asistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            fecha TEXT NOT NULL,
            turno TEXT NOT NULL
        )
    """
    )

    # Tabla de Solicitudes de Vacaciones
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS solicitudes_vacaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solicitante TEXT NOT NULL,
            fechas TEXT NOT NULL,
            estado TEXT NOT NULL,
            autorizado_por TEXT,
            fecha_autorizacion TEXT,
            hora_autorizacion TEXT
        )
    """
    )

    # Insertar usuario administrador por defecto si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """
            INSERT INTO usuarios (nomina, nombre, rol, password)
            VALUES ('1001', 'Angel Alexis', 'Admin', 'admin123')
        """
        )

    conn.commit()
    conn.close()


init_db()

# --- MANEJO DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""
if "rol" not in st.session_state:
    st.session_state.rol = ""

# --- LOGIN ---
if not st.session_state.autenticado:
    st.title("🔐 Iniciar Sesión")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        nomina_input = st.text_input("Nómina:")
        pass_input = st.text_input("Contraseña:", type="password")

        if st.button("Ingresar", type="primary", use_container_width=True):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nombre, rol FROM usuarios WHERE nomina = ? AND password = ?",
                (nomina_input, pass_input),
            )
            user_data = cursor.fetchone()
            conn.close()

            if user_data:
                st.session_state.autenticado = True
                st.session_state.usuario = user_data[0]
                st.session_state.rol = user_data[1]
                st.rerun()
            else:
                st.error("Nómina o contraseña incorrectas.")
    st.stop()

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.title(f"👤 {st.session_state.usuario}")
st.sidebar.caption(f"Rol: {st.session_state.rol}")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.usuario = ""
    st.session_state.rol = ""
    st.rerun()

# Flags de permisos
es_angel = st.session_state.usuario.lower().startswith("angel") or st.session_state.rol == "Admin"
es_autorizado_especial = (
    st.session_state.rol in ["Admin", "Supervisor"] or es_angel
)

# Definición dinámica de Pestañas
pestanias = ["Rol de Asistencia", "Solicitar Vacaciones", "Historial Vacaciones"]
if es_autorizado_especial:
    pestanias.append("Control TE")
if es_angel:
    pestanias.append("Gestión Usuarios")

st.title("📅 Control de Asistencia, Turnos y Vacaciones")
tab_actual = st.tabs(pestanias)

# --- PESTAÑA 1: ROL DE ASISTENCIA ---
with tab_actual[0]:
    st.subheader("📋 Rol de Asistencia Semanal")
    conn = sqlite3.connect(DB_NAME)
    df_rol = pd.read_sql("SELECT * FROM rol_asistencia", conn)
    conn.close()

    if not df_rol.empty:
        st.dataframe(df_rol, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos cargados en el rol de asistencia.")

# --- PESTAÑA 2: SOLICITAR VACACIONES ---
with tab_actual[1]:
    st.subheader("📝 Registrar Solicitud de Vacaciones")
    with st.form("form_vacaciones"):
        empleado_sol = st.text_input("Empleado:", value=st.session_state.usuario)
        rango_vac = st.date_input(
            "Fechas solicitadas:",
            value=[dt.date.today(), dt.date.today() + dt.timedelta(days=1)],
        )
        btn_solicitar = st.form_submit_button("Enviar Solicitud")

        if btn_solicitar:
            if isinstance(rango_vac, (list, tuple)) and len(rango_vac) == 2:
                str_fechas = f"{rango_vac[0].strftime('%Y-%m-%d')} a {rango_vac[1].strftime('%Y-%m-%d')}"
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO solicitudes_vacaciones (solicitante, fechas, estado)
                    VALUES (?, ?, 'Pendiente')
                """,
                    (empleado_sol, str_fechas),
                )
                conn.commit()
                conn.close()
                st.success("¡Solicitud enviada correctamente!")
                st.rerun()
            else:
                st.error("Por favor selecciona un rango válido en el calendario.")

# --- PESTAÑA 3: HISTORIAL VACACIONES ---
with tab_actual[2]:
    st.subheader("📑 Historial y Autorización de Vacaciones")
    conn = sqlite3.connect(DB_NAME)
    df_hist_raw = pd.read_sql("SELECT * FROM solicitudes_vacaciones", conn)
    conn.close()

    if df_hist_raw.empty:
        st.info("No hay registro de solicitudes de vacaciones.")
    else:
        if es_autorizado_especial:
            st.markdown("##### ✏️ Modificar Estados y Dictamen")
            df_editado = st.data_editor(
                df_hist_raw,
                key="editor_historial_vac",
                disabled=[
                    "id",
                    "solicitante",
                    "fechas",
                    "autorizado_por",
                    "fecha_autorizacion",
                    "hora_autorizacion",
                ],
                column_config={
                    "estado": st.column_config.SelectboxColumn(
                        "Estado",
                        options=["Pendiente", "Aprobado", "Rechazado"],
                        required=True,
                    )
                },
                use_container_width=True,
                hide_index=True,
            )

            if st.button("💾 Guardar Cambios en Dictámenes", type="primary"):
                f_act = dt.datetime.now().strftime("%Y-%m-%d")
                h_act = dt.datetime.now().strftime("%H:%M:%S")

                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                for index, row in df_editado.iterrows():
                    cursor.execute(
                        """
                        UPDATE solicitudes_vacaciones
                        SET estado = ?,
                            autorizado_por = ?,
                            fecha_autorizacion = ?,
                            hora_autorizacion = ?
                        WHERE id = ?
                    """,
                        (
                            row["estado"],
                            st.session_state.usuario,
                            f_act,
                            h_act,
                            row["id"],
                        ),
                    )
                conn.commit()
                conn.close()
                st.success("¡Historial y auditoría actualizados correctamente!")
                st.rerun()
        else:
            st.dataframe(df_hist_raw, use_container_width=True, hide_index=True)

    # --- SECCIÓN DE ELIMINACIÓN DE HISTORIAL (1X1 Y COMPLETO CON REINICIO DE ID) ---
    if es_angel and not df_hist_raw.empty:
        st.markdown("---")
        st.subheader("🗑️ Opciones de Eliminación de Historial")

        col_del_single, col_del_all = st.columns(2)

        # Opción 1: Eliminar Registro 1x1
        with col_del_single:
            st.markdown("##### 📌 Eliminar Registro Individual (1x1)")
            opciones_reg = [
                f"ID {r['id']} | {r['solicitante']} | {r['fechas']} ({r['estado']})"
                for _, r in df_hist_raw.iterrows()
            ]
            reg_sel = st.selectbox(
                "Selecciona el registro a borrar:",
                options=["-- Seleccionar --"] + opciones_reg,
                key="sb_del_hist_single",
            )

            if st.button(
                "🗑️ Eliminar Registro Seleccionado",
                type="secondary",
                use_container_width=True,
            ):
                if reg_sel != "-- Seleccionar --":
                    id_target = int(
                        reg_sel.split("ID ")[1].split(" |")[0].strip()
                    )
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM solicitudes_vacaciones WHERE id = ?",
                        (id_target,),
                    )

                    # Si la tabla queda completamente vacía, reiniciamos la secuencia
                    cursor.execute(
                        "SELECT COUNT(*) FROM solicitudes_vacaciones"
                    )
                    total_restantes = cursor.fetchone()[0]
                    if total_restantes == 0:
                        cursor.execute(
                            "DELETE FROM sqlite_sequence WHERE name='solicitudes_vacaciones'"
                        )

                    conn.commit()
                    conn.close()
                    st.success(
                        f"¡Registro ID {id_target} eliminado exitosamente!"
                    )
                    st.rerun()
                else:
                    st.warning("Selecciona un registro válido de la lista.")

        # Opción 2: Eliminar Historial Completo + Reiniciar Autoincremento
        with col_del_all:
            st.markdown("##### ⚠️ Eliminar Historial Completo")
            confirmar_borrado_total = st.checkbox(
                "Confirmar que deseas VACIAR TODO EL HISTORIAL",
                key="chk_confirm_del_all_hist",
            )
            if st.button(
                "🔥 Vaciar Historial Completo",
                type="primary",
                use_container_width=True,
            ):
                if confirmar_borrado_total:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()

                    # Borrar todos los datos de la tabla
                    cursor.execute("DELETE FROM solicitudes_vacaciones")

                    # Borrar la secuencia para que el siguiente ID comience desde 1
                    cursor.execute(
                        "DELETE FROM sqlite_sequence WHERE name='solicitudes_vacaciones'"
                    )

                    conn.commit()
                    conn.close()
                    st.success(
                        "¡Todo el historial fue eliminado y el contador de ID ha sido reiniciado a 1!"
                    )
                    st.rerun()
                else:
                    st.error(
                        "Por favor, marca la casilla de confirmación para proceder con el vaciado total."
                    )

# --- PESTAÑA 4: CONTROL TE ---
if es_autorizado_especial and "Control TE" in pestanias:
    idx_te = pestanias.index("Control TE")
    with tab_actual[idx_te]:
        st.subheader("⏱️ CONTROL Y ACUMULADO DE TIEMPO EXTRA (TE)")

        st.info(
            "**Cálculo automático basado en el Rol de Asistencia:** "
            "Se considera como Tiempo Extra todos los días laborados (`DIA` / `NOCHE`) "
            "que exceden los 4 días estándar por semana (incluyendo aquellos días "
            "programados originalmente con vacaciones pero trabajados)."
        )

        modo_calculo = st.selectbox(
            "Filtrar por modo de cálculo:",
            [
                "Histórico Acumulado General",
                "Días (seleccionar en calendario)",
            ],
        )

        rango_fechas_sel = None
        if modo_calculo == "Días (seleccionar en calendario)":
            col_c1, _ = st.columns([2, 2])
            with col_c1:
                rango_fechas_sel = st.date_input(
                    "Selecciona el rango de días en el calendario:",
                    value=[
                        dt.date.today() - dt.timedelta(days=7),
                        dt.date.today(),
                    ],
                )

        st.markdown("---")
        st.subheader("📊 Resumen de Días de Tiempo Extra")

        conn = sqlite3.connect(DB_NAME)
        df_rol_all = pd.read_sql(
            "SELECT nombre AS Empleado, fecha, turno FROM rol_asistencia",
            conn,
        )
        conn.close()

        if not df_rol_all.empty:
            df_rol_all["es_laborado"] = df_rol_all["turno"].apply(
                lambda t: 1
                if str(t).upper().strip()
                in ["DIA", "NOCHE", "🟩 DIA", "🟦 NOCHE"]
                else 0
            )

            if modo_calculo == "Días (seleccionar en calendario)":
                if (
                    isinstance(rango_fechas_sel, (list, tuple))
                    and len(rango_fechas_sel) == 2
                ):
                    f_inicio, f_fin = rango_fechas_sel
                    f_ini_str = f_inicio.strftime("%Y-%m-%d")
                    f_fin_str = f_fin.strftime("%Y-%m-%d")
                    df_rol_all = df_rol_all[
                        (df_rol_all["fecha"] >= f_ini_str)
                        & (df_rol_all["fecha"] <= f_fin_str)
                    ]
                    rango_label = f"{f_inicio.strftime('%d/%m/%Y')} al {f_fin.strftime('%d/%m/%Y')}"
                else:
                    rango_label = "Rango Seleccionado"
            else:
                rango_label = "Histórico General"

            resumen_list = []
            for emp, grp in df_rol_all.groupby("Empleado"):
                dias_trabajados = grp["es_laborado"].sum()
                dias_te = max(0, dias_trabajados - 4)
                if dias_trabajados > 0:
                    resumen_list.append(
                        {
                            "Empleado": emp,
                            "Periodo / Rango": rango_label,
                            "Días Trabajados": dias_trabajados,
                            "Días de T.E.": dias_te,
                        }
                    )

            df_resumen = pd.DataFrame(resumen_list)

            if not df_resumen.empty:
                st.dataframe(
                    df_resumen,
                    use_container_width=True,
                    hide_index=True,
                )

                df_graf = df_resumen[df_resumen["Días de T.E."] > 0]
                if df_graf.empty:
                    df_graf = df_resumen
                y_col = "Días de T.E."
                y_label = "Total Días T.E."
            else:
                st.info(
                    "No hay registros de asistencia en el periodo seleccionado."
                )
                df_graf = pd.DataFrame()
        else:
            st.info("No hay turnos capturados en el Rol de Asistencia.")
            df_graf = pd.DataFrame()

        if not df_graf.empty:
            st.markdown("---")
            st.subheader("📈 Gráfica de Colaboradores con más Tiempo Extra")

            fig = px.bar(
                df_graf,
                x="Empleado",
                y=y_col,
                color="Empleado",
                text_auto=True,
                labels={"Empleado": "Empleado", y_col: y_label},
            )

            fig.update_traces(
                textposition="inside",
                textfont_size=12,
                textfont_color="black",
            )

            fig.update_layout(
                showlegend=False,
                xaxis_tickangle=-30,
                height=450,
                margin=dict(l=20, r=20, t=30, b=80),
                yaxis=dict(gridcolor="rgba(255, 255, 255, 0.1)"),
            )

            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 5: GESTIÓN DE USUARIOS ---
if es_angel and "Gestión Usuarios" in pestanias:
    idx_users = pestanias.index("Gestión Usuarios")
    with tab_actual[idx_users]:
        st.subheader("⚙️ Administración de Usuarios")

        conn = sqlite3.connect(DB_NAME)
        df_users = pd.read_sql(
            "SELECT id, nomina, nombre, rol, password FROM usuarios", conn
        )
        conn.close()

        df_users_edit = st.data_editor(
            df_users,
            key="editor_usuarios_angel",
            disabled=["id"],
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
        )

        col_guardar, _ = st.columns([2, 2])
        with col_guardar:
            if st.button(
                "💾 Guardar Cambios de Usuarios",
                type="primary",
                use_container_width=True,
            ):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()

                ids_actuales = df_users_edit["id"].dropna().tolist()

                if ids_actuales:
                    placeholders = ",".join(["?"] * len(ids_actuales))
                    cursor.execute(
                        f"DELETE FROM usuarios WHERE id NOT IN ({placeholders})",
                        ids_actuales,
                    )

                for index, row in df_users_edit.iterrows():
                    if pd.notna(row["id"]):
                        cursor.execute(
                            """
                            UPDATE usuarios
                            SET nomina = ?, nombre = ?, rol = ?, password = ?
                            WHERE id = ?
                        """,
                            (
                                row["nomina"],
                                row["nombre"],
                                row["rol"],
                                row["password"],
                                row["id"],
                            ),
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO usuarios (nomina, nombre, rol, password)
                            VALUES (?, ?, ?, ?)
                        """,
                            (
                                row["nomina"],
                                row["nombre"],
                                row["rol"],
                                row["password"],
                            ),
                        )
                conn.commit()
                conn.close()
                st.success("¡Base de datos de usuarios actualizada!")
                st.rerun()

        st.markdown("---")
        st.subheader("🗑️ Eliminar Usuario Específico")

        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            opciones_eliminar = [
                f"{r['nomina']} - {r['nombre']}" for _, r in df_users.iterrows()
            ]
            usuario_a_eliminar = st.selectbox(
                "Selecciona el usuario que deseas eliminar:",
                options=["-- Seleccionar --"] + opciones_eliminar,
            )

        with col_del2:
            st.write("")
            st.write("")
            if st.button(
                "🗑️ Eliminar Usuario",
                type="secondary",
                use_container_width=True,
            ):
                if usuario_a_eliminar != "-- Seleccionar --":
                    nomina_target = usuario_a_eliminar.split(" - ")[0].strip()
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM usuarios WHERE nomina = ?",
                        (nomina_target,),
                    )
                    conn.commit()
                    conn.close()
                    st.success(
                        f"¡Usuario con nómina {nomina_target} eliminado con éxito!"
                    )
                    st.rerun()
                else:
                    st.warning("Selecciona un usuario válido para eliminar.")
