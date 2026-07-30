import datetime as dt
from datetime import datetime
import pandas as pd
import plotly.express as px
import sqlite3
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode

DB_NAME = "asistencia.db"


# ----------------------------------------------------------------------
# INICIALIZACIÓN DE BASE DE DATOS
# ----------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nomina TEXT DEFAULT '',
            nombre TEXT UNIQUE NOT NULL,
            rol TEXT NOT NULL DEFAULT 'OPERADOR',
            password TEXT NOT NULL DEFAULT '1234'
        )
    """)

    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN nomina TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    usuarios_base = [
        ("10031976", "JIMENEZ, LUIS RAUL", "OPERADOR", "1234"),
        ("10015510", "PEREZ, RAYMUNDO", "OPERADOR", "1234"),
        ("10016085", "SALVADOR, ERNESTO", "OPERADOR", "1234"),
        ("10019675", "RIVERA, RIGOBERTO", "OPERADOR", "1234"),
        ("10139954", "OSCAR GARCIA HERNANDEZ", "OPERADOR", "1234"),
        ("10007219", "LUIS ANGEL PEREZ", "OPERADOR", "1234"),
        ("10018255", "SERNA, ORLANDO", "OPERADOR", "1234"),
        ("10005881", "SANTOS GUTIERREZ", "OPERADOR", "1234"),
        ("10019578", "LOREDO, JESUS", "OPERADOR", "1234"),
        ("10022967", "SANTIAGO, RICARDO", "OPERADOR", "1234"),
        ("10005894", "ZARAGOZA, GILBERTO", "OPERADOR", "1234"),
        ("10092630", "JUAN CARLOS", "OPERADOR", "1234"),
        ("10076145", "HERNANDEZ, OSCAR", "OPERADOR", "1234"),
        ("10004365", "BENITO, OSCAR", "OPERADOR", "1234"),
        ("10023526", "MARIA DOREYDA PEREZ", "OPERADOR", "1234"),
        ("10019258", "ANTONIO, ROBERTO", "OPERADOR", "1234"),
        ("10015453", "PORTILLO, JOSE JUAN", "OPERADOR", "1234"),
        ("10035253", "ANGEL FLORES", "ADMIN_USUARIOS", "1234"),
        ("10003693", "ALEJANDRO GUARDA", "ADMIN_ROL", "1234"),
        ("10215435", "DONATO BACCO", "ADMIN_ROL", "1234"),
    ]

    for nom, nombre, rol, pwd in usuarios_base:
        cursor.execute(
            """
            INSERT INTO usuarios (nomina, nombre, rol, password) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(nombre) DO UPDATE SET 
                nomina=excluded.nomina,
                rol=excluded.rol
        """,
            (nom, nombre, rol, pwd),
        )

    try:
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_nomina ON"
            " usuarios(nomina)"
        )
    except (sqlite3.OperationalError, sqlite3.IntegrityError):
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rol_asistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            empleado TEXT,
            fecha TEXT NOT NULL,
            turno TEXT DEFAULT '',
            estado TEXT DEFAULT '',
            UNIQUE(nombre, fecha)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitudes_vacaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solicitante TEXT NOT NULL,
            fechas TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'PENDIENTE',
            fecha_solicitud TEXT NOT NULL,
            motivo TEXT DEFAULT '',
            autorizado_por TEXT DEFAULT '',
            fecha_autorizacion TEXT DEFAULT '',
            hora_autorizacion TEXT DEFAULT ''
        )
    """)

    for col in [
        "autorizado_por TEXT DEFAULT ''",
        "fecha_autorizacion TEXT DEFAULT ''",
        "hora_autorizacion TEXT DEFAULT ''",
    ]:
        try:
            cursor.execute(
                f"ALTER TABLE solicitudes_vacaciones ADD COLUMN {col}"
            )
        except sqlite3.OperationalError:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tiempo_extra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado TEXT NOT NULL,
            fecha TEXT NOT NULL,
            horas REAL NOT NULL,
            motivo TEXT DEFAULT '',
            registrado_por TEXT NOT NULL,
            fecha_registro TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ----------------------------------------------------------------------
# FUNCIONES AUXILIARES DE TURNO
# ----------------------------------------------------------------------
def formatear_turno_vista(val):
    val_clean = str(val).strip().upper()
    if val_clean in ["DIA", "🟩 DIA"]:
        return "🟩 DIA"
    elif val_clean in ["NOCHE", "🟦 NOCHE"]:
        return "🟦 NOCHE"
    elif val_clean in ["V", "VACACIONES", "🟨 V"]:
        return "🟨 V"
    elif val_clean == "DESCANSO":
        return "DESCANSO"
    return "-"


def limpiar_turno_bd(val):
    val_str = str(val).upper()
    if "DIA" in val_str:
        return "DIA"
    elif "NOCHE" in val_str:
        return "NOCHE"
    elif "V" in val_str:
        return "V"
    elif "DESCANSO" in val_str:
        return "DESCANSO"
    return "-"


# ----------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y SESIÓN
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Control de Asistencia", page_icon="📅", layout="wide"
)

if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "nomina" not in st.session_state:
    st.session_state.nomina = None
if "rol" not in st.session_state:
    st.session_state.rol = None
if "fecha_ref" not in st.session_state:
    st.session_state.fecha_ref = dt.date.today()

# ----------------------------------------------------------------------
# MÓDULO DE LOGIN
# ----------------------------------------------------------------------
if not st.session_state.usuario:
    st.title("📱 Control de Asistencia y Vacaciones")
    st.subheader("Inicio de Sesión")

    nomina_input = st.text_input("Número de Nómina:").strip()
    password_sel = st.text_input("Contraseña:", type="password")

    if st.button("Ingresar", type="primary", use_container_width=True):
        if nomina_input and password_sel:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nombre, rol, nomina FROM usuarios WHERE nomina = ? AND"
                " password = ?",
                (nomina_input, password_sel),
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                st.session_state.usuario = row[0]
                st.session_state.rol = row[1]
                st.session_state.nomina = row[2]
                st.rerun()
            else:
                st.error("Número de nómina o contraseña incorrectos.")
        else:
            st.warning("Ingresa tu número de nómina y contraseña.")

# ----------------------------------------------------------------------
# INTERFAZ PRINCIPAL DENTRO DE SESIÓN
# ----------------------------------------------------------------------
else:
    with st.sidebar:
        st.write(f"👤 **{st.session_state.usuario}**")
        st.write(f"🆔 Nómina: `{st.session_state.nomina}`")
        st.write(f"🔰 Rol: `{st.session_state.rol}`")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.usuario = None
            st.session_state.nomina = None
            st.session_state.rol = None
            if "msg_exito" in st.session_state:
                del st.session_state["msg_exito"]
            st.rerun()

    st.title("📱 Control de Asistencia y Vacaciones")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM solicitudes_vacaciones WHERE estado = 'PENDIENTE'"
    )
    num_pendientes = cursor.fetchone()[0]
    conn.close()

    st.markdown(
        """
        <style>
        @keyframes parpadeo {
            0% { background-color: rgba(255, 75, 75, 0.8); color: white; }
            50% { background-color: rgba(255, 193, 7, 0.8); color: black; }
            100% { background-color: rgba(255, 75, 75, 0.8); color: white; }
        }
        .notif-parpadeo {
            animation: parpadeo 1.2s infinite;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 15px;
            text-align: center;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
        }
        .alerta-grande {
            background-color: #fff3cd;
            color: #856404;
            padding: 20px;
            border-radius: 8px;
            border-left: 8px solid #ffc107;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 20px;
            box-shadow: 0px 4px 12px rgba(0,0,0,0.15);
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    pestanias = ["Rol de Asistencia", "Solicitar vacaciones"]

    if st.session_state.rol in ["ADMIN_ROL", "ADMIN_USUARIOS"]:
        if num_pendientes > 0:
            texto_notif = f"🔴 Notificaciones ({num_pendientes})"
        else:
            texto_notif = "Notificaciones 🔔"
        pestanias.append(texto_notif)

    nombre_usuario_actual = str(st.session_state.usuario).strip().upper()

    es_autorizado_especial = nombre_usuario_actual in [
        "ANGEL FLORES",
        "ALEJANDRO GUARDA",
        "DONATO BACCO",
    ]
    es_angel = "ANGEL" in nombre_usuario_actual

    if es_autorizado_especial:
        if "Historial" not in pestanias:
            pestanias.append("Historial")
        if "Control TE" not in pestanias:
            pestanias.append("Control TE")

    if es_angel:
        if "Gestión Usuarios" not in pestanias:
            pestanias.append("Gestión Usuarios")

    if (
        st.session_state.rol in ["ADMIN_ROL", "ADMIN_USUARIOS"]
        and num_pendientes > 0
    ):
        st.markdown(
            f'<div class="notif-parpadeo">'
            f"🔔 ¡ATENCIÓN! Tienes {num_pendientes} solicitud(es) de vacaciones"
            f" pendiente(s) por dictaminar."
            f"</div>",
            unsafe_allow_html=True,
        )

    tab_actual = st.tabs(pestanias)

    # --- PESTAÑA 1: ROL DE ASISTENCIA (AG-GRID CON ROW DRAGGING) ---
    with tab_actual[0]:
        st.subheader("Tabla de Asistencia")

        col_atras, col_fecha, col_adelante = st.columns([1, 2, 1])
        with col_atras:
            if st.button("◀ Semana Anterior", use_container_width=True):
                st.session_state.fecha_ref -= dt.timedelta(days=7)
                st.rerun()
        with col_adelante:
            if st.button("Semana Siguiente ▶", use_container_width=True):
                st.session_state.fecha_ref += dt.timedelta(days=7)
                st.rerun()
        with col_fecha:
            st.session_state.fecha_ref = st.date_input(
                "Fecha Base:", st.session_state.fecha_ref
            )

        # Rango de 8 días (Domingo a Domingo)
        offset_domingo = (st.session_state.fecha_ref.weekday() + 1) % 7
        domingo_inicio = st.session_state.fecha_ref - dt.timedelta(days=offset_domingo)
        domingo_fin = domingo_inicio + dt.timedelta(days=7)

        st.info(
            f"📅 Semana del **{domingo_inicio.strftime('%d/%m/%Y')}** al"
            f" **{domingo_fin.strftime('%d/%m/%Y')}**"
        )

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM usuarios ORDER BY nombre ASC")
        todos_empleados = [r[0] for r in cursor.fetchall()]

        es_admin = st.session_state.rol in ["ADMIN_ROL", "ADMIN_USUARIOS"]
        usuario_actual = st.session_state.usuario

        dias_fechas = [
            (domingo_inicio + dt.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(8)
        ]
        nombres_dias_abrev = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

        if not es_admin:
            st.markdown(f"### 👋 Hola, **{usuario_actual}**")
            st.markdown("##### Tus turnos programados para esta semana:")

            partes = usuario_actual.replace(",", "").split()
            posibles_nombres = [usuario_actual]
            if len(partes) >= 2:
                posibles_nombres.append(f"{partes[-1]}, {partes[0]}")
                posibles_nombres.append(f"{partes[1]}, {partes[0]}")

            cols_turnos = st.columns(8)
            for i, f_str in enumerate(dias_fechas):
                placeholders = ",".join(["?"] * len(posibles_nombres))
                cursor.execute(
                    f"""
                    SELECT turno FROM rol_asistencia 
                    WHERE (nombre IN ({placeholders}) OR empleado IN ({placeholders}))
                    AND fecha = ?
                """,
                    (*posibles_nombres, *posibles_nombres, f_str),
                )
                res = cursor.fetchone()
                val_bd = res[0] if res and res[0] else "-"

                with cols_turnos[i]:
                    fecha_fmt = (domingo_inicio + dt.timedelta(days=i)).strftime("%d/%m")
                    st.metric(
                        label=f"{nombres_dias_abrev[i]} {fecha_fmt}",
                        value=formatear_turno_vista(val_bd),
                    )

            st.markdown("---")

        col_filtro, _ = st.columns([2, 2])
        with col_filtro:
            empleado_filtrado = st.selectbox(
                "🔍 Buscar o filtrar por empleado:",
                options=["-- Mostrar Todos --"] + todos_empleados,
                index=0,
            )

        if empleado_filtrado != "-- Mostrar Todos --":
            empleados_a_mostrar = [empleado_filtrado]
        else:
            empleados_a_mostrar = todos_empleados

        encabezados = ["Empleado"] + [
            f"{nombres_dias_abrev[i]} {(domingo_inicio + dt.timedelta(days=i)).strftime('%d/%m')}"
            for i in range(8)
        ]

        tabla_datos = []
        for emp in empleados_a_mostrar:
            fila = [emp]
            partes_emp = emp.replace(",", "").split()
            posibles_emp = [emp]
            if len(partes_emp) >= 2:
                posibles_emp.append(f"{partes_emp[-1]}, {partes_emp[0]}")
                posibles_emp.append(f"{partes_emp[1]}, {partes_emp[0]}")

            for f_str in dias_fechas:
                placeholders = ",".join(["?"] * len(posibles_emp))
                cursor.execute(
                    f"""
                    SELECT turno FROM rol_asistencia 
                    WHERE (nombre IN ({placeholders}) OR empleado IN ({placeholders}))
                    AND fecha = ?
                """,
                    (*posibles_emp, *posibles_emp, f_str),
                )
                res = cursor.fetchone()
                val_bd = res[0] if res and res[0] else "-"
                fila.append(formatear_turno_vista(val_bd))
            tabla_datos.append(fila)
        conn.close()

        df_rol = pd.DataFrame(tabla_datos, columns=encabezados)
        opciones_turnos = ["-", "🟩 DIA", "🟦 NOCHE", "🟨 V", "DESCANSO"]

        # --- CONFIGURACIÓN DE AG-GRID PARA ARRASTRAR FILAS ---
        gb = GridOptionsBuilder.from_dataframe(df_rol)

        # Habilitar arrastre manual de filas desde la columna Empleado
        gb.configure_column("Empleado", rowDrag=True, editable=False, pinned="left")

        # Configurar menús desplegables editables para cada día de la semana
        for col in encabezados[1:]:
            gb.configure_column(
                col,
                editable=es_admin,
                cellEditor="agSelectCellEditor",
                cellEditorParams={"values": opciones_turnos},
            )

        gb.configure_grid_options(
            animateRows=True,
            rowDragManaged=True,
            suppressMoveWithRowGroup=True,
        )

        grid_options = gb.build()

        grid_response = AgGrid(
            df_rol,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.ALWAYS,
            fit_columns_on_grid_load=True,
            theme="streamlit",
            height=450,
        )

        df_editado = pd.DataFrame(grid_response["data"])

        if es_admin:
            if st.button("💾 Guardar Cambios en la Tabla", type="primary"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()

                for idx, row in df_editado.iterrows():
                    emp = row["Empleado"]
                    for i, f_str in enumerate(dias_fechas):
                        val_pantalla = row[encabezados[i + 1]]
                        nuevo_turno = limpiar_turno_bd(val_pantalla)

                        cursor.execute(
                            """
                            INSERT INTO rol_asistencia (nombre, empleado, fecha, turno, estado) 
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(nombre, fecha) DO UPDATE SET turno=excluded.turno, estado=excluded.estado
                        """,
                            (emp, emp, f_str, nuevo_turno, nuevo_turno),
                        )

                conn.commit()
                conn.close()
                st.success("¡Todos los turnos y el orden guardados con éxito!")
                st.rerun()

    # --- PESTAÑA 2: SOLICITAR VACACIONES ---
    with tab_actual[1]:
        st.subheader("Programación de Vacaciones")
        fechas_sel = st.date_input(
            "Selecciona los días deseados:", [], min_value=dt.date.today()
        )

        fechas_str = ""
        dias_actuales = []
        if fechas_sel:
            if isinstance(fechas_sel, (list, tuple)):
                if len(fechas_sel) == 2:
                    d_inicio, d_fin = fechas_sel
                    curr = d_inicio
                    while curr <= d_fin:
                        dias_actuales.append(curr.strftime("%Y-%m-%d"))
                        curr += dt.timedelta(days=1)
                    fechas_str = ", ".join(dias_actuales)
                elif len(fechas_sel) == 1:
                    fechas_str = fechas_sel[0].strftime("%Y-%m-%d")
                    dias_actuales = [fechas_str]
            else:
                fechas_str = fechas_sel.strftime("%Y-%m-%d")
                dias_actuales = [fechas_str]

        hoy_str = dt.date.today().strftime("%Y-%m-%d")
        alertas_empalme_usuario = []

        if dias_actuales:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT solicitante, fechas, fecha_solicitud FROM solicitudes_vacaciones 
                WHERE estado IN ('APROBADO', 'PENDIENTE') AND solicitante != ?
            """,
                (st.session_state.usuario,),
            )
            otras_solicitudes = cursor.fetchall()
            conn.close()

            for otro_sol, o_fechas, o_fecha_sol in otras_solicitudes:
                if o_fecha_sol <= hoy_str:
                    dias_otro = [
                        d.strip() for d in o_fechas.split(",") if d.strip()
                    ]
                    dias_coincidentes = [
                        d for d in dias_actuales if d in dias_otro
                    ]

                    if dias_coincidentes:
                        fechas_str_emp = ", ".join(dias_coincidentes)
                        alerta_msg = (
                            f"⚠️ ALERTA DE EMPALME CON {otro_sol} SOLICITO EL"
                            f" DIA {fechas_str_emp} SE TEDRA QUE REVISAR EN"
                            " CONJUNTO PARA VER LA NECESIDAD."
                        )
                        alertas_empalme_usuario.append(alerta_msg)

        if alertas_empalme_usuario:
            for alerta in alertas_empalme_usuario:
                st.markdown(
                    f'<div class="alerta-grande">{alerta}</div>',
                    unsafe_allow_html=True,
                )

        if st.button(
            "Enviar Solicitud", type="primary", use_container_width=True
        ):
            if fechas_str:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO solicitudes_vacaciones (solicitante, fechas, estado, fecha_solicitud) 
                    VALUES (?, ?, 'PENDIENTE', ?)
                """,
                    (st.session_state.usuario, fechas_str, hoy_str),
                )
                conn.commit()
                conn.close()

                st.session_state.msg_exito = (
                    f"✅ ¡Solicitud enviada correctamente para las fechas:"
                    f" {fechas_str}!"
                )
                st.rerun()
            else:
                st.warning("Selecciona las fechas en el calendario.")

        if "msg_exito" in st.session_state and st.session_state.msg_exito:
            st.success(st.session_state.msg_exito)

    idx_notif = (
        2 if st.session_state.rol in ["ADMIN_ROL", "ADMIN_USUARIOS"] else -1
    )

    # --- PESTAÑA 3: NOTIFICACIONES ---
    if st.session_state.rol in ["ADMIN_ROL", "ADMIN_USUARIOS"]:
        with tab_actual[idx_notif]:
            st.subheader("Dictamen de Solicitudes Pendientes")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, solicitante, fechas, fecha_solicitud FROM"
                " solicitudes_vacaciones WHERE estado = 'PENDIENTE'"
            )
            pendientes = cursor.fetchall()
            conn.close()

            if not pendientes:
                st.success("No hay solicitudes pendientes por revisar.")
            else:
                for sol_id, sol, fechas, f_sol in pendientes:
                    with st.expander(
                        f"📌 Solicitud de {sol} (Enviada: {f_sol})",
                        expanded=True,
                    ):
                        st.write(f"**Fechas solicitadas:** `{fechas}`")

                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        dias_lista = [
                            d.strip() for d in fechas.split(",") if d.strip()
                        ]
                        alertas_empalme = []

                        cursor.execute(
                            """
                            SELECT solicitante, fechas, fecha_solicitud FROM solicitudes_vacaciones 
                            WHERE estado IN ('APROBADO', 'PENDIENTE') AND solicitante != ? AND id != ?
                        """,
                            (sol, sol_id),
                        )
                        otras_solicitudes = cursor.fetchall()

                        for (
                            otro_sol,
                            o_fechas,
                            o_fecha_sol,
                        ) in otras_solicitudes:
                            if o_fecha_sol <= f_sol:
                                dias_otro = [
                                    d.strip()
                                    for d in o_fechas.split(",")
                                    if d.strip()
                                ]
                                dias_coincidentes = [
                                    d for d in dias_lista if d in dias_otro
                                ]

                                if dias_coincidentes:
                                    fechas_str_emp = ", ".join(
                                        dias_coincidentes
                                    )
                                    alerta_texto = (
                                        f"⚠️ ALERTA DE EMPALME CON {otro_sol}"
                                        f" SOLICITO EL DIA {fechas_str_emp} SE"
                                        " TEDRA QUE REVISAR EN CONJUNTO PARA"
                                        " VER LA NECESIDAD."
                                    )
                                    alertas_empalme.append(alerta_texto)

                        conn.close()

                        for alerta in alertas_empalme:
                            st.markdown(
                                f"""
                                <div style="background-color: rgba(255, 193, 7, 0.2); border-left: 5px solid #ffc107; padding: 12px; border-radius: 4px; margin-bottom: 15px;">
                                    <strong>{alerta}</strong>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        st.markdown(
                            "**Dictamen individual por día (Aprobar /"
                            " Rechazar):**"
                        )
                        decisiones_dias = {}
                        cols_dias = st.columns(
                            min(len(dias_lista), 4) if dias_lista else 1
                        )

                        for idx_d, dia in enumerate(dias_lista):
                            with cols_dias[idx_d % len(cols_dias)]:
                                decisiones_dias[dia] = st.selectbox(
                                    f"{dia}",
                                    ["Aprobar", "Rechazar"],
                                    key=f"dec_{sol_id}_{dia}",
                                )

                        st.write("")
                        if st.button(
                            f"💾 Aplicar Dictamen para Solicitud #{sol_id}",
                            type="primary",
                            key=f"btn_aplicar_{sol_id}",
                        ):
                            f_act = datetime.now().strftime("%Y-%m-%d")
                            h_act = datetime.now().strftime("%H:%M:%S")

                            conn = sqlite3.connect(DB_NAME)
                            cursor = conn.cursor()

                            dias_aprobados = [
                                d
                                for d, dec in decisiones_dias.items()
                                if dec == "Aprobar"
                            ]
                            dias_rechazados = [
                                d
                                for d, dec in decisiones_dias.items()
                                if dec == "Rechazar"
                            ]

                            for dia in dias_aprobados:
                                cursor.execute(
                                    """
                                        INSERT INTO rol_asistencia (nombre, empleado, fecha, turno, estado) 
                                        VALUES (?, ?, ?, 'V', 'V')
                                        ON CONFLICT(nombre, fecha) DO UPDATE SET turno='V', estado='V'
                                    """,
                                    (sol, sol, dia),
                                )

                            for dia in dias_rechazados:
                                cursor.execute(
                                    """
                                        UPDATE rol_asistencia 
                                        SET turno = '-', estado = '-' 
                                        WHERE (nombre = ? OR empleado = ?) AND fecha = ? AND turno = 'V'
                                    """,
                                    (sol, sol, dia),
                                )

                            estado_general = (
                                "APROBADO"
                                if len(dias_aprobados) > 0
                                else "RECHAZADO"
                            )

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
                                    estado_general,
                                    st.session_state.usuario,
                                    f_act,
                                    h_act,
                                    sol_id,
                                ),
                            )

                            conn.commit()
                            conn.close()
                            st.success(
                                "¡Dictamen aplicado correctamente para la"
                                f" solicitud #{sol_id}!"
                            )
                            st.rerun()

    # --- PESTAÑA 4: HISTORIAL (CON EDICIÓN Y LIMPIEZA) ---
    if es_autorizado_especial and "Historial" in pestanias:
        idx_historial = pestanias.index("Historial")
        with tab_actual[idx_historial]:
            st.markdown("---")
            st.subheader("📋 HISTORIAL DE DICTÁMENES Y AUDITORÍA")

            if es_angel:
                st.info(
                    "Panel exclusivo de **Angel Flores**. Modifica estatus,"
                    " utiliza los filtros de búsqueda o elimina registros"
                    " individualmente o por completo."
                )
            else:
                st.info(
                    f"Panel de supervisión para **{st.session_state.usuario}**."
                    " Puedes visualizar y filtrar el historial de dictámenes."
                )

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_texto = st.text_input(
                    "🔍 Buscar por Solicitante o Fechas:", ""
                ).upper()
            with col_f2:
                filtro_estado = st.selectbox(
                    "Filtrar por Estado:",
                    ["TODOS", "PENDIENTE", "APROBADO", "RECHAZADO"],
                )

            conn = sqlite3.connect(DB_NAME)
            query = """
                SELECT id, solicitante, fechas, estado, fecha_solicitud, 
                       autorizado_por, fecha_autorizacion, hora_autorizacion 
                FROM solicitudes_vacaciones 
                ORDER BY id DESC
            """
            df_hist_raw = pd.read_sql(query, conn)
            conn.close()

            df_hist = df_hist_raw.copy()
            if not df_hist.empty:
                if filtro_texto:
                    df_hist = df_hist[
                        df_hist["solicitante"]
                        .str.upper()
                        .str.contains(filtro_texto)
                        | df_hist["fechas"].str.upper().str.contains(filtro_texto)
                    ]
                if filtro_estado != "TODOS":
                    df_hist = df_hist[df_hist["estado"] == filtro_estado]

            if df_hist.empty:
                st.warning(
                    "No se encontraron registros con los filtros aplicados."
                )
            else:
                if es_angel:
                    df_editado = st.data_editor(
                        df_hist,
                        key="editor_hist_exclusivo_v11",
                        disabled=[
                            "id",
                            "solicitante",
                            "fechas",
                            "fecha_solicitud",
                            "autorizado_por",
                            "fecha_autorizacion",
                            "hora_autorizacion",
                        ],
                        column_config={
                            "estado": st.column_config.SelectboxColumn(
                                "Estado",
                                options=["PENDIENTE", "APROBADO", "RECHAZADO"],
                                required=True,
                            )
                        },
                        hide_index=True,
                        use_container_width=True,
                    )

                    c_sav, c_del_ind, c_del_all = st.columns([2, 2, 2])
                    with c_sav:
                        if st.button("💾 Guardar Cambios de Estatus", type="primary"):
                            conn = sqlite3.connect(DB_NAME)
                            cursor = conn.cursor()
                            for _, r in df_editado.iterrows():
                                cursor.execute(
                                    "UPDATE solicitudes_vacaciones SET estado = ? WHERE id = ?",
                                    (r["estado"], r["id"]),
                                )
                            conn.commit()
                            conn.close()
                            st.success("¡Estatus actualizados correctamente!")
                            st.rerun()

                    with c_del_ind:
                        id_a_borrar = st.number_input(
                            "ID a eliminar:", min_value=1, step=1, value=1
                        )
                        if st.button("🗑️ Eliminar Registro"):
                            conn = sqlite3.connect(DB_NAME)
                            cursor = conn.cursor()
                            cursor.execute(
                                "DELETE FROM solicitudes_vacaciones WHERE id = ?",
                                (id_a_borrar,),
                            )
                            conn.commit()
                            conn.close()
                            st.success(f"Registro ID #{id_a_borrar} eliminado.")
                            st.rerun()

                    with c_del_all:
                        if st.button("🔥 Vaciar Todo el Historial", type="secondary"):
                            conn = sqlite3.connect(DB_NAME)
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM solicitudes_vacaciones")
                            cursor.execute("DELETE FROM sqlite_sequence WHERE name='solicitudes_vacaciones'")
                            conn.commit()
                            conn.close()
                            st.success("Historial vaciado e ID reiniciado.")
                            st.rerun()
                else:
                    st.dataframe(df_hist, hide_index=True, use_container_width=True)

    # --- PESTAÑA 5: CONTROL DE TIEMPO EXTRA (TE) ---
    if es_autorizado_especial and "Control TE" in pestanias:
        idx_te = pestanias.index("Control TE")
        with tab_actual[idx_te]:
            st.subheader("⏱️ Registro y Control de Tiempo Extra")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT nombre FROM usuarios ORDER BY nombre ASC")
            lista_emp_te = [r[0] for r in cursor.fetchall()]
            conn.close()

            with st.form("form_tiempo_extra"):
                c_emp, c_fec, c_hrs = st.columns([2, 1, 1])
                with c_emp:
                    emp_te = st.selectbox("Empleado:", lista_emp_te)
                with c_fec:
                    fec_te = st.date_input("Fecha TE:", dt.date.today())
                with c_hrs:
                    hrs_te = st.number_input("Horas:", min_value=0.5, max_value=24.0, step=0.5)

                motivo_te = st.text_input("Motivo / Justificación:")
                btn_reg_te = st.form_submit_button("Registrar Tiempo Extra", type="primary")

                if btn_reg_te:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO tiempo_extra (empleado, fecha, horas, motivo, registrado_por, fecha_registro)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            emp_te,
                            fec_te.strftime("%Y-%m-%d"),
                            hrs_te,
                            motivo_te,
                            st.session_state.usuario,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"¡Registradas {hrs_te} hrs extras para {emp_te}!")
                    st.rerun()

            st.markdown("---")
            st.subheader("📊 Resumen y Registros de Horas Extra")

            conn = sqlite3.connect(DB_NAME)
            df_te = pd.read_sql("SELECT * FROM tiempo_extra ORDER BY id DESC", conn)
            conn.close()

            if not df_te.empty:
                fig_te = px.bar(
                    df_te,
                    x="empleado",
                    y="horas",
                    color="empleado",
                    title="Horas Extra Totales por Empleado",
                )
                st.plotly_chart(fig_te, use_container_width=True)
                st.dataframe(df_te, hide_index=True, use_container_width=True)
            else:
                st.info("No hay horas extra registradas todavía.")

    # --- PESTAÑA 6: GESTIÓN DE USUARIOS ---
    if es_angel and "Gestión Usuarios" in pestanias:
        idx_usr = pestanias.index("Gestión Usuarios")
        with tab_actual[idx_usr]:
            st.subheader("⚙️ Administración de Usuarios y Accesos")

            with st.expander("➕ Agregar Nuevo Usuario"):
                with st.form("form_add_user"):
                    c_nom, c_nam = st.columns(2)
                    with c_nom:
                        new_nomina = st.text_input("Nómina:").strip()
                    with c_nam:
                        new_nombre = st.text_input("Nombre Completo:").strip().upper()

                    c_rol, c_pwd = st.columns(2)
                    with c_rol:
                        new_rol = st.selectbox("Rol:", ["OPERADOR", "ADMIN_ROL", "ADMIN_USUARIOS"])
                    with c_pwd:
                        new_pwd = st.text_input("Contraseña Initial:", value="1234")

                    if st.form_submit_button("Crear Usuario", type="primary"):
                        if new_nomina and new_nombre:
                            try:
                                conn = sqlite3.connect(DB_NAME)
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT INTO usuarios (nomina, nombre, rol, password) VALUES (?, ?, ?, ?)",
                                    (new_nomina, new_nombre, new_rol, new_pwd),
                                )
                                conn.commit()
                                conn.close()
                                st.success(f"Usuario {new_nombre} registrado con éxito.")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Error: La nómina o el nombre ya se encuentran registrados.")
                        else:
                            st.warning("Completa la nómina y el nombre.")

            st.markdown("---")
            conn = sqlite3.connect(DB_NAME)
            df_users = pd.read_sql("SELECT id, nomina, nombre, rol FROM usuarios ORDER BY nombre ASC", conn)
            conn.close()

            st.dataframe(df_users, hide_index=True, use_container_width=True)
