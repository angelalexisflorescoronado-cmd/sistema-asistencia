from datetime import datetime
import datetime as dt
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

DB_NAME = "asistencia.db"


# ----------------------------------------------------------------------
# INICIALIZACIÓN DE BASE DE DATOS (MIGRACIÓN SEGURA)
# ----------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Crear tabla usuarios si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nomina TEXT DEFAULT '',
            nombre TEXT UNIQUE NOT NULL,
            rol TEXT NOT NULL DEFAULT 'OPERADOR',
            password TEXT NOT NULL DEFAULT '1234'
        )
    """)

    # 2. Agregar columna nomina si la tabla existía previamente sin ella
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN nomina TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # 3. Lista completa de usuarios extraída de la nómina
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

    # Actualizar primero las nóminas vinculadas a cada nombre
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

    # 4. Intentar crear el índice único de nómina capturando cualquier conflicto previo
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

    conn.commit()
    conn.close()


init_db()

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

    st.title("📅 Sistema de Asistencia")

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
        div[data-baseweb="calendar"] div[role="row"] {
            font-size: 11px !important;
        }
        div[data-baseweb="calendar"] abbr {
            text-decoration: none !important;
            font-size: 11px !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    pestanias = ["Rol de Asistencia", "Solicitar Vacaciones"]

    if st.session_state.rol in ["ADMIN_ROL", "ADMIN_USUARIOS"]:
        if num_pendientes > 0:
            texto_notif = f"🔴 NOTIFICACIONES ({num_pendientes})"
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
        if "Control T.E." not in pestanias:
            pestanias.append("Control T.E.")

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

    # --- PESTAÑA 1: ROL DE ASISTENCIA INTERACTIVO ---
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

        lunes = st.session_state.fecha_ref - dt.timedelta(
            days=st.session_state.fecha_ref.weekday()
        )
        domingo = lunes + dt.timedelta(days=6)

        st.info(
            f"📅 Semana del **{lunes.strftime('%d/%m/%Y')}** al"
            f" **{domingo.strftime('%d/%m/%Y')}**"
        )

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM usuarios ORDER BY nombre ASC")
        empleados = [r[0] for r in cursor.fetchall()]

        dias_fechas = [
            (lunes + dt.timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(7)
        ]
        nombres_dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        encabezados = ["Empleado"] + [
            f"{nombres_dias[i]} {(lunes + dt.timedelta(days=i)).strftime('%d/%m')}"
            for i in range(7)
        ]

        tabla_datos = []
        for emp in empleados:
            fila = [emp]
            for f_str in dias_fechas:
                cursor.execute(
                    "SELECT turno FROM rol_asistencia WHERE (nombre=? OR"
                    " empleado=?) AND fecha=?",
                    (emp, emp, f_str),
                )
                res = cursor.fetchone()
                fila.append(res[0] if res and res[0] else "-")
            tabla_datos.append(fila)
        conn.close()

        df_rol = pd.DataFrame(tabla_datos, columns=encabezados)

        es_admin = st.session_state.rol in ["ADMIN_ROL", "ADMIN_USUARIOS"]
        opciones_turnos = ["-", "DIA", "NOCHE", "DESCANSO", "V"]

        config_columnas = {
            "Empleado": st.column_config.TextColumn("Empleado", disabled=True)
        }
        for col in encabezados[1:]:
            config_columnas[col] = st.column_config.SelectboxColumn(
                col,
                options=opciones_turnos,
                required=True,
                disabled=not es_admin,
            )

        df_editado = st.data_editor(
            df_rol,
            column_config=config_columnas,
            use_container_width=True,
            hide_index=True,
            disabled=not es_admin,
            key="editor_turnos",
        )

        if es_admin:
            if st.button("💾 Guardar Cambios en la Tabla", type="primary"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()

                for idx, row in df_editado.iterrows():
                    emp = row["Empleado"]
                    for i, f_str in enumerate(dias_fechas):
                        nuevo_turno = row[encabezados[i + 1]]
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
                st.success("¡Todos los turnos se guardaron con éxito!")
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

    # --- PESTAÑA 4: HISTORIAL (EXCLUSIVO PARA ANGEL, ALEJANDRO Y DONATO) ---
    if es_autorizado_especial and "Historial" in pestanias:
        idx_historial = pestanias.index("Historial")
        with tab_actual[idx_historial]:
            st.markdown("---")
            st.subheader("📋 HISTORIAL DE DICTÁMENES Y AUDITORÍA")

            if es_angel:
                st.info(
                    "Panel exclusivo de **Angel Flores**. Modifica estatus,"
                    " utiliza los filtros de búsqueda o elimina registros"
                    " permanentemente."
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
            df_hist = pd.read_sql(query, conn)
            conn.close()

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
                        key="editor_hist_exclusivo_v10",
                        disabled=[
                            "id",
                            "solicitante",
                            "fechas",
                            "fecha_solicitud",
                            "autorizado_por",
                            "fecha_autorizacion",
                            "hora_autorizacion",
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                    if st.button(
                        "💾 Guardar Cambios y Registrar Auditoría",
                        type="primary",
                    ):
                        f_act = datetime.now().strftime("%Y-%m-%d")
                        h_act = datetime.now().strftime("%H:%M:%S")

                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()

                        for index, row in df_editado.iterrows():
                            id_reg = row["id"]
                            nuevo_estado = row["estado"]
                            solicitante_reg = row["solicitante"]
                            fechas_reg = row["fechas"]

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
                                    nuevo_estado,
                                    st.session_state.usuario,
                                    f_act,
                                    h_act,
                                    id_reg,
                                ),
                            )

                            for dia in [
                                d.strip()
                                for d in fechas_reg.split(",")
                                if d.strip()
                            ]:
                                if nuevo_estado == "APROBADO":
                                    cursor.execute(
                                        """
                                            INSERT INTO rol_asistencia (nombre, empleado, fecha, turno, estado) 
                                            VALUES (?, ?, ?, 'V', 'V')
                                            ON CONFLICT(nombre, fecha) DO UPDATE SET turno='V', estado='V'
                                        """,
                                        (
                                            solicitante_reg,
                                            solicitante_reg,
                                            dia,
                                        ),
                                    )
                                elif nuevo_estado == "RECHAZADO":
                                    cursor.execute(
                                        """
                                            UPDATE rol_asistencia 
                                            SET turno = '-', estado = '-' 
                                            WHERE (nombre = ? OR empleado = ?) AND fecha = ? AND turno = 'V'
                                        """,
                                        (
                                            solicitante_reg,
                                            solicitante_reg,
                                            dia,
                                        ),
                                    )

                        conn.commit()
                        conn.close()
                        st.success(
                            "¡Historial actualizado, auditado y turnos"
                            " sincronizados con éxito!"
                        )
                        st.rerun()

                    st.markdown("---")
                    st.subheader("🗑️ ZONA DE ELIMINACIÓN DE SOLICITUDES")
                    ids_disponibles = df_hist["id"].tolist()

                    if ids_disponibles:
                        col_del1, col_del2 = st.columns([1, 2])
                        with col_del1:
                            id_a_eliminar = st.selectbox(
                                "Selecciona el ID a eliminar:",
                                ids_disponibles,
                                key="sel_del_id",
                            )
                        with col_del2:
                            st.write("")
                            st.write("")
                            if st.button(
                                f"❌ Eliminar Solicitud #{id_a_eliminar}",
                                type="secondary",
                            ):
                                conn = sqlite3.connect(DB_NAME)
                                cursor = conn.cursor()
                                cursor.execute(
                                    "DELETE FROM solicitudes_vacaciones WHERE"
                                    " id = ?",
                                    (id_a_eliminar,),
                                )
                                conn.commit()
                                conn.close()
                                st.success(
                                    f"¡Solicitud con ID #{id_a_eliminar}"
                                    " eliminada correctamente!"
                                )
                                st.rerun()

                else:
                    st.dataframe(
                        df_hist, use_container_width=True, hide_index=True
                    )

    # --- PESTAÑA 5: CONTROL DE TIEMPO EXTRA (EXCLUSIVO PARA ANGEL, ALEJANDRO Y DONATO) ---
    if es_autorizado_especial and "Control T.E." in pestanias:
        idx_te = pestanias.index("Control T.E.")
        with tab_actual[idx_te]:
            st.markdown("---")
            st.subheader("⏱️ CONTROL Y ACUMULADO DE TIEMPO EXTRA (T.E.)")
            st.info(
                "Cálculo automático basado en el Rol de Asistencia: Se"
                " consideran como **Tiempo Extra** todos los días laborados"
                " (`DIA` o `NOCHE`) que excedan los **4 días estándar** por"
                " semana."
            )

            col_te1, col_te2 = st.columns(2)
            with col_te1:
                mes_filtro_te = st.selectbox(
                    "Filtrar por modo de cálculo:",
                    [
                        "Semana Actual Seleccionada",
                        "Histórico Acumulado General",
                    ],
                )

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT nombre FROM usuarios ORDER BY nombre ASC")
            todos_empleados = [r[0] for r in cursor.fetchall()]
            conn.close()

            registros_te = []

            if mes_filtro_te == "Semana Actual Seleccionada":
                dias_semana_actual = [
                    (lunes + dt.timedelta(days=i)).strftime("%Y-%m-%d")
                    for i in range(7)
                ]

                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                for emp in todos_empleados:
                    dias_trabajados = 0
                    for f_str in dias_semana_actual:
                        cursor.execute(
                            "SELECT turno FROM rol_asistencia WHERE (nombre=? OR"
                            " empleado=?) AND fecha=?",
                            (emp, emp, f_str),
                        )
                        res = cursor.fetchone()
                        if res and res[0] in ["DIA", "NOCHE"]:
                            dias_trabajados += 1

                    dias_te = max(0, dias_trabajados - 4)
                    if dias_te > 0:
                        registros_te.append({
                            "Empleado": emp,
                            "Semana": (
                                f"{lunes.strftime('%d/%m/%Y')} al"
                                f" {domingo.strftime('%d/%m/%Y')}"
                            ),
                            "Días Trabajados": dias_trabajados,
                            "Días de T.E.": dias_te,
                        })
                conn.close()

            else:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT fecha FROM rol_asistencia ORDER BY fecha"
                    " ASC"
                )
                todas_fechas = [r[0] for r in cursor.fetchall()]

                semanas_agrupadas = {}
                for f_str in todas_fechas:
                    try:
                        f_date = datetime.strptime(f_str, "%Y-%m-%d").date()
                        lun_sem = f_date - dt.timedelta(days=f_date.weekday())
                        if lun_sem not in semanas_agrupadas:
                            semanas_agrupadas[lun_sem] = []
                        semanas_agrupadas[lun_sem].append(f_str)
                    except ValueError:
                        continue

                for emp in todos_empleados:
                    total_dias_te_emp = 0
                    semanas_con_te = 0

                    for lun_sem, dias_list in semanas_agrupadas.items():
                        dias_trab = 0
                        for d_str in dias_list:
                            cursor.execute(
                                "SELECT turno FROM rol_asistencia WHERE"
                                " (nombre=? OR empleado=?) AND fecha=?",
                                (emp, emp, d_str),
                            )
                            res = cursor.fetchone()
                            if res and res[0] in ["DIA", "NOCHE"]:
                                dias_trab += 1

                        ste = max(0, dias_trab - 4)
                        if ste > 0:
                            total_dias_te_emp += ste
                            semanas_con_te += 1

                    if total_dias_te_emp > 0:
                        registros_te.append({
                            "Empleado": emp,
                            "Semanas con T.E.": semanas_con_te,
                            "Total Días de T.E. Acumulados": total_dias_te_emp,
                        })
                conn.close()

            df_te = pd.DataFrame(registros_te)

            if df_te.empty:
                st.success(
                    "No hay registros de Tiempo Extra generados para el período"
                    " seleccionado."
                )
            else:
                st.dataframe(
                    df_te, use_container_width=True, hide_index=True
                )

                if (
                    mes_filtro_te == "Semana Actual Seleccionada"
                    and "Días de T.E." in df_te.columns
                ):
                    fig = px.bar(
                        df_te,
                        x="Empleado",
                        y="Días de T.E.",
                        title="Días de Tiempo Extra por Empleado (Semana Actual)",
                        color="Días de T.E.",
                        color_continuous_scale="Reds",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                elif "Total Días de T.E. Acumulados" in df_te.columns:
                    fig = px.bar(
                        df_te,
                        x="Empleado",
                        y="Total Días de T.E. Acumulados",
                        title="Acumulado Histórico de Días T.E. por Empleado",
                        color="Total Días de T.E. Acumulados",
                        color_continuous_scale="Oranges",
                    )
                    st.plotly_chart(fig, use_container_width=True)

    # --- PESTAÑA 6: GESTIÓN DE USUARIOS (EXCLUSIVO PARA ANGEL) ---
    if es_angel and "Gestión Usuarios" in pestanias:
        idx_users = pestanias.index("Gestión Usuarios")
        with tab_actual[idx_users]:
            st.markdown("---")
            st.subheader("⚙️ ADMINISTRACIÓN GENERAL DE USUARIOS")
            st.info(
                "Módulo exclusivo de administración. Puedes registrar nuevos"
                " empleados asignando su nómina, modificar datos o eliminar"
                " accesos."
            )

            st.markdown("### ➕ Registrar Nuevo Usuario")
            col_u1, col_u2, col_u3, col_u4 = st.columns(4)
            with col_u1:
                nueva_nomina = st.text_input("Nómina:").strip()
            with col_u2:
                nuevo_nombre = st.text_input("Nombre Completo:").strip().upper()
            with col_u3:
                nuevo_rol = st.selectbox(
                    "Rol asignado:",
                    ["OPERADOR", "ADMIN_ROL", "ADMIN_USUARIOS"],
                )
            with col_u4:
                nueva_pass = st.text_input(
                    "Contraseña inicial:", value="1234", type="password"
                )

            if st.button("👥 Agregar Usuario", type="primary"):
                if nueva_nomina and nuevo_nombre and nueva_pass:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            """
                            INSERT INTO usuarios (nomina, nombre, rol, password) 
                            VALUES (?, ?, ?, ?)
                        """,
                            (nueva_nomina, nuevo_nombre, nuevo_rol, nueva_pass),
                        )
                        conn.commit()
                        st.success(
                            f"¡Usuario **{nuevo_nombre}** (Nómina: {nueva_nomina}) registrado con éxito!"
                        )
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(
                            f"El usuario o la nómina **{nueva_nomina}** ya existe en el sistema."
                        )
                    finally:
                        conn.close()
                else:
                    st.warning("Completa la nómina, el nombre y la contraseña.")

            st.markdown("---")
            st.markdown("### ✏️ Modificar o Eliminar Usuarios Existentes")

            conn = sqlite3.connect(DB_NAME)
            df_usuarios = pd.read_sql(
                "SELECT id, nomina, nombre, rol, password FROM usuarios ORDER BY nombre ASC",
                conn,
            )
            conn.close()

            if not df_usuarios.empty:
                df_u_editado = st.data_editor(
                    df_usuarios,
                    column_config={
                        "id": st.column_config.NumberColumn(
                            "ID", disabled=True
                        ),
                        "nomina": st.column_config.TextColumn("Nómina"),
                        "nombre": st.column_config.TextColumn("Nombre"),
                        "rol": st.column_config.SelectboxColumn(
                            "Rol",
                            options=["OPERADOR", "ADMIN_ROL", "ADMIN_USUARIOS"],
                        ),
                        "password": st.column_config.TextColumn("Contraseña"),
                    },
                    use_container_width=True,
                    hide_index=True,
                    key="editor_usuarios_app",
                )

                if st.button("💾 Guardar Cambios en Usuarios", type="primary"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    errores = []

                    for idx, row in df_u_editado.iterrows():
                        try:
                            cursor.execute(
                                """
                                UPDATE usuarios 
                                SET nomina = ?, nombre = ?, rol = ?, password = ? 
                                WHERE id = ?
                            """,
                                (
                                    str(row["nomina"]).strip(),
                                    str(row["nombre"]).strip().upper(),
                                    row["rol"],
                                    str(row["password"]),
                                    row["id"],
                                ),
                            )
                        except sqlite3.IntegrityError:
                            errores.append(
                                f"No se pudo actualizar a '{row['nombre']}': La"
                                f" nómina '{row['nomina']}' o el nombre coincide"
                                " con otro registro existente."
                            )

                    conn.commit()
                    conn.close()

                    if errores:
                        for err in errores:
                            st.error(err)
                        st.warning(
                            "Los demás usuarios sin conflicto sí se actualizaron"
                            " correctamente."
                        )
                    else:
                        st.success(
                            "¡Datos y contraseñas de usuarios actualizados"
                            " correctamente!"
                        )
                        st.rerun()

                st.markdown("---")
                col_du1, col_du2 = st.columns([1, 2])
                with col_du1:
                    u_a_eliminar = st.selectbox(
                        "Selecciona usuario a eliminar:",
                        df_usuarios["nombre"].tolist(),
                        key="sel_del_user",
                    )
                with col_du2:
                    st.write("")
                    st.write("")
                    if st.button(
                        f"❌ Eliminar Usuario {u_a_eliminar}", type="secondary"
                    ):
                        if u_a_eliminar.strip().upper() == "ANGEL FLORES":
                            st.error(
                                "No es posible eliminar la cuenta principal de"
                                " administración."
                            )
                        else:
                            conn = sqlite3.connect(DB_NAME)
                            cursor = conn.cursor()
                            cursor.execute(
                                "DELETE FROM usuarios WHERE nombre = ?",
                                (u_a_eliminar,),
                            )
                            conn.commit()
                            conn.close()
                            st.success(
                                f"¡El usuario {u_a_eliminar} ha sido eliminado!"
                            )
                            st.rerun()
