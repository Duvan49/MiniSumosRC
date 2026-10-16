import os
import sqlite3
from contextlib import closing
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from .llaves import (
        obtener_tabla_clasificacion,
        generar_llaves_manualmente,
        generar_final_todos_manualmente,
    )
except ImportError:
    from llaves import (
        obtener_tabla_clasificacion,
        generar_llaves_manualmente,
        generar_final_todos_manualmente,
    )

FONDO = "#FFFFFF"
ROJO = "#C62828"
ROJO_OSCURO = "#8E1B1B"
VERDE = "#DCFCE7"
VERDE_TEXTO = "#166534"
ROJO_FONDO = "#FEE2E2"
ROJO_TEXTO = "#991B1B"
GRIS = "#666666"

RUTA_BD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "BasesDeDatos",
    "competencia.db",
)

def estado_fase():
    with closing(sqlite3.connect(RUTA_BD)) as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM grupo_participantes")
        hay_grupos = cursor.fetchone()[0] > 0

        cursor.execute("SELECT COUNT(*) FROM enfrentamientos WHERE etapa = 'Grupo'")
        total_grupos = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM enfrentamientos WHERE etapa = 'Grupo' AND estado != 'Completado'")
        pendientes_grupos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM enfrentamientos WHERE etapa = 'Todos'")
        total_todos = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM enfrentamientos WHERE etapa = 'Todos' AND estado != 'Completado'")
        pendientes_todos = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM llaves")
        total_llaves = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM enfrentamientos WHERE etapa = 'Final'")
        total_finales = cursor.fetchone()[0]

    return {
        "hay_grupos": hay_grupos,
        "total_grupos": total_grupos,
        "pendientes_grupos": pendientes_grupos,
        "total_todos": total_todos,
        "pendientes_todos": pendientes_todos,
        "total_llaves": total_llaves,
        "total_finales": total_finales,
    }

def mostrar_clasificaciones(contenedor):
    for widget in contenedor.winfo_children():
        widget.destroy()

    principal = tk.Frame(contenedor, bg=FONDO)
    principal.pack(fill="both", expand=True, padx=36, pady=28)

    tk.Label(
        principal, text="CLASIFICACIONES",
        font=("Arial", 20, "bold"), fg=ROJO_OSCURO, bg=FONDO
    ).pack(anchor="w", pady=(0, 20))

    marco = tk.Frame(principal, bg=FONDO)
    marco.pack(fill="both", expand=True)

    columnas = ("posicion", "robot", "puntos", "tiempo", "ataques", "victorias")
    tabla = ttk.Treeview(marco, columns=columnas, show="headings")
    for col, titulo, ancho in [
        ("posicion", "POS.", 75),
        ("robot", "ROBOT", 240),
        ("puntos", "PUNTOS", 110),
        ("tiempo", "TIEMPO PROM.", 165),
        ("ataques", "% ATAQUES", 145),
        ("victorias", "% VICTORIAS", 145),
    ]:
        tabla.heading(col, text=titulo)
        tabla.column(col, width=ancho, anchor="center", stretch=True)

    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)
    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")

    tabla.tag_configure("clasifica", background=VERDE, foreground=VERDE_TEXTO)
    tabla.tag_configure("eliminado", background=ROJO_FONDO, foreground=ROJO_TEXTO)
    tabla.tag_configure("sin_jugar", background="#FFFFFF", foreground="#64748B")

    def cargar():
        try:
            filas = obtener_tabla_clasificacion() or []
        except (sqlite3.Error, KeyError, TypeError) as error:
            print(f"No se pudo actualizar la clasificación: {error}")
            return

        tabla.delete(*tabla.get_children())
        for fila in filas:
            if not fila.get("ha_competido"):
                valores = (
                    f'{fila.get("posicion", fila.get("posicion_grupo", "—"))}°',
                    "", "", "", "", ""
                )
                tag = "sin_jugar"
            else:
                valores = (
                    f'{fila.get("posicion", fila.get("posicion_grupo", "—"))}°',
                    fila.get("robot") or "—",
                    fila.get("puntos", 0),
                    fila.get("tiempo_mostrar", "—"),
                    f'{(fila.get("porcentaje_ataques") or 0):.1f}%',
                    f'{(fila.get("porcentaje_victorias") or 0):.1f}%',
                )
                tag = "clasifica" if fila.get("clasifica") else "eliminado"
            tabla.insert("", "end", values=valores, tags=(tag,))

    def actualizar_periodicamente():
        if not principal.winfo_exists():
            return
        cargar()
        principal.after(1000, actualizar_periodicamente)

    cargar()
    principal.after(1000, actualizar_periodicamente)
