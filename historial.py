import os
import sqlite3
import tkinter as tk
from tkinter import ttk

FONDO = "#FFFFFF"
ROJO_OSCURO = "#8E1B1B"
TEXTO = "#1F2937"
GRIS = "#64748B"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(BASE_DIR).lower() == "interfaz":
    BASE_DIR = os.path.dirname(BASE_DIR)
RUTA_BD = os.path.join(BASE_DIR, "BasesDeDatos", "competencia.db")


def conectar():
    return sqlite3.connect(RUTA_BD)


def obtener_historial():
    """Devuelve los enfrentamientos ordenados por el número de batalla."""
    with conectar() as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT
                e.id,
                COALESCE(p1.robot, '—'),
                COALESCE(p2.robot, '—'),
                COALESCE(e.tiempo, ''),
                COALESCE(e.ataques1, ''),
                COALESCE(e.ataques2, ''),
                COALESCE(pg.robot, CASE
                    WHEN e.estado = 'Completado' THEN 'Sin ganador'
                    ELSE 'Pendiente'
                END),
                COALESCE(e.criterio_ganador, '')
            FROM enfrentamientos e
            LEFT JOIN participantes p1 ON p1.id = e.participante1
            LEFT JOIN participantes p2 ON p2.id = e.participante2
            LEFT JOIN participantes pg ON pg.id = e.ganador
            ORDER BY e.id
        """)
        return cursor.fetchall()


def mostrar_historial(contenedor):
    for widget in contenedor.winfo_children():
        widget.destroy()

    principal = tk.Frame(contenedor, bg=FONDO)
    principal.pack(fill="both", expand=True, padx=36, pady=28)

    tk.Label(
        principal,
        text="HISTORIAL DE BATALLAS",
        font=("Arial", 16, "bold"),
        fg=ROJO_OSCURO,
        bg=FONDO
    ).pack(anchor="w", pady=(0, 14))

    marco = tk.Frame(principal, bg=FONDO)
    marco.pack(fill="both", expand=True)

    columnas = ("numero", "robot1", "robot2", "tiempo", "ataques1", "ataques2", "ganador", "motivo")
    tabla = ttk.Treeview(marco, columns=columnas, show="headings", height=16)

    encabezados = [
        ("numero", "N°", 65),
        ("robot1", "ROBOT 1", 155),
        ("robot2", "ROBOT 2", 155),
        ("tiempo", "TIEMPO", 125),
        ("ataques1", "ATQ. 1", 85),
        ("ataques2", "ATQ. 2", 85),
        ("ganador", "GANADOR", 155),
        ("motivo", "MOTIVO", 190),
    ]
    for columna, titulo, ancho in encabezados:
        tabla.heading(columna, text=titulo)
        tabla.column(columna, width=ancho, minwidth=55, anchor="center", stretch=True)

    estilo = ttk.Style()
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass
    estilo.configure(
        "Historial.Treeview",
        rowheight=36,
        borderwidth=1,
        relief="solid",
        bordercolor="#CBD5E1",
        background="#FFFFFF",
        fieldbackground="#FFFFFF",
        foreground=TEXTO,
        font=("Arial", 12),
    )
    estilo.configure(
        "Historial.Treeview.Heading",
        borderwidth=1,
        relief="solid",
        bordercolor="#CBD5E1",
        font=("Arial", 12, "bold"),
    )
    tabla.configure(style="Historial.Treeview")
    tabla.tag_configure("completado", background="#DCFCE7", foreground="#166534")
    tabla.tag_configure("pendiente", background="#F8FAFC", foreground=GRIS)

    barra_vertical = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    barra_horizontal = ttk.Scrollbar(principal, orient="horizontal", command=tabla.xview)
    tabla.configure(yscrollcommand=barra_vertical.set, xscrollcommand=barra_horizontal.set)
    tabla.pack(side="left", fill="both", expand=True)
    barra_vertical.pack(side="right", fill="y")
    barra_horizontal.pack(fill="x")

    def cargar():
        if not principal.winfo_exists():
            return
        try:
            filas = obtener_historial()
            tabla.delete(*tabla.get_children())
            for fila in filas:
                valores = list(fila)
                valores[0] = f"{valores[0]}"
                if valores[3] is None:
                    valores[3] = ""
                if valores[4] == "":
                    valores[4] = "—"
                if valores[5] == "":
                    valores[5] = "—"
                tag = "completado" if valores[6] not in ("Pendiente", "Sin ganador") and valores[6] else "pendiente"
                tabla.insert("", "end", values=valores, tags=(tag,))
        except sqlite3.Error as error:
            print(f"No se pudo cargar el historial: {error}")
        principal.after(2000, cargar)

    cargar()
