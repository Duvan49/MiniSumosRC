import tkinter as tk
from tkinter import messagebox
import sqlite3
import os
import threading
from tkinter import ttk
from serial.tools import list_ports

from Interfaz.esp32 import esp32


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

    cabecera_resultado = tk.Frame(principal, bg="#922b2b", height=90)
    cabecera_resultado.pack(fill="x", pady=(0, 18))
    cabecera_resultado.pack_propagate(False)

    tk.Label(
        cabecera_resultado,
        text=f"RESULTADO • BATALLA {id_batalla}",
        font=("Segoe UI", 22, "bold"),
        fg="white", bg="#922b2b"
    ).pack(side="left", padx=20, expand=True)

    tk.Label(
        cabecera_resultado,
        text=grupo or etapa,
        font=("Segoe UI", 10, "bold"),
        fg="white", bg="#7f1d1d", padx=12, pady=7
    ).pack(side="right", padx=18)

    # --------------------------------------------------------
    # DATOS
    # --------------------------------------------------------

    datos = tk.Frame(
        principal,
        bg="white",
        highlightbackground="#d9dee3",
        highlightthickness=1
    )

    datos.pack(
        fill="x",
        pady=(0, 20)
    )

    for columna in range(3):
        datos.grid_columnconfigure(columna, weight=1)

    estadisticas = [
        ("ATAQUES R1", str(ataques1)),
        ("TIEMPO", tiempo),
        ("ATAQUES R2", str(ataques2)),
    ]

    for columna, (titulo, valor) in enumerate(estadisticas):
        tk.Label(
            datos, text=titulo,
            font=("Segoe UI", 9, "bold"),
            fg="#7a858e", bg="white"
        ).grid(row=0, column=columna, padx=18, pady=(12, 0), sticky="ew")

        tk.Label(
            datos, text=valor,
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

    boton1 = tk.Radiobutton(
        marco_ganadores,
        text=f"{nombre1}\n{robot1}",
        variable=ganador,
        value=participante1,
        indicatoron=False,
        font=("Segoe UI", 13, "bold"),
        height=3,
        bg="white",
        fg="#17202a",
        selectcolor="#dbeafe",
        activebackground="#eef6ff",
        relief="solid",
        bd=1,
        cursor="hand2"
    )

    boton1.pack(
        side="left",
        expand=True,
        fill="both",
        padx=(0, 7)
    )

    boton2 = tk.Radiobutton(
        marco_ganadores,
        text=f"{nombre2}\n{robot2}",
        variable=ganador,
        value=participante2,
        indicatoron=False,
        font=("Segoe UI", 13, "bold"),
        height=3,
        bg="white",
        fg="#17202a",
        selectcolor="#dbeafe",
        activebackground="#eef6ff",
        relief="solid",
        bd=1,
        cursor="hand2"
    )

    boton2.pack(
        side="left",
        expand=True,
        fill="both",
        padx=(7, 0)
    )

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

    for texto in criterios:

        boton = tk.Radiobutton(
            marco_criterios,
            text=texto,
            variable=criterio,
            value=texto,
            indicatoron=False,
            font=("Segoe UI", 11, "bold"),
            height=1,
            bg="white",
            fg="#263238",
            selectcolor="#dbeafe",
            activebackground="#eef6ff",
            relief="solid",
            bd=1,
            cursor="hand2"
        )

        boton.pack(
            fill="x",
            pady=2
        )

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

    encabezado = tk.Frame(
        principal,
        bg="#922b2b",
        height=110
    )

    encabezado.pack(
        fill="x"
    )

    encabezado.pack_propagate(False)

    tk.Label(
        encabezado,
        text=f"BATALLA {id_batalla}",
        font=("Segoe UI", 28, "bold"),
        fg="white",
        bg="#922b2b"
    ).pack(
        side="left",
        padx=40
    )

    informacion = etapa

    if grupo:
        informacion += f"   •   {grupo}"

    informacion += f"   •   Ronda {ronda}"

    tk.Label(
        encabezado,
        text=informacion,
        font=("Segoe UI", 11),
        fg="#fbeaea",
        bg="#922b2b"
    ).pack(
        side="right",
        padx=40
    )

    # Selector de puerto y estado real de conexión
    zona_puerto = tk.Frame(encabezado, bg="#922b2b")
    zona_puerto.pack(side="right", padx=(10, 22), pady=8)

    puertos_disponibles = [p.device for p in list_ports.comports()]
    if not puertos_disponibles:
        puertos_disponibles = ["COM4"]

    puerto_var = tk.StringVar(value=puertos_disponibles[0])
    selector_puerto = ttk.Combobox(
        zona_puerto, textvariable=puerto_var,
        values=puertos_disponibles, width=12, state="readonly"
    )
    selector_puerto.pack(pady=(0, 3))

    estado_conexion = tk.Label(
        zona_puerto, text="● No conectado",
        font=("Segoe UI", 9, "bold"), fg="#d1d5db", bg="#922b2b"
    )
    estado_conexion.pack()

    def refrescar_puertos():
        encontrados = [p.device for p in list_ports.comports()]
        if not encontrados:
            encontrados = ["COM4"]
        actual = puerto_var.get()
        selector_puerto.configure(values=encontrados)
        if actual not in encontrados:
            puerto_var.set(encontrados[0])

    def conectar_puerto(event=None, mostrar_error=False):
        try:
            correcto = esp32.conectar(puerto_var.get())
            if correcto:
                estado_conexion.config(text=f"● Conectado ({puerto_var.get()})", fg="#86efac")
            else:
                estado_conexion.config(text="● No conectado", fg="#d1d5db")
        except Exception as error:
            estado_conexion.config(text="● No conectado", fg="#d1d5db")
            if mostrar_error:
                messagebox.showerror(
                    "Conexión ESP32", str(error),
                    parent=contenedor.winfo_toplevel()
                )

    selector_puerto.bind(
        "<<ComboboxSelected>>",
        lambda evento: conectar_puerto(evento, True)
    )
    conectar_puerto()

    # --------------------------------------------------------
    # ESTADO
    # --------------------------------------------------------

    estado_frame = tk.Frame(
        principal,
        bg="#f3f5f7"
    )

    estado_frame.pack(
        pady=18
    )

    estado_label = tk.Label(
        estado_frame,
        text=estado.upper(),
        font=("Segoe UI", 11, "bold"),
        fg="#17202a",
        bg="#e8eeee",
        padx=25,
        pady=7
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

    tarjeta1 = tk.Frame(
        combate,
        bg="#ffffff",
        highlightbackground="#d7dde2",
        highlightthickness=1
    )

    tarjeta1.pack(
        side="left",
        expand=True,
        fill="both",
        ipady=18
    )

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
        tarjeta1,
        text=nombre1,
        font=("Segoe UI", 21, "bold"),
        fg="#17202a",
        bg="white"
    ).pack()

    tk.Label(
        tarjeta1,
        text=robot1,
        font=("Segoe UI", 12),
        fg="#68737d",
        bg="white"
    ).pack(
        pady=(4, 10)
    )

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

    tarjeta2 = tk.Frame(
        combate,
        bg="#ffffff",
        highlightbackground="#d7dde2",
        highlightthickness=1
    )

    tarjeta2.pack(
        side="left",
        expand=True,
        fill="both",
        ipady=18
    )

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
        tarjeta2,
        text=nombre2,
        font=("Segoe UI", 21, "bold"),
        fg="#17202a",
        bg="white"
    ).pack()

    tk.Label(
        tarjeta2,
        text=robot2,
        font=("Segoe UI", 12),
        fg="#68737d",
        bg="white"
    ).pack(
        pady=(4, 10)
    )

    # --------------------------------------------------------
    # PANEL TIEMPO / ATAQUES
    # --------------------------------------------------------

    datos = tk.Frame(
        principal,
        bg="white",
        highlightbackground="#d7dde2",
        highlightthickness=1
    )

    datos.pack(
        fill="x",
        padx=60,
        pady=20
    )

    # Tiempo
    tk.Label(
        datos,
        text="◷  TIEMPO",
        font=("Segoe UI", 9, "bold"),
        fg="#7a858e",
        bg="white"
    ).grid(
        row=0,
        column=0,
        pady=(12, 0)
    )

    tiempo_label = tk.Label(
        datos,
        text="--:--",
        font=("Segoe UI", 25, "bold"),
        fg="#17202a",
        bg="white"
    )

    tiempo_label.grid(
        row=1,
        column=0,
        padx=70,
        pady=(0, 12)
    )

    # Ataques 1
    tk.Label(
        datos,
        text="⚔  ATAQUES R1",
        font=("Segoe UI", 9, "bold"),
        fg="#7a858e",
        bg="white"
    ).grid(
        row=0,
        column=1,
        pady=(12, 0)
    )

    ataques1_label = tk.Label(
        datos,
        text="0",
        font=("Segoe UI", 25, "bold"),
        fg="#17202a",
        bg="white"
    )

    ataques1_label.grid(
        row=1,
        column=1,
        padx=70,
        pady=(0, 12)
    )

    # Ataques 2
    tk.Label(
        datos,
        text="⚔  ATAQUES R2",
        font=("Segoe UI", 9, "bold"),
        fg="#7a858e",
        bg="white"
    ).grid(
        row=0,
        column=2,
        pady=(12, 0)
    )

    ataques2_label = tk.Label(
        datos,
        text="0",
        font=("Segoe UI", 25, "bold"),
        fg="#17202a",
        bg="white"
    )

    ataques2_label.grid(
        row=1,
        column=2,
        padx=70,
        pady=(0, 12)
    )

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

    boton_iniciar = tk.Button(
        controles,
        text="▶  INICIAR",
        command=None,
        font=("Segoe UI", 11, "bold"),
        width=13,
        height=2,
        bg="#2563eb",
        fg="white",
        activebackground="#1d4ed8",
        activeforeground="white",
        relief="flat",
        cursor="hand2"
    )

    boton_pausar = tk.Button(
        controles,
        text="Ⅱ  PAUSAR",
        command=None,
        font=("Segoe UI", 11, "bold"),
        width=13,
        height=2,
        bg="#e9a23b",
        fg="white",
        activebackground="#d18b28",
        activeforeground="white",
        relief="flat",
        cursor="hand2"
    )

    boton_continuar = tk.Button(
        controles,
        text="▶  CONTINUAR",
        command=None,
        font=("Segoe UI", 11, "bold"),
        width=13,
        height=2,
        bg="#2563eb",
        fg="white",
        activebackground="#1d4ed8",
        activeforeground="white",
        relief="flat",
        cursor="hand2"
    )

    boton_finalizar = tk.Button(
        controles,
        text="■  FINALIZAR",
        command=None,
        font=("Segoe UI", 11, "bold"),
        width=13,
        height=2,
        bg="#dc3545",
        fg="white",
        activebackground="#b91c2b",
        activeforeground="white",
        relief="flat",
        cursor="hand2"
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
