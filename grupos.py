import os
import sqlite3
from contextlib import closing
import tkinter as tk
from tkinter import ttk

FONDO = "#FFFFFF"
ROJO = "#C62828"
ROJO_OSCURO = "#8E1B1B"
TEXTO = "#222222"
GRIS = "#666666"

RUTA_BD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "BasesDeDatos",
    "competencia.db",
)

def conectar():
    return sqlite3.connect(RUTA_BD)

def mostrar_grupos(contenedor):
    for widget in contenedor.winfo_children():
        widget.destroy()

    principal = tk.Frame(contenedor, bg=FONDO)
    principal.pack(fill="both", expand=True, padx=36, pady=28)

    tk.Label(
        principal, text="GRUPOS DE LA COMPETENCIA",
        font=("Arial", 20, "bold"), fg=ROJO_OSCURO, bg=FONDO
    ).pack(anchor="w", pady=(0, 6))

    tk.Label(
        principal,
        text="Distribución en el mismo orden en que se generaron los grupos.",
        font=("Arial", 11), fg=GRIS, bg=FONDO
    ).pack(anchor="w", pady=(0, 18))

    marco = tk.Frame(principal, bg=FONDO)
    marco.pack(fill="both", expand=True)

    columnas = ("grupo", "numero", "robot", "participante")
    tabla = ttk.Treeview(marco, columns=columnas, show="headings", height=16)
    encabezados = {
        "grupo": ("GRUPO", 170),
        "numero": ("N.º", 70),
        "robot": ("ROBOT", 280),
        "participante": ("PARTICIPANTE", 260),
    }
    for col, (titulo, ancho) in encabezados.items():
        tabla.heading(col, text=titulo)
        tabla.column(col, width=ancho, anchor="center", stretch=True)

    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)
    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")

    estado = tk.Label(principal, text="", font=("Arial", 11), bg=FONDO, fg=GRIS)
    estado.pack(anchor="w", pady=(10, 0))

    def cargar():
        tabla.delete(*tabla.get_children())
        try:
            with closing(conectar()) as conexion:
                cursor = conexion.cursor()
                cursor.execute("""
                    SELECT g.id, g.nombre, p.robot, p.nombre
                    FROM grupos g
                    LEFT JOIN grupo_participantes gp ON gp.grupo_id = g.id
                    LEFT JOIN participantes p ON p.id = gp.participante_id
                    ORDER BY g.id, p.id
                """)
                filas = cursor.fetchall()
        except sqlite3.Error as error:
            estado.config(text=f"No se pudieron leer los grupos: {error}", fg=ROJO)
            return

        if not filas:
            estado.config(
                text="Todavía no hay grupos generados. Prepara la competencia desde Enfrentamientos.",
                fg=GRIS
            )
            return

        contadores = {}
        for _, grupo, robot, participante in filas:
            contadores[grupo] = contadores.get(grupo, 0) + 1
            tabla.insert(
                "", "end",
                values=(grupo, contadores[grupo], robot or "—", participante or "—")
            )
        estado.config(text=f"{len(contadores)} grupos • {len(filas)} plazas de grupo", fg=GRIS)

    ttk.Button(principal, text="ACTUALIZAR", command=cargar).pack(anchor="e", pady=(10, 0))
    cargar()
