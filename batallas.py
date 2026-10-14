import tkinter as tk
from tkinter import messagebox
import sqlite3
import os
import threading
from tkinter import ttk
from serial.tools import list_ports

from Interfaz.esp32 import esp32


# ============================================================
# COMPONENTES VISUALES REDONDEADOS
# ============================================================

def _puntos_redondeados(x1, y1, x2, y2, radio):
    radio = max(2, min(radio, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + radio, y1, x2 - radio, y1,
        x2, y1, x2, y1 + radio,
        x2, y2 - radio, x2, y2,
        x2 - radio, y2, x1 + radio, y2,
        x1, y2, x1, y2 - radio,
        x1, y1 + radio, x1, y1
    ]


class RoundedCard(tk.Frame):
    """Tarjeta con fondo redondeado y un frame interior para sus widgets."""
    def __init__(self, master, fill="#ffffff", outline="#d7dde2",
                 radius=18, padding=8, height=120, **kwargs):
        super().__init__(master, bg=master.cget("bg"), bd=0,
                         highlightthickness=0, **kwargs)
        self.fill = fill
        self.outline = outline
        self.radius = radius
        self.padding = padding
        self.canvas = tk.Canvas(
            self, bg=master.cget("bg"), bd=0, highlightthickness=0,
            relief="flat", height=height
        )
        self.canvas.pack(fill="both", expand=True)
        self.content = tk.Frame(self.canvas, bg=fill, bd=0,
                                highlightthickness=0)
        self.window_id = self.canvas.create_window(
            padding, padding, anchor="nw", window=self.content
        )
        self.canvas.bind("<Configure>", self._redibujar)
        self.after_idle(self._redibujar)

    def _redibujar(self, event=None):
        ancho = max(2, self.canvas.winfo_width())
        alto = max(2, self.canvas.winfo_height())
        p = min(self.padding, max(2, ancho // 5), max(2, alto // 5))
        self.canvas.delete("fondo_redondeado")
        self.canvas.create_polygon(
            _puntos_redondeados(1, 1, ancho - 1, alto - 1, self.radius),
            smooth=True, splinesteps=24, fill=self.fill,
            outline=self.outline, width=1, tags="fondo_redondeado"
        )
        self.canvas.tag_lower("fondo_redondeado")
        self.canvas.coords(self.window_id, p, p)
        self.canvas.itemconfigure(
            self.window_id, width=max(1, ancho - 2 * p),
            height=max(1, alto - 2 * p)
        )


class RoundedButton(tk.Canvas):
    """Botón dibujado en Canvas para mantener esquinas redondeadas."""
    def __init__(self, master, text="", command=None, width=150, height=44,
                 bg="#2563eb", fg="white", activebackground=None,
                 activeforeground=None, disabledbackground="#cbd5e1",
                 font=("Segoe UI", 11, "bold"), radius=14, state="normal",
                 **kwargs):
        super().__init__(
            master, width=width, height=height, bg=master.cget("bg"),
            bd=0, highlightthickness=0, relief="flat", cursor="hand2"
        )
        self.text = text
        self.command = command
        self.button_bg = bg
        self.button_fg = fg
        self.activebackground = activebackground or bg
        self.activeforeground = activeforeground or fg
        self.disabledbackground = disabledbackground
        self.font = font
        self.radius = radius
        self.state = state
        self.hover = False
        self.bind("<Configure>", self._dibujar)
        self.bind("<Enter>", self._entrar)
        self.bind("<Leave>", self._salir)
        self.bind("<Button-1>", self._clic)
        self.after_idle(self._dibujar)

    def _color_actual(self):
        if self.state == "disabled":
            return self.disabledbackground
        return self.activebackground if self.hover else self.button_bg

    def _dibujar(self, event=None):
        self.delete("all")
        ancho = max(2, self.winfo_width())
        alto = max(2, self.winfo_height())
        self.create_polygon(
            _puntos_redondeados(1, 1, ancho - 1, alto - 1, self.radius),
            smooth=True, splinesteps=24, fill=self._color_actual(),
            outline=self._color_actual()
        )
        self.create_text(
            ancho / 2, alto / 2, text=self.text,
            fill="#f8fafc" if self.state == "disabled" else self.button_fg,
            font=self.font, justify="center"
        )
        super().configure(cursor="arrow" if self.state == "disabled" else "hand2")

    def _entrar(self, event=None):
        self.hover = True
        self._dibujar()

    def _salir(self, event=None):
        self.hover = False
        self._dibujar()

    def _clic(self, event=None):
        if self.state != "disabled" and callable(self.command):
            self.command()

    def config(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
        atributos = {
            "command": "command", "text": "text", "bg": "button_bg",
            "fg": "button_fg", "activebackground": "activebackground",
            "activeforeground": "activeforeground",
            "disabledbackground": "disabledbackground",
            "font": "font", "state": "state"
        }
        for key, attr in atributos.items():
            if key in kwargs:
                setattr(self, attr, kwargs.pop(key))
        if kwargs:
            super().configure(**kwargs)
        self._dibujar()

    configure = config


# ============================================================
# BASE DE DATOS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ruta_bd = os.path.join(
    BASE_DIR,
    "BasesDeDatos",
    "competencia.db"
)


def conectar_bd():
    return sqlite3.connect(ruta_bd)


# ============================================================
# PREPARAR BASE DE DATOS
# ============================================================

def preparar_base_batallas():

    conexion = conectar_bd()
    cursor = conexion.cursor()

    cursor.execute(
        "PRAGMA table_info(enfrentamientos)"
    )

    columnas = [
        fila[1]
        for fila in cursor.fetchall()
    ]

    if "criterio_ganador" not in columnas:

        cursor.execute("""
            ALTER TABLE enfrentamientos
            ADD COLUMN criterio_ganador TEXT
        """)

    if "tiempo" not in columnas:

        cursor.execute("""
            ALTER TABLE enfrentamientos
            ADD COLUMN tiempo TEXT
        """)

    if "ataques1" not in columnas:

        cursor.execute("""
            ALTER TABLE enfrentamientos
            ADD COLUMN ataques1 INTEGER DEFAULT 0
        """)

    if "ataques2" not in columnas:

        cursor.execute("""
            ALTER TABLE enfrentamientos
            ADD COLUMN ataques2 INTEGER DEFAULT 0
        """)

    conexion.commit()
    conexion.close()


preparar_base_batallas()


# ============================================================
# OBTENER BATALLA
# ============================================================

def obtener_batalla_actual():

    conexion = conectar_bd()
    cursor = conexion.cursor()

    # Primero una batalla activa
    cursor.execute("""
        SELECT
            e.id,
            e.etapa,
            COALESCE(g.nombre, ''),
            e.participante1,
            e.participante2,
            p1.nombre,
            p1.robot,
            p2.nombre,
            p2.robot,
            e.estado,
            e.ronda,
            COALESCE(e.criterio_ganador, ''),
            COALESCE(e.tiempo, ''),
            COALESCE(e.ataques1, 0),
            COALESCE(e.ataques2, 0)

        FROM enfrentamientos e

        INNER JOIN participantes p1
            ON e.participante1 = p1.id

        INNER JOIN participantes p2
            ON e.participante2 = p2.id

        LEFT JOIN grupos g
            ON e.grupo_id = g.id

        WHERE e.estado IN ('En curso', 'Pausada')

        ORDER BY e.id

        LIMIT 1
    """)

    batalla = cursor.fetchone()

    # Si no hay activa, siguiente pendiente
    if batalla is None:

        cursor.execute("""
            SELECT
                e.id,
                e.etapa,
                COALESCE(g.nombre, ''),
                e.participante1,
                e.participante2,
                p1.nombre,
                p1.robot,
                p2.nombre,
                p2.robot,
                e.estado,
                e.ronda,
                COALESCE(e.criterio_ganador, ''),
                COALESCE(e.tiempo, ''),
                COALESCE(e.ataques1, 0),
                COALESCE(e.ataques2, 0)

            FROM enfrentamientos e

            INNER JOIN participantes p1
                ON e.participante1 = p1.id

            INNER JOIN participantes p2
                ON e.participante2 = p2.id

            LEFT JOIN grupos g
                ON e.grupo_id = g.id

            WHERE e.estado = 'Pendiente'

            ORDER BY e.id

            LIMIT 1
        """)

        batalla = cursor.fetchone()

    conexion.close()

    return batalla


# ============================================================
# ACTUALIZAR ESTADO
# ============================================================

def actualizar_estado(id_batalla, estado):

    conexion = conectar_bd()
    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE enfrentamientos

        SET estado = ?

        WHERE id = ?
    """, (
        estado,
        id_batalla
    ))

    conexion.commit()
    conexion.close()


# ============================================================
# REGISTRAR RESULTADO
# ============================================================

def registrar_resultado(
    id_batalla,
    ganador,
    criterio,
    tiempo,
    ataques1,
    ataques2
):

    conexion = conectar_bd()
    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE enfrentamientos

        SET
            ganador = ?,
            criterio_ganador = ?,
            estado = 'Completado',
            tiempo = ?,
            ataques1 = ?,
            ataques2 = ?

        WHERE id = ?
    """, (
        ganador,
        criterio,
        tiempo,
        ataques1,
        ataques2,
        id_batalla
    ))

    conexion.commit()
    conexion.close()


# ============================================================
# CENTRAR VENTANA
# ============================================================

def centrar_ventana(ventana, ancho, alto):

    ventana.update_idletasks()

    pantalla_ancho = ventana.winfo_screenwidth()
    pantalla_alto = ventana.winfo_screenheight()

    x = (pantalla_ancho - ancho) // 2
    y = (pantalla_alto - alto) // 2

    ventana.geometry(
        f"{ancho}x{alto}+{x}+{y}"
    )


# ============================================================
# VENTANA RESULTADO
# ============================================================

def abrir_resultado(
    parent,
    batalla,
    actualizar
):

    (
        id_batalla,
        etapa,
        grupo,
        participante1,
        participante2,
        nombre1,
        robot1,
        nombre2,
        robot2,
        estado,
        ronda,
        criterio_actual,
        tiempo_bd,
        ataques1_bd,
        ataques2_bd
    ) = batalla

    # --------------------------------------------------------
    # OBTENER ÚLTIMOS DATOS ESP32
    # --------------------------------------------------------

    tiempo, ataques1, ataques2 = esp32.obtener_datos()

    # Si ESP32 no tiene datos, usamos los de BD
    if tiempo == "--:--" and tiempo_bd:
        tiempo = tiempo_bd

    if ataques1 == 0 and ataques1_bd:
        ataques1 = ataques1_bd

    if ataques2 == 0 and ataques2_bd:
        ataques2 = ataques2_bd

    # --------------------------------------------------------
    # VENTANA
    # --------------------------------------------------------

    ventana = tk.Toplevel(parent)

    ventana.title(
        "Resultado de batalla"
    )

    centrar_ventana(
        ventana,
        760,
        720
    )

    ventana.transient(parent)
    ventana.grab_set()

    # No se puede cerrar con X
    ventana.protocol(
        "WM_DELETE_WINDOW",
        lambda: None
    )

    # --------------------------------------------------------
    # FONDO
    # --------------------------------------------------------

    ventana.configure(
        bg="#f3f5f7"
    )

    # --------------------------------------------------------
    # CONTENEDOR
    # --------------------------------------------------------

    principal = tk.Frame(
        ventana,
        bg="#f3f5f7"
    )

    principal.pack(
        fill="both",
        expand=True,
        padx=30,
        pady=25
    )

    # --------------------------------------------------------
    # ENCABEZADO ROJO DEL RESULTADO
    # --------------------------------------------------------

    cabecera_resultado = RoundedCard(
        principal, fill="#922b2b", outline="#922b2b",
        radius=22, padding=8, height=90
    )
    cabecera_resultado.pack(fill="x", pady=(0, 18))

    tk.Label(
        cabecera_resultado.content,
        text=f"RESULTADO • BATALLA {id_batalla}",
        font=("Segoe UI", 22, "bold"),
        fg="white", bg="#922b2b"
    ).pack(side="left", padx=20, expand=True)

    tk.Label(
        cabecera_resultado.content,
        text=(f"Grupos - {grupo}" if etapa == "Grupo" and grupo
              else "Todos vs Todos" if etapa == "Todos" else etapa),
        font=("Segoe UI", 10, "bold"),
        fg="white", bg="#7f1d1d", padx=12, pady=7
    ).pack(side="right", padx=18)

    # --------------------------------------------------------
    # DATOS
    # --------------------------------------------------------

    datos = RoundedCard(
        principal, fill="white", outline="#d9dee3",
        radius=20, padding=8, height=94
    )
    datos.pack(fill="x", pady=(0, 20))

    for columna in range(3):
        datos.content.grid_columnconfigure(columna, weight=1)

    estadisticas = [
        ("ATAQUES R1", str(ataques1)),
        ("TIEMPO", tiempo),
        ("ATAQUES R2", str(ataques2)),
    ]

    for columna, (titulo, valor) in enumerate(estadisticas):
        tk.Label(
            datos.content, text=titulo,
            font=("Segoe UI", 9, "bold"),
            fg="#7a858e", bg="white"
        ).grid(row=0, column=columna, padx=18, pady=(12, 0), sticky="ew")

        tk.Label(
            datos.content, text=valor,
            font=("Segoe UI", 18, "bold"),
            fg="#17202a", bg="white"
        ).grid(row=1, column=columna, padx=18, pady=(0, 12), sticky="ew")

    # --------------------------------------------------------
    # GANADOR
    # --------------------------------------------------------

    tk.Label(
        principal,
        text="SELECCIONA EL GANADOR",
        font=("Segoe UI", 13, "bold"),
        fg="#17202a",
        bg="#f3f5f7"
    ).pack(
        anchor="w",
        pady=(0, 8)
    )

    ganador = tk.IntVar(value=0)

    marco_ganadores = tk.Frame(
        principal,
        bg="#f3f5f7"
    )

    marco_ganadores.pack(
        fill="x"
    )

    boton1 = None
    boton2 = None

    def seleccionar_ganador(valor):
        ganador.set(valor)
        boton1.config(
            bg="#2563eb" if valor == participante1 else "#ffffff",
            fg="white" if valor == participante1 else "#17202a"
        )
        boton2.config(
            bg="#2563eb" if valor == participante2 else "#ffffff",
            fg="white" if valor == participante2 else "#17202a"
        )

    boton1 = RoundedButton(
        marco_ganadores,
        text=f"{robot1}\n{nombre1}",
        command=lambda: seleccionar_ganador(participante1),
        width=300, height=78, bg="#ffffff", fg="#17202a",
        activebackground="#dbeafe", activeforeground="#17202a",
        font=("Segoe UI", 13, "bold"), radius=16
    )
    boton1.pack(side="left", expand=True, fill="both", padx=(0, 7))

    boton2 = RoundedButton(
        marco_ganadores,
        text=f"{robot2}\n{nombre2}",
        command=lambda: seleccionar_ganador(participante2),
        width=300, height=78, bg="#ffffff", fg="#17202a",
        activebackground="#dbeafe", activeforeground="#17202a",
        font=("Segoe UI", 13, "bold"), radius=16
    )
    boton2.pack(side="left", expand=True, fill="both", padx=(7, 0))

    # --------------------------------------------------------
    # CRITERIO
    # --------------------------------------------------------

    tk.Label(
        principal,
        text="CRITERIO DE VICTORIA",
        font=("Segoe UI", 13, "bold"),
        fg="#17202a",
        bg="#f3f5f7"
    ).pack(
        anchor="w",
        pady=(20, 8)
    )

    criterio = tk.StringVar(value="")

    marco_criterios = tk.Frame(
        principal,
        bg="#f3f5f7"
    )

    marco_criterios.pack(
        fill="x"
    )

    criterios = [
        "Expulsión del dohyo",
        "Inmovilización",
        "Mayor cantidad de ataques",
        "Tiempo",
        "Decisión del juez"
    ]

    botones_criterio = {}

    def seleccionar_criterio(texto):
        criterio.set(texto)
        for nombre, boton in botones_criterio.items():
            boton.config(
                bg="#2563eb" if nombre == texto else "#ffffff",
                fg="white" if nombre == texto else "#263238"
            )

    for texto in criterios:
        boton = RoundedButton(
            marco_criterios,
            text=texto,
            command=lambda opcion=texto: seleccionar_criterio(opcion),
            width=620, height=38,
            bg="#ffffff", fg="#263238",
            activebackground="#dbeafe", activeforeground="#263238",
            font=("Segoe UI", 11, "bold"), radius=13
        )
        boton.pack(fill="x", pady=3)
        botones_criterio[texto] = boton

    # --------------------------------------------------------
    # REGISTRAR
    # --------------------------------------------------------

    def registrar():

        if ganador.get() == 0:

            messagebox.showwarning(
                "Resultado incompleto",
                "Selecciona el ganador.",
                parent=ventana
            )

            return

        if criterio.get() == "":

            messagebox.showwarning(
                "Resultado incompleto",
                "Selecciona el criterio de victoria.",
                parent=ventana
            )

            return

        registrar_resultado(
            id_batalla,
            ganador.get(),
            criterio.get(),
            tiempo,
            ataques1,
            ataques2
        )

        # Reiniciamos los datos para la siguiente batalla
        esp32.reiniciar_datos()

        ventana.grab_release()
        ventana.destroy()

        # ACTUALIZAR INMEDIATAMENTE
        actualizar()

    ventana.bind(
        "<Return>",
        lambda evento: registrar()
    )

    # --------------------------------------------------------
    # TEXTO INFERIOR
    # --------------------------------------------------------

    tk.Label(
        principal,
        text="Presiona ENTER para registrar",
        font=("Segoe UI", 11, "italic"),
        fg="#68737d",
        bg="#f3f5f7"
    ).pack(
        pady=(12, 0)
    )


# ============================================================
# INTERFAZ BATALLAS
# ============================================================

def mostrar_batallas(contenedor):

    # --------------------------------------------------------
    # LIMPIAR LA PÁGINA ANTES DE DIBUJAR
    # --------------------------------------------------------

    for widget in contenedor.winfo_children():
        widget.destroy()

    batalla = obtener_batalla_actual()

    # --------------------------------------------------------
    # PRINCIPAL
    # --------------------------------------------------------

    principal = tk.Frame(
        contenedor,
        bg="#f3f5f7"
    )

    principal.pack(
        fill="both",
        expand=True
    )

    # --------------------------------------------------------
    # SI NO HAY BATALLAS
    # --------------------------------------------------------

    if batalla is None:

        tk.Label(
            principal,
            text="BATALLAS",
            font=("Segoe UI", 30, "bold"),
            fg="#17202a",
            bg="#f3f5f7"
        ).pack(
            pady=(80, 15)
        )

        tk.Label(
            principal,
            text="No hay batallas pendientes",
            font=("Segoe UI", 16),
            fg="#68737d",
            bg="#f3f5f7"
        ).pack()

        return

    (
        id_batalla,
        etapa,
        grupo,
        participante1,
        participante2,
        nombre1,
        robot1,
        nombre2,
        robot2,
        estado,
        ronda,
        criterio_actual,
        tiempo_bd,
        ataques1_bd,
        ataques2_bd
    ) = batalla

    # --------------------------------------------------------
    # ENCABEZADO
    # --------------------------------------------------------

    encabezado = RoundedCard(
        principal, fill="#922b2b", outline="#922b2b",
        radius=24, padding=10, height=112
    )
    encabezado.pack(fill="x", padx=18, pady=(8, 0))

    encabezado_interior = encabezado.content
    for columna in range(3):
        encabezado_interior.grid_columnconfigure(columna, weight=1, uniform="encabezado")

    modo_texto = (
        f"Grupos - {grupo}" if etapa == "Grupo" and grupo
        else "Todos vs Todos" if etapa == "Todos"
        else etapa
    )
    tk.Label(
        encabezado_interior, text=modo_texto,
        font=("Segoe UI", 12, "bold"), fg="#fbeaea", bg="#922b2b",
        anchor="w"
    ).grid(row=0, column=0, sticky="w", padx=(18, 6), pady=8)

    tk.Label(
        encabezado_interior, text=f"BATALLA {id_batalla}",
        font=("Segoe UI", 26, "bold"), fg="white", bg="#922b2b",
        anchor="center"
    ).grid(row=0, column=1, sticky="nsew", padx=4, pady=8)

    zona_puerto = tk.Frame(encabezado_interior, bg="#922b2b")
    zona_puerto.grid(row=0, column=2, sticky="e", padx=(6, 18), pady=5)

    def obtener_puertos_disponibles():
        try:
            return [p.device for p in list_ports.comports()]
        except Exception:
            return []

    puertos_disponibles = obtener_puertos_disponibles()
    puerto_var = tk.StringVar(
        value=puertos_disponibles[0] if puertos_disponibles else "Sin puertos disponibles"
    )
    selector_puerto = ttk.Combobox(
        zona_puerto, textvariable=puerto_var,
        values=puertos_disponibles or ["Sin puertos disponibles"],
        width=18, state="readonly", font=("Segoe UI", 11)
    )
    selector_puerto.pack(pady=(0, 4))

    estado_conexion = tk.Label(
        zona_puerto, text="● No conectado",
        font=("Segoe UI", 9, "bold"), fg="#d1d5db", bg="#922b2b"
    )
    estado_conexion.pack()

    def conectar_puerto(event=None, mostrar_error=False):
        puerto = puerto_var.get()
        if puerto == "Sin puertos disponibles":
            estado_conexion.config(text="● No conectado", fg="#d1d5db")
            return
        try:
            correcto = esp32.conectar(puerto)
            if correcto:
                estado_conexion.config(text=f"● Conectado ({puerto})", fg="#86efac")
            else:
                estado_conexion.config(text="● No conectado", fg="#d1d5db")
        except Exception as error:
            estado_conexion.config(text="● No conectado", fg="#d1d5db")
            if mostrar_error:
                messagebox.showerror(
                    "Conexión ESP32", str(error),
                    parent=contenedor.winfo_toplevel()
                )

    def refrescar_puertos():
        if not principal.winfo_exists():
            return
        encontrados = obtener_puertos_disponibles()
        valores = encontrados or ["Sin puertos disponibles"]
        actual = puerto_var.get()
        selector_puerto.configure(values=valores)
        if actual not in valores:
            puerto_var.set(valores[0])
            if getattr(esp32, "conectado", False):
                esp32.desconectar()
            estado_conexion.config(text="● No conectado", fg="#d1d5db")
        if encontrados and not getattr(esp32, "conectado", False):
            conectar_puerto()
        principal.after(2500, refrescar_puertos)

    selector_puerto.bind(
        "<<ComboboxSelected>>",
        lambda evento: conectar_puerto(evento, True)
    )
    if puertos_disponibles:
        conectar_puerto()
    principal.after(2500, refrescar_puertos)

    # --------------------------------------------------------
    # ESTADO
    # --------------------------------------------------------

    estado_frame = RoundedCard(
        principal, fill="#e8eeee", outline="#e8eeee",
        radius=20, padding=5, height=44
    )
    estado_frame.pack(pady=18)

    estado_label = tk.Label(
        estado_frame.content, text=estado.upper(),
        font=("Segoe UI", 11, "bold"), fg="#17202a",
        bg="#e8eeee", padx=25, pady=5
    )
    estado_label.pack()

    # --------------------------------------------------------
    # COMBATE
    # --------------------------------------------------------

    combate = tk.Frame(
        principal,
        bg="#f3f5f7"
    )

    combate.pack(
        fill="x",
        padx=60
    )

    # --------------------------------------------------------
    # TARJETA ROBOT 1
    # --------------------------------------------------------

    tarjeta1_card = RoundedCard(
        combate, fill="#ffffff", outline="#d7dde2",
        radius=22, padding=8, height=178
    )
    tarjeta1_card.pack(side="left", expand=True, fill="both", ipady=8)
    tarjeta1 = tarjeta1_card.content

    tk.Label(
        tarjeta1,
        text="ROBOT 1",
        font=("Segoe UI", 10, "bold"),
        fg="#7a858e",
        bg="white"
    ).pack(
        pady=(10, 3)
    )

    tk.Label(
        tarjeta1, text=robot1,
        font=("Segoe UI", 21, "bold"), fg="#17202a", bg="white"
    ).pack()

    tk.Label(
        tarjeta1, text=nombre1,
        font=("Segoe UI", 12), fg="#68737d", bg="white"
    ).pack(pady=(4, 10))

    # --------------------------------------------------------
    # VS
    # --------------------------------------------------------

    tk.Label(
        combate,
        text="VS",
        font=("Segoe UI", 19, "bold"),
        fg="#68737d",
        bg="#f3f5f7"
    ).pack(
        side="left",
        padx=22
    )

    # --------------------------------------------------------
    # TARJETA ROBOT 2
    # --------------------------------------------------------

    tarjeta2_card = RoundedCard(
        combate, fill="#ffffff", outline="#d7dde2",
        radius=22, padding=8, height=178
    )
    tarjeta2_card.pack(side="left", expand=True, fill="both", ipady=8)
    tarjeta2 = tarjeta2_card.content

    tk.Label(
        tarjeta2,
        text="ROBOT 2",
        font=("Segoe UI", 10, "bold"),
        fg="#7a858e",
        bg="white"
    ).pack(
        pady=(10, 3)
    )

    tk.Label(
        tarjeta2, text=robot2,
        font=("Segoe UI", 21, "bold"), fg="#17202a", bg="white"
    ).pack()

    tk.Label(
        tarjeta2, text=nombre2,
        font=("Segoe UI", 12), fg="#68737d", bg="white"
    ).pack(pady=(4, 10))

    # --------------------------------------------------------
    # PANEL TIEMPO / ATAQUES
    # --------------------------------------------------------

    datos_card = RoundedCard(
        principal, fill="white", outline="#d7dde2",
        radius=22, padding=8, height=112
    )
    datos_card.pack(fill="x", padx=60, pady=20)
    datos = datos_card.content
    for columna in range(3):
        datos.grid_columnconfigure(columna, weight=1, uniform="estadisticas")

    tk.Label(
        datos, text="⚔  ATAQUES R1",
        font=("Segoe UI", 9, "bold"), fg="#7a858e", bg="white"
    ).grid(row=0, column=0, pady=(12, 0), sticky="ew")
    ataques1_label = tk.Label(
        datos, text="0", font=("Segoe UI", 25, "bold"),
        fg="#17202a", bg="white"
    )
    ataques1_label.grid(row=1, column=0, padx=18, pady=(0, 12), sticky="ew")

    tk.Label(
        datos, text="◷  TIEMPO",
        font=("Segoe UI", 9, "bold"), fg="#7a858e", bg="white"
    ).grid(row=0, column=1, pady=(12, 0), sticky="ew")
    tiempo_label = tk.Label(
        datos, text="00:00", font=("Segoe UI", 25, "bold"),
        fg="#17202a", bg="white"
    )
    tiempo_label.grid(row=1, column=1, padx=18, pady=(0, 12), sticky="ew")

    tk.Label(
        datos, text="⚔  ATAQUES R2",
        font=("Segoe UI", 9, "bold"), fg="#7a858e", bg="white"
    ).grid(row=0, column=2, pady=(12, 0), sticky="ew")
    ataques2_label = tk.Label(
        datos, text="0", font=("Segoe UI", 25, "bold"),
        fg="#17202a", bg="white"
    )
    ataques2_label.grid(row=1, column=2, padx=18, pady=(0, 12), sticky="ew")

    # --------------------------------------------------------
    # CONTROLES
    # --------------------------------------------------------

    controles = tk.Frame(
        principal,
        bg="#f3f5f7"
    )

    controles.pack(
        pady=5
    )

    boton_iniciar = RoundedButton(
        controles, text="▶  INICIAR", command=None,
        width=150, height=48, bg="#16a34a", fg="white",
        activebackground="#15803d", activeforeground="white",
        font=("Segoe UI", 11, "bold"), radius=16
    )
    boton_pausar = RoundedButton(
        controles, text="Ⅱ  PAUSAR", command=None,
        width=150, height=48, bg="#e9a23b", fg="white",
        activebackground="#d18b28", activeforeground="white",
        font=("Segoe UI", 11, "bold"), radius=16
    )
    boton_continuar = RoundedButton(
        controles, text="▶  CONTINUAR", command=None,
        width=150, height=48, bg="#2563eb", fg="white",
        activebackground="#1d4ed8", activeforeground="white",
        font=("Segoe UI", 11, "bold"), radius=16
    )
    boton_finalizar = RoundedButton(
        controles, text="■  FINALIZAR", command=None,
        width=150, height=48, bg="#dc3545", fg="white",
        activebackground="#b91c2b", activeforeground="white",
        font=("Segoe UI", 11, "bold"), radius=16
    )

    boton_iniciar.pack(
        side="left",
        padx=5
    )

    boton_pausar.pack(
        side="left",
        padx=5
    )

    boton_continuar.pack(
        side="left",
        padx=5
    )

    boton_finalizar.pack(
        side="left",
        padx=5
    )

    # --------------------------------------------------------
    # ACTUALIZACIÓN ESP32
    # --------------------------------------------------------

    def actualizar_datos():

        if not principal.winfo_exists():
            return

        tiempo, ataques1, ataques2 = esp32.obtener_datos()
        if getattr(esp32, "conectado", False):
            estado_conexion.config(text=f"● Conectado ({puerto_var.get()})", fg="#86efac")
        else:
            estado_conexion.config(text="● No conectado", fg="#d1d5db")

        tiempo_label.config(
            text=tiempo
        )

        ataques1_label.config(
            text=str(ataques1)
        )

        ataques2_label.config(
            text=str(ataques2)
        )

        principal.after(
            100,
            actualizar_datos
        )

    actualizar_datos()

    # --------------------------------------------------------
    # INICIAR
    # --------------------------------------------------------

    def iniciar():

        actualizar_estado(
            id_batalla,
            "En curso"
        )

        esp32.reiniciar_datos()

        esp32.enviar(
            "INICIAR"
        )

        estado_label.config(
            text="EN CURSO"
        )

        boton_iniciar.config(
            state="disabled"
        )

        boton_pausar.config(
            state="normal"
        )

        boton_continuar.config(
            state="disabled"
        )

        boton_finalizar.config(
            state="normal"
        )

    # --------------------------------------------------------
    # PAUSAR
    # --------------------------------------------------------

    def pausar():

        actualizar_estado(
            id_batalla,
            "Pausada"
        )

        esp32.enviar(
            "PAUSAR"
        )

        estado_label.config(
            text="PAUSADA"
        )

        boton_pausar.config(
            state="disabled"
        )

        boton_continuar.config(
            state="normal"
        )

    # --------------------------------------------------------
    # CONTINUAR
    # --------------------------------------------------------

    def continuar():

        actualizar_estado(
            id_batalla,
            "En curso"
        )

        esp32.enviar(
            "CONTINUAR"
        )

        estado_label.config(
            text="EN CURSO"
        )

        boton_pausar.config(
            state="normal"
        )

        boton_continuar.config(
            state="disabled"
        )

    # --------------------------------------------------------
    # FINALIZAR
    # --------------------------------------------------------

    def finalizar():

        # SIN CONFIRMACIÓN
        esp32.enviar(
            "FINALIZAR"
        )

        boton_iniciar.config(
            state="disabled"
        )

        boton_pausar.config(
            state="disabled"
        )

        boton_continuar.config(
            state="disabled"
        )

        boton_finalizar.config(
            state="disabled"
        )

        abrir_resultado(
            contenedor.winfo_toplevel(),
            batalla,
            lambda: mostrar_batallas(contenedor)
        )

    # --------------------------------------------------------
    # ASIGNAR BOTONES
    # --------------------------------------------------------

    boton_iniciar.config(
        command=iniciar
    )

    boton_pausar.config(
        command=pausar
    )

    boton_continuar.config(
        command=continuar
    )

    boton_finalizar.config(
        command=finalizar
    )

    # --------------------------------------------------------
    # ESTADO INICIAL
    # --------------------------------------------------------

    if estado == "Pendiente":

        boton_iniciar.config(
            state="normal"
        )

        boton_pausar.config(
            state="disabled"
        )

        boton_continuar.config(
            state="disabled"
        )

        boton_finalizar.config(
            state="disabled"
        )

    elif estado == "En curso":

        boton_iniciar.config(
            state="disabled"
        )

        boton_pausar.config(
            state="normal"
        )

        boton_continuar.config(
            state="disabled"
        )

        boton_finalizar.config(
            state="normal"
        )

    elif estado == "Pausada":

        boton_iniciar.config(
            state="disabled"
        )

        boton_pausar.config(
            state="disabled"
        )

        boton_continuar.config(
            state="normal"
        )

        boton_finalizar.config(
            state="normal"
        )
