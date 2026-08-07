import datetime as dt
from datetime import datetime
import os
import re
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Configuración de página y sesión (debe ir antes de cualquier comando de Streamlit)
st.set_page_config(
    page_title="Control de Asistencia", page_icon="📅", layout="wide"
)

# Conexión segura con Google Sheets
try:
    private_key_raw = st.secrets["connections"]["gsheets"]["private_key"]
    private_key_formatted = private_key_raw.replace("\\n", "\n")

    creds_dict = {
        "type": "service_account",
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": private_key_formatted,
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"]
    }

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    # Apertura de la hoja dentro del try para evitar NameError si falla
    sheet = client.open_by_key("1Q8Pw68xm6PjeZMrvuNRkeLZzAkcq3At4o7h7lBz3y9o").sheet1
    st.success("¡Conexión exitosa con Google Sheets!")
except Exception as e:
    st.error(f"Ocurrió un error al conectar: {e}")
    st.stop()  # Detiene la ejecución de la app para evitar errores en cascada
  
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
      ("10031976", "LUIS RAUL JIMENEZ", "OPERADOR", "1234"),
      ("10015510", "RAYMUNDO PEREZ", "OPERADOR", "1234"),
      ("10016085", "ERNESTO SALVADOR", "OPERADOR", "1234"),
      ("10019675", "RIGOBERTO RIVERA", "OPERADOR", "1234"),
      ("10139954", "OSCAR GARCIA HERNANDEZ", "OPERADOR", "1234"),
      ("10007219", "LUIS ANGEL PEREZ", "OPERADOR", "1234"),
      ("10018255", "ORLANDO SERNA", "OPERADOR", "1234"),
      ("10005881", "SANTOS GUTIERREZ", "OPERADOR", "1234"),
      ("10019578", "JESUS LOREDO", "OPERADOR", "1234"),
      ("10022967", "RICARDO SANTIAGO", "OPERADOR", "1234"),
      ("10005894", "GILBERTO ZARAGOZA", "OPERADOR", "1234"),
      ("10092630", "JUAN CARLOS", "OPERADOR", "1234"),
      ("10076145", "OSCAR HERNANDEZ", "OPERADOR", "1234"),
      ("10004365", "OSCAR BENITO", "OPERADOR", "1234"),
      ("10023526", "MARIA DOREYDA PEREZ", "OPERADOR", "1234"),
      ("10019258", "ROBERTO ANTONIO", "OPERADOR", "1234"),
      ("10015453", "JOSE JUAN PORTILLO", "OPERADOR", "1234"),
      ("10035253", "ANGEL FLORES", "ADMIN_USUARIOS", "Alex1996"),
      ("10003693", "ALEJANDRO GUARDA", "ADMIN_ROL", "1234"),
      ("10215435", "DONATO BACCO", "ADMIN_ROL", "1234"),
  ]

  cursor.execute("SELECT COUNT(*) FROM usuarios")
  if cursor.fetchone()[0] == 0:
    for nom, nombre, rol, pwd in usuarios_base:
      cursor.execute(
          """
                INSERT INTO usuarios (nomina, nombre, rol, password) 
                VALUES (?, ?, ?, ?)
            """,
          (nom, nombre, rol, pwd),
      )
  else:
    cursor.execute(
        """
            UPDATE usuarios 
            SET nomina = '10035253', password = 'Alex1996', rol = 'ADMIN_USUARIOS' 
            WHERE nombre = 'ANGEL FLORES'
        """
    )
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE nombre = 'ANGEL FLORES'")
    if cursor.fetchone()[0] == 0:
      cursor.execute(
          """
                INSERT INTO usuarios (nomina, nombre, rol, password) 
                VALUES ('10035253', 'ANGEL FLORES', 'ADMIN_USUARIOS', 'Alex1996')
            """
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
      cursor.execute(f"ALTER TABLE solicitudes_vacaciones ADD COLUMN {col}")
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
# GESTIÓN DE SESIÓN
# ----------------------------------------------------------------------
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
  st.title("📱 Core Process")
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

  st.title("📱 Core Process Espumado")

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
    if "💾 Guardar Código Base" not in pestanias:
      pestanias.append("💾 Guardar Código Base")

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
    st.info(
        "💡 **Tip:** Puedes editar la numeración en la columna `id` para"
        " reordenar los registros directamente desde aquí."
    )

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

    offset_domingo = (st.session_state.fecha_ref.weekday() + 1) % 7
    domingo_inicio = st.session_state.fecha_ref - dt.timedelta(
        days=offset_domingo
    )
    domingo_fin = domingo_inicio + dt.timedelta(days=7)

    st.markdown(
        f"📅 Semana del **{domingo_inicio.strftime('%d/%m/%Y')}** al"
        f" **{domingo_fin.strftime('%d/%m/%Y')}**"
    )

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM usuarios ORDER BY id ASC")
    usuarios_db = cursor.fetchall()
    todos_empleados = [r[1] for r in usuarios_db]

    es_admin = st.session_state.rol in ["ADMIN_ROL", "ADMIN_USUARIOS"]
    usuario_actual = st.session_state.usuario

    dias_fechas = [
        (domingo_inicio + dt.timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(8)
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
      empleados_seleccionados = st.multiselect(
          "🔍 Buscar o filtrar por empleado(s):",
          options=todos_empleados,
          default=[],
          placeholder=(
              "Selecciona uno o varios empleados (o deja vacío para mostrar"
              " todos)"
          ),
      )

    if empleados_seleccionados:
      mapa_usuarios = {nombre: uid for uid, nombre in usuarios_db}
      empleados_a_mostrar = [
          (mapa_usuarios[emp], emp) for emp in empleados_seleccionados
      ]
    else:
      empleados_a_mostrar = usuarios_db

    encabezados = ["id", "Empleado"] + [
        f"{nombres_dias_abrev[i]} {(domingo_inicio + dt.timedelta(days=i)).strftime('%d/%m')}"
        for i in range(8)
    ]

    tabla_datos = []
    for uid, emp in empleados_a_mostrar:
      fila = [uid, emp]
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
        "id": st.column_config.NumberColumn(
            "id", format="%d", required=True, disabled=not es_admin
        ),
        "Empleado": st.column_config.TextColumn("Empleado", disabled=True),
    }
    for col in encabezados[2:]:
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
          nuevo_id = int(row["id"])
          emp = row["Empleado"]

          cursor.execute(
              "UPDATE usuarios SET id = ? WHERE nombre = ?", (nuevo_id, emp)
          )

          partes_emp = emp.replace(",", "").split()
          posibles_emp = [emp]
          if len(partes_emp) >= 2:
            posibles_emp.append(f"{partes_emp[-1]}, {partes_emp[0]}")
            posibles_emp.append(f"{partes_emp[1]}, {partes_emp[0]}")

          for i, f_str in enumerate(dias_fechas):
            val_pantalla = row[encabezados[i + 2]]
            nuevo_turno = limpiar_turno_bd(val_pantalla)

            placeholders_del = ",".join(["?"] * len(posibles_emp))
            cursor.execute(
                f"""
                            DELETE FROM rol_asistencia 
                            WHERE fecha = ? AND (nombre IN ({placeholders_del}) OR empleado IN ({placeholders_del}))
                        """,
                (f_str, *posibles_emp, *posibles_emp),
            )

            cursor.execute(
                """
                            INSERT INTO rol_asistencia (nombre, empleado, fecha, turno, estado) 
                            VALUES (?, ?, ?, ?, ?)
                        """,
                (emp, emp, f_str, nuevo_turno, nuevo_turno),
            )

        conn.commit()
        conn.close()
        st.success(
            "¡Numeración, orden y turnos guardados y sincronizados con éxito!"
        )
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
          dias_otro = [d.strip() for d in o_fechas.split(",") if d.strip()]
          dias_coincidentes = [d for d in dias_actuales if d in dias_otro]

          if dias_coincidentes:
            fechas_str_emp = ", ".join(dias_coincidentes)
            alerta_msg = (
                f"⚠️ ALERTA DE EMPALME CON {otro_sol} SOLICITO EL DIA"
                f" {fechas_str_emp} SE TEDRA QUE REVISAR EN CONJUNTO PARA VER"
                " LA NECESIDAD."
            )
            alertas_empalme_usuario.append(alerta_msg)

    if alertas_empalme_usuario:
      for alerta in alertas_empalme_usuario:
        st.markdown(
            f'<div class="alerta-grande">{alerta}</div>',
            unsafe_allow_html=True,
        )

    if st.button("Enviar Solicitud", type="primary", use_container_width=True):
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
              f"📌 Solicitud de {sol} (Enviada: {f_sol})", expanded=True
          ):
            st.write(f"**Fechas solicitadas:** `{fechas}`")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            dias_lista = [d.strip() for d in fechas.split(",") if d.strip()]
            alertas_empalme = []

            cursor.execute(
                """
                            SELECT solicitante, fechas, fecha_solicitud FROM solicitudes_vacaciones 
                            WHERE estado IN ('APROBADO', 'PENDIENTE') AND solicitante != ? AND id != ?
                        """,
                (sol, sol_id),
            )
            otras_solicitudes = cursor.fetchall()

            for otro_sol, o_fechas, o_fecha_sol in otras_solicitudes:
              if o_fecha_sol <= f_sol:
                dias_otro = [d.strip() for d in o_fechas.split(",") if d.strip()]
                dias_coincidentes = [d for d in dias_lista if d in dias_otro]

                if dias_coincidentes:
                  fechas_str_emp = ", ".join(dias_coincidentes)
                  alerta_texto = (
                      f"⚠️ ALERTA DE EMPALME CON {otro_sol} SOLICITO EL DIA"
                      f" {fechas_str_emp} SE TEDRA QUE REVISAR EN CONJUNTO PARA"
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
                "**Dictamen individual por día (Aprobar / Rechazar):**"
            )
            decisiones_dias = {}
            cols_dias = st.columns(min(len(dias_lista), 4) if dias_lista else 1)

            for idx_d, dia in enumerate(dias_lista):
              with cols_dias[idx_d % len(cols_dias)]:
                decisiones_dias[dia] = st.selectbox(
                    f"{dia}", ["Aprobar", "Rechazar"], key=f"dec_{sol_id}_{dia}"
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
                  d for d, dec in decisiones_dias.items() if dec == "Aprobar"
              ]
              dias_rechazados = [
                  d for d, dec in decisiones_dias.items() if dec == "Rechazar"
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
                  "APROBADO" if len(dias_aprobados) > 0 else "RECHAZADO"
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
                  (estado_general, st.session_state.usuario, f_act, h_act, sol_id),
              )

              conn.commit()
              conn.close()
              st.success(
                  f"¡Dictamen aplicado correctamente para la solicitud #{sol_id}!"
              )
              st.rerun()

  # --- PESTAÑA 4: HISTORIAL ---
  if es_autorizado_especial and "Historial" in pestanias:
    idx_historial = pestanias.index("Historial")
    with tab_actual[idx_historial]:
      st.markdown("---")
      st.subheader("📋 HISTORIAL DE DICTÁMENES Y AUDITORÍA")

      if es_angel:
        st.info(
            "Panel exclusivo de **Angel Flores**. Modifica estatus, utiliza los"
            " filtros de búsqueda o elimina registros individualmente o por"
            " completo."
        )
      else:
        st.info(
            f"Panel de supervisión para **{st.session_state.usuario}**. Puedes"
            " visualizar y filtrar el historial de dictámenes."
        )

      col_f1, col_f2 = st.columns(2)
      with col_f1:
        filtro_texto = st.text_input(
            "🔍 Buscar por Solicitante o Fechas:", ""
        ).upper()
      with col_f2:
        filtro_estado = st.selectbox(
            "Filtrar por Estado:", ["TODOS", "PENDIENTE", "APROBADO", "RECHAZADO"]
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
              df_hist["solicitante"].str.upper().str.contains(filtro_texto)
              | df_hist["fechas"].str.upper().str.contains(filtro_texto)
          ]
        if filtro_estado != "TODOS":
          df_hist = df_hist[df_hist["estado"] == filtro_estado]

      if df_hist.empty:
        st.warning("No se encontraron registros con los filtros aplicados.")
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
              use_container_width=True,
              hide_index=True,
          )

          if st.button(
              "💾 Guardar Cambios y Registrar Auditoría", type="primary"
          ):
            f_act = datetime.now().strftime("%Y-%m-%d")
            h_act = datetime.now().strftime("%H:%M:%S")

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
                  (row["estado"], st.session_state.usuario, f_act, h_act, row["id"]),
              )
            conn.commit()
            conn.close()
            st.success("¡Historial y auditoría actualizados correctamente!")
            st.rerun()
        else:
          st.dataframe(df_hist, use_container_width=True, hide_index=True)

      if es_angel and not df_hist_raw.empty:
        st.markdown("---")
        st.subheader("🗑️ Opciones de Eliminación de Historial")

        col_del_single, col_del_all = st.columns(2)

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

              cursor.execute("SELECT COUNT(*) FROM solicitudes_vacaciones")
              total_restantes = cursor.fetchone()[0]
              if total_restantes == 0:
                cursor.execute(
                    "DELETE FROM sqlite_sequence WHERE"
                    " name='solicitudes_vacaciones'"
                )

              conn.commit()
              conn.close()
              st.success(f"¡Registro ID {id_target} eliminado exitosamente!")
              st.rerun()
            else:
              st.warning("Selecciona un registro válido de la lista.")

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

              cursor.execute("DELETE FROM solicitudes_vacaciones")
              cursor.execute(
                  "DELETE FROM sqlite_sequence WHERE"
                  " name='solicitudes_vacaciones'"
              )

              conn.commit()
              conn.close()
              st.success(
                  "¡Todo el historial fue eliminado y el contador de ID ha"
                  " sido reiniciado al 1!"
              )
              st.rerun()
            else:
              st.error(
                  "Por favor, marca la casilla de confirmación para proceder"
                  " con el vaciado total."
              )

  # --- PESTAÑA 5: CONTROL TE ---
  if es_autorizado_especial and "Control TE" in pestanias:
    idx_te = pestanias.index("Control TE")
    with tab_actual[idx_te]:
      st.subheader("⏱️ CONTROL Y ACUMULADO DE TIEMPO EXTRA (TE)")

      st.info(
          "**Cálculo automático basado en el Rol de Asistencia:** Se considera"
          " como Tiempo Extra todos los días laborados (`DIA` / `NOCHE`) que"
          " exceden los 4 días estándar por semana (incluyendo aquellos días"
          " programados originalmente con vacaciones pero trabajados)."
      )

      modo_calculo = st.selectbox(
          "Filtrar por modo de cálculo:",
          ["Histórico Acumulado General", "Días (seleccionar en calendario)"],
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
          "SELECT nombre AS Empleado, fecha, turno FROM rol_asistencia", conn
      )
      conn.close()

      if not df_rol_all.empty:
        df_rol_all["es_laborado"] = df_rol_all["turno"].apply(
            lambda t: 1
            if str(t).upper().strip() in ["DIA", "NOCHE", "🟩 DIA", "🟦 NOCHE"]
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
            rango_label = (
                f"{f_inicio.strftime('%d/%m/%Y')} al"
                f" {f_fin.strftime('%d/%m/%Y')}"
            )
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
          st.dataframe(df_resumen, use_container_width=True, hide_index=True)

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
            textposition="inside", textfont_size=12, textfont_color="black"
        )

        fig.update_layout(
            showlegend=False,
            xaxis_tickangle=-30,
            height=450,
            margin=dict(l=20, r=20, t=30, b=80),
            yaxis=dict(gridcolor="rgba(255, 255, 255, 0.1)"),
        )

        st.plotly_chart(fig, use_container_width=True)

  # --- PESTAÑA 6: GESTIÓN DE USUARIOS ---
  if es_angel and "Gestión Usuarios" in pestanias:
    idx_users = pestanias.index("Gestión Usuarios")
    with tab_actual[idx_users]:
      st.subheader("⚙️ Administración de Usuarios")
      st.info(
          "💡 **Tip:** Puedes editar directamente la columna de numeración"
          " (`id`) en la tabla para ordenar y numerar a los usuarios a tu"
          " preferencia."
      )

      conn = sqlite3.connect(DB_NAME)
      df_users = pd.read_sql(
          "SELECT id, nomina, nombre, rol, password FROM usuarios ORDER BY id"
          " ASC",
          conn,
      )
      conn.close()

      df_users_edit = st.data_editor(
          df_users,
          key="editor_usuarios_angel",
          disabled=[],
          num_rows="dynamic",
          use_container_width=True,
          hide_index=True,
      )

      col_guardar, _ = st.columns([2, 2])
      with col_guardar:
        if st.button(
            "💾 Guardar Cambios y Numeración de Usuarios",
            type="primary",
            use_container_width=True,
        ):
          if "id" in df_users_edit.columns:
            try:
              df_users_edit["id"] = pd.to_numeric(df_users_edit["id"])
              df_users_edit = df_users_edit.sort_values(
                  by="id", na_position="last"
              )
            except Exception:
              pass

          conn = sqlite3.connect(DB_NAME)
          cursor = conn.cursor()

          cursor.execute("DELETE FROM usuarios")
          try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='usuarios'")
          except sqlite3.OperationalError:
            pass

          for index, row in df_users_edit.iterrows():
            uid = row.get("id", None)
            nom = str(row.get("nomina", "")).strip()
            nombre = str(row.get("nombre", "")).strip()
            rol = str(row.get("rol", "OPERADOR")).strip()
            password = str(row.get("password", "1234")).strip()

            if nombre:
              if pd.notna(uid) and str(uid).strip() != "":
                try:
                  cursor.execute(
                      """
                                        INSERT INTO usuarios (id, nomina, nombre, rol, password)
                                        VALUES (?, ?, ?, ?, ?)
                                    """,
                      (int(uid), nom, nombre, rol, password),
                  )
                except sqlite3.IntegrityError:
                  cursor.execute(
                      """
                                        INSERT INTO usuarios (nomina, nombre, rol, password)
                                        VALUES (?, ?, ?, ?)
                                    """,
                      (nom, nombre, rol, password),
                  )
              else:
                cursor.execute(
                    """
                                    INSERT INTO usuarios (nomina, nombre, rol, password)
                                    VALUES (?, ?, ?, ?)
                                """,
                    (nom, nombre, rol, password),
                )

          conn.commit()
          conn.close()
          st.success(
              "¡Base de datos de usuarios y numeración actualizados con"
              " éxito!"
          )
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
            "🗑️ Eliminar Usuario", type="secondary", use_container_width=True
        ):
          if usuario_a_eliminar != "-- Seleccionar --":
            nomina_target = usuario_a_eliminar.split(" - ")[0].strip()
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM usuarios WHERE nomina = ?", (nomina_target,)
            )
            conn.commit()
            conn.close()
            st.success(
                f"¡Usuario con nómina {nomina_target} eliminado con éxito!"
            )
            st.rerun()
          else:
            st.warning("Selecciona un usuario válido para eliminar.")

  # --- PESTAÑA 7: GUARDAR CÓDIGO BASE ---
  if es_angel and "💾 Guardar Código Base" in pestanias:
    idx_codigo = pestanias.index("💾 Guardar Código Base")
    with tab_actual[idx_codigo]:
      st.subheader("💾 Actualización Automática del Código Fuente")
      st.info(
          "Esta herramienta lee todos los usuarios y registros actuales de la"
          " base de datos y actualiza el archivo de código fuente para que"
          " incluya esta información de manera predeterminada."
      )

      if st.button(
          "🔄 Actualizar y Guardar Código con Datos Actuales", type="primary"
      ):
        try:
          conn = sqlite3.connect(DB_NAME)
          cursor = conn.cursor()
          cursor.execute(
              "SELECT nomina, nombre, rol, password FROM usuarios ORDER BY id"
              " ASC"
          )
          users_db_data = cursor.fetchall()
          conn.close()

          nuevas_lineas_base = []
          for nom, nombre, rol, pwd in users_db_data:
            nuevas_lineas_base.append(
                f'      ("{nom}", "{nombre}", "{rol}", "{pwd}"),'
            )

          contenido_usuarios = "\n".join(nuevas_lineas_base)
          bloque_nuevo_str = f"""  usuarios_base = [
{contenido_usuarios}
  ]"""

          archivo_actual = __file__
          with open(archivo_actual, "r", encoding="utf-8") as f:
            contenido = f.read()

          patron = r"usuarios_base\s*=\s*\[.*?\]"
          nuevo_contenido, reemplazos = re.subn(
              patron, bloque_nuevo_str, contenido, flags=re.DOTALL
          )

          if reemplazos > 0:
            with open(archivo_actual, "w", encoding="utf-8") as f:
              f.write(nuevo_contenido)
            st.success(
                "¡Código actualizado y guardado exitosamente con los"
                " datos actuales de la base de datos!"
            )
          else:
            st.error(
                "No se pudo encontrar el bloque `usuarios_base` en el archivo"
                " para realizar el reemplazo automático."
            )
        except Exception as e:
          st.error(f"Ocurrió un error al actualizar el archivo: {e}")
