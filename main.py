from datetime import datetime
import datetime as dt
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

DB_NAME = "asistencia.db"

# ----------------------------------------------------------------------
# URL DIRECTA Y LIMPIA DEL LOGO DE WHIRLPOOL CORPORATION
# ----------------------------------------------------------------------
URL_LOGO = "https://upload.wikimedia.org/wikipedia/commons/c/c2/Whirlpool_Corporation_Logo.png"


# ----------------------------------------------------------------------
# INICIALIZACIÓN DE BASE DE DATOS
# ----------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabla Usuarios
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

    # Tabla Rol Asistencia
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

    # Tabla Solicitudes Vacaciones
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

    # Tabla Tiempo Extra (T.E.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tiempo_extra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado TEXT NOT NULL,
            fecha TEXT NOT NULL,
            horas REAL NOT NULL,
            motivo TEXT DEFAULT '',
            registrado_por TEXT NOT NULL
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
    if val_clean == "DIA":
        return "🟩 DIA"
    elif val_clean == "NOCHE":
        return "🟦 NOCHE"
    elif val_clean in ["V", "VACACIONES"]:
        return "🟨 V"
    return "-"


def limpiar_turno_bd(val):
    val_str = str(val).upper()
    if "DIA" in val_str:
        return "DIA"
    elif "NOCHE" in val_str:
        return "NOCHE"
    elif "V" in val_str:
        return "V"
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

    # --- ENCABEZADO CON LOGO Y TÍTULO ---
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        try:
            st.image(URL_LOGO, width=150)
        except Exception:
            st.markdown("🖼️ *(Logo)*")

    with col_titulo:
        st.title("Core Process Espumado")

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

    # --- PESTAÑA 1: ROL DE ASISTENCIA ---
    with tab_actual[0]:
        st.subheader("Tabla de Asistencia")

        # NAVEGACIÓN DE FECHAS
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
        todos_empleados = [r[0] for r in cursor.fetchall()]

        es_admin = st.session_state.rol in ["ADMIN_ROL", "ADMIN_USUARIOS"]
        usuario_actual = st.session_state.usuario

        # VISTA RESUMIDA INDIVIDUAL AL INICIAR SESIÓN (PARA OPERADOR)
        if not es_admin:
            st.markdown(f"### 👋 Hola, **{usuario_actual}**")
            st.markdown("##### Tus turnos programados para esta semana:")

            dias_fechas = [
                (lunes + dt.timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(7)
            ]
            nombres_dias_abrev = [
                "Lunes",
                "Martes",
                "Miércoles",
                "Jueves",
                "Viernes",
                "Sábado",
                "Domingo",
            ]

            partes = usuario_actual.replace(",", "").split()
            posibles_nombres = [usuario_actual]
            if len(partes) >= 2:
                posibles_nombres.append(f"{partes[-1]}, {partes[0]}")
                posibles_nombres.append(f"{partes[1]}, {partes[0]}")

            cols_turnos = st.columns(7)
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
                    fecha_fmt = (lunes + dt.timedelta(days=i)).strftime("%d/%m")
                    st.metric(
                        label=f"{nombres_dias_abrev[i]} {fecha_fmt}",
                        value=formatear_turno_vista(val_bd),
                    )

            st.markdown("---")

        # BUSCADOR / FILTRO POR EMPLEADO
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

        dias_fechas = [
            (lunes + dt.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)
        ]
        nombres_dias_abrev = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        encabezados = ["Empleado"] + [
            f"{nombres_dias_abrev[i]} {(lunes + dt.timedelta(days=i)).strftime('%d/%m')}"
            for i in range(7)
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

        config_cols = {
            "Empleado": st.column_config.TextColumn("Empleado", disabled=True)
        }
        for col in encabezados[1:]:
            config_cols[col] = st.column_config.SelectboxColumn(
                col,
                options=opciones_turnos,
                required=True,
                disabled=not es_admin,
            )

        df_editado = st.data_editor(
            df_rol,
            column_config=config_cols,
            use_container_width=True,
            hide_index=True,
            key="editor_turnos_captura_izquierda",
        )

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

    # --- PESTAÑA: HISTORIAL ---
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
                        column_config={
                            "estado": st.column_config.SelectboxColumn(
                                "estado",
                                options=["PENDIENTE", "APROBADO", "RECHAZADO"],
                                required=True,
                            )
                        },
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

                    col_btn_save, col_btn_del = st.columns([2, 1])
                    with col_btn_save:
                        if st.button(
                            "💾 Guardar Cambios y Registrar Auditoría",
                            type="primary",
                            use_container_width=True,
                        ):
                            f_act = datetime.now().strftime("%Y-%m-%d")
                            h_act = datetime.now().strftime("%H:%M:%S")

                            conn = sqlite3.connect(DB_NAME)
                            cursor = conn.cursor()

                            for index, row in df_editado.iterrows():
                                cursor.execute(
                                    """
                                    UPDATE solicitudes_vacaciones 
                                    SET estado = ?, autorizado_por = ?, fecha_autorizacion = ?, hora_autorizacion = ? 
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
                            st.success("¡Historial actualizado exitosamente!")
                            st.rerun()

                    with col_btn_del:
                        id_eliminar = st.number_input(
                            "ID a eliminar:", min_value=1, step=1, value=1
                        )
                        if st.button("🗑️ Eliminar Registro", use_container_width=True):
                            conn = sqlite3.connect(DB_NAME)
                            cursor = conn.cursor()
                            cursor.execute(
                                "DELETE FROM solicitudes_vacaciones WHERE id = ?",
                                (id_eliminar,),
                            )
                            conn.commit()
                            conn.close()
                            st.warning(f"Registro ID #{id_eliminar} eliminado.")
                            st.rerun()
                else:
                    st.dataframe(df_hist, use_container_width=True, hide_index=True)

    # --- PESTAÑA: CONTROL T.E. (TIEMPO EXTRA) ---
    if es_autorizado_especial and "Control T.E." in pestanias:
        idx_te = pestanias.index("Control T.E.")
        with tab_actual[idx_te]:
            st.markdown("---")
            st.subheader("⏱️ CONTROL DE TIEMPO EXTRA (T.E.)")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT nombre FROM usuarios ORDER BY nombre ASC")
            lista_emp_te = [r[0] for r in cursor.fetchall()]
            conn.close()

            with st.form("form_tiempo_extra", clear_on_submit=True):
                st.markdown("##### Registrar Horas Extra")
                col_te1, col_te2, col_te3 = st.columns([2, 1, 1])
                with col_te1:
                    emp_te = st.selectbox("Empleado:", lista_emp_te)
                with col_te2:
                    fecha_te = st.date_input("Fecha:", dt.date.today())
                with col_te3:
                    horas_te = st.number_input(
                        "Horas:", min_value=0.5, max_value=24.0, step=0.5, value=2.0
                    )

                motivo_te = st.text_input("Motivo / Justificación del T.E.:")
                btn_te = st.form_submit_button("💾 Registrar Tiempo Extra", type="primary")

                if btn_te:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO tiempo_extra (empleado, fecha, horas, motivo, registrado_por) 
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            emp_te,
                            fecha_te.strftime("%Y-%m-%d"),
                            horas_te,
                            motivo_te,
                            st.session_state.usuario,
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"¡Registradas {horas_te}h de T.E. para {emp_te}!")
                    st.rerun()

            st.markdown("---")
            st.subheader("📊 Métricas y Reportes de Tiempo Extra")

            conn = sqlite3.connect(DB_NAME)
            df_te = pd.read_sql("SELECT * FROM tiempo_extra ORDER BY fecha DESC", conn)
            conn.close()

            if df_te.empty:
                st.info("No hay registros de tiempo extra capturados.")
            else:
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("Total Horas Extra Registradas", f"{df_te['horas'].sum():.1f} hrs")
                with col_m2:
                    st.metric("Total de Registros", f"{len(df_te)}")

                df_resumen_te = (
                    df_te.groupby("empleado")["horas"]
                    .sum()
                    .reset_index()
                    .sort_values(by="horas", ascending=False)
                )

                fig_te = px.bar(
                    df_resumen_te,
                    x="empleado",
                    y="horas",
                    title="Acumulado de Horas Extra por Empleado",
                    labels={"empleado": "Empleado", "horas": "Horas Totales"},
                    color="horas",
                    color_continuous_scale="Viridis",
                )
                st.plotly_chart(fig_te, use_container_width=True)

                st.markdown("##### Historial Detallado de T.E.")
                st.dataframe(df_te, use_container_width=True, hide_index=True)

    # --- PESTAÑA: GESTIÓN USUARIOS (EXCLUSIVO PARA ANGEL) ---
    if es_angel and "Gestión Usuarios" in pestanias:
        idx_gestion = pestanias.index("Gestión Usuarios")
        with tab_actual[idx_gestion]:
            st.markdown("---")
            st.subheader("⚙️ GESTIÓN Y ADMINISTRACIÓN DE USUARIOS")
            st.info("Panel exclusivo para creación, modificación y eliminación de usuarios del sistema.")

            tab_usr1, tab_usr2 = st.tabs(["👥 Lista y Edición", "➕ Nuevo Usuario"])

            with tab_usr1:
                conn = sqlite3.connect(DB_NAME)
                df_usr = pd.read_sql("SELECT id, nomina, nombre, rol, password FROM usuarios ORDER BY id ASC", conn)
                conn.close()

                df_usr_edit = st.data_editor(
                    df_usr,
                    key="editor_usuarios_crud",
                    column_config={
                        "id": st.column_config.TextColumn("id", disabled=True),
                        "rol": st.column_config.SelectboxColumn(
                            "rol",
                            options=["OPERADOR", "ADMIN_ROL", "ADMIN_USUARIOS"],
                            required=True,
                        ),
                    },
                    use_container_width=True,
                    hide_index=True,
                )

                col_u_save, col_u_del = st.columns([2, 1])
                with col_u_save:
                    if st.button("💾 Guardar Cambios de Usuarios", type="primary", use_container_width=True):
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        for idx, row in df_usr_edit.iterrows():
                            cursor.execute(
                                """
                                UPDATE usuarios 
                                SET nomina = ?, nombre = ?, rol = ?, password = ? 
                                WHERE id = ?
                            """,
                                (row["nomina"], row["nombre"], row["rol"], row["password"], row["id"]),
                            )
                        conn.commit()
                        conn.close()
                        st.success("¡Datos de usuarios actualizados correctamente!")
                        st.rerun()

                with col_u_del:
                    id_u_del = st.number_input("ID de Usuario a Eliminar:", min_value=1, step=1, value=1, key="num_u_del")
                    if st.button("🗑️ Eliminar Usuario", use_container_width=True, key="btn_u_del"):
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_u_del,))
                        conn.commit()
                        conn.close()
                        st.warning(f"Usuario con ID #{id_u_del} ha sido eliminado.")
                        st.rerun()

            with tab_usr2:
                with st.form("form_crear_usuario", clear_on_submit=True):
                    st.markdown("##### Registrar Nuevo Usuario")
                    c_n1, c_n2 = st.columns(2)
                    with c_n1:
                        nueva_nom = st.text_input("Número de Nómina:").strip()
                        nuevo_nombre = st.text_input("Nombre Completo:").strip().upper()
                    with c_n2:
                        nuevo_rol = st.selectbox("Rol:", ["OPERADOR", "ADMIN_ROL", "ADMIN_USUARIOS"])
                        nueva_pwd = st.text_input("Contraseña:", value="1234")

                    btn_crear_u = st.form_submit_button("➕ Crear Usuario", type="primary")

                    if btn_crear_u:
                        if nueva_nom and nuevo_nombre:
                            try:
                                conn = sqlite3.connect(DB_NAME)
                                cursor = conn.cursor()
                                cursor.execute(
                                    """
                                    INSERT INTO usuarios (nomina, nombre, rol, password) 
                                    VALUES (?, ?, ?, ?)
                                """,
                                    (nueva_nom, nuevo_nombre, nuevo_rol, nueva_pwd),
                                )
                                conn.commit()
                                conn.close()
                                st.success(f"¡Usuario **{nuevo_nombre}** creado exitosamente!")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Error: El nombre o número de nómina ya existe en la base de datos.")
                        else:
                            st.warning("Completa los campos obligatorios (Nómina y Nombre).")
