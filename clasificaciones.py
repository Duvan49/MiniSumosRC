import os
import sqlite3
from contextlib import closing
import tkinter as tk
from tkinter import ttk

try:
    from .llaves import obtener_tabla_clasificacion
except ImportError:
    from llaves import obtener_tabla_clasificacion

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

def cantidad_participantes():
    with closing(sqlite3.connect(RUTA_BD)) as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM participantes")
        return cursor.fetchone()[0]

def mostrar_clasificaciones(contenedor):
    for widget in contenedor.winfo_children():
        widget.destroy()

    principal = tk.Frame(contenedor, bg=FONDO)
    principal.pack(fill="both", expand=True, padx=36, pady=28)

    tk.Label(
        principal, text="CLASIFICACIONES",
        font=("Arial", 20, "bold"), fg=ROJO_OSCURO, bg=FONDO
    ).pack(anchor="w", pady=(0, 6))

    tk.Label(
        principal,
        text="Se actualiza automáticamente mientras se registran los resultados.",
        font=("Arial", 11), fg=GRIS, bg=FONDO
    ).pack(anchor="w", pady=(0, 18))

    marco = tk.Frame(principal, bg=FONDO)
    marco.pack(fill="both", expand=True)

    columnas = ("posicion", "robot", "grupo", "puntos", "tiempo", "ataques", "victorias")
    tabla = ttk.Treeview(marco, columns=columnas, show="headings")
    encabezados = [
        ("posicion", "POS.", 75),
        ("robot", "ROBOT", 210),
        ("grupo", "GRUPO", 130),
        ("puntos", "PUNTOS", 100),
        ("tiempo", "TIEMPO PROM.", 145),
        ("ataques", "% ATAQUES", 125),
        ("victorias", "% VICTORIAS", 125),
    ]
    for col, titulo, ancho in encabezados:
        tabla.heading(col, text=titulo)
        tabla.column(col, width=ancho, anchor="center", stretch=True)

    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)
    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    tabla.tag_configure("clasifica", background=VERDE, foreground=VERDE_TEXTO)
    tabla.tag_configure("eliminado", background=ROJO_FONDO, foreground=ROJO_TEXTO)

    estado = tk.Label(principal, text="", font=("Arial", 11), bg=FONDO, fg=GRIS)
    estado.pack(anchor="w", pady=(10, 0))

    def cargar():
        try:
            filas = obtener_tabla_clasificacion()
            cantidad = cantidad_participantes()
        except (sqlite3.Error, KeyError, TypeError) as error:
            estado.config(text=f"Aún no se puede calcular la clasificación: {error}", fg=ROJO)
            return

        tabla.delete(*tabla.get_children())
        if not filas:
            estado.config(
                text="Prepara la competencia y registra resultados para ver la clasificación.",
                fg=GRIS
            )
            return

        hay_grupos = any(fila.get("grupo") for fila in filas)
        for fila in filas:
            grupo = fila.get("grupo") or "—"
            valores = (
                f'{fila.get("posicion_grupo", "—")}°',
                fila.get("robot") or "—",
                grupo if hay_grupos else "Todos contra todos",
                fila.get("puntos", 0),
                fila.get("tiempo_mostrar", "—"),
                f'{fila.get("porcentaje_ataques", 0):.1f}%',
                f'{fila.get("porcentaje_victorias", 0):.1f}%',
            )
            tabla.insert(
                "", "end", values=valores,
                tags=("clasifica" if fila.get("clasifica") else "eliminado",)
            )

        clasificados = sum(1 for fila in filas if fila.get("clasifica"))
        estado.config(
            text=f"{len(filas)} participantes • {clasificados} plazas clasificatorias • actualización automática cada 2 s",
            fg=GRIS
        )

    def actualizar_periodicamente():
        if not principal.winfo_exists():
            return
        cargar()
        principal.after(2000, actualizar_periodicamente)

    ttk.Button(principal, text="ACTUALIZAR AHORA", command=cargar).pack(anchor="e", pady=(10, 0))
    cargar()
    principal.after(2000, actualizar_periodicamente)
