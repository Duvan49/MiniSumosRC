import os
import sqlite3
from contextlib import closing
import tkinter as tk
from tkinter import ttk
from llaves import obtener_tabla_clasificacion

FONDO = "#FFFFFF"
ROJO = "#C62828"
ROJO_OSCURO = "#8E1B1B"
VERDE = "#DCFCE7"
VERDE_TEXTO = "#166534"
ROJO_FONDO = "#FEE2E2"
ROJO_TEXTO = "#991B1B"
GRIS = "#666666"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(BASE_DIR).lower() == "interfaz":
    BASE_DIR = os.path.dirname(BASE_DIR)
RUTA_BD = os.path.join(BASE_DIR, "BasesDeDatos", "competencia.db")

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
    ).pack(anchor="w", pady=(0, 14))

    marco = tk.Frame(principal, bg=FONDO)
    marco.pack(fill="both", expand=True)

    columnas = ("posicion", "robot", "puntos", "tiempo", "ataques", "victorias")
    tabla = ttk.Treeview(marco, columns=columnas, show="headings")
    for col, titulo, ancho in [
        ("posicion", "POSICIÓN", 90),
        ("robot", "ROBOT", 220),
        ("puntos", "PUNTOS", 100),
        ("tiempo", "TIEMPO PROM. (M:S:CS)", 190),
        ("ataques", "% ATAQUES", 135),
        ("victorias", "% VICTORIAS", 135),
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
    tabla.tag_configure(
        "encabezado_grupo", background="#DBEAFE", foreground="#1E3A8A",
        font=("Arial", 10, "bold")
    )

    def cargar():
        try:
            filas = obtener_tabla_clasificacion() or []
            estado = estado_fase()
        except (sqlite3.Error, KeyError, TypeError) as error:
            print(f"No se pudo actualizar la clasificación: {error}")
            return

        tabla.delete(*tabla.get_children())
        hay_grupos = estado["hay_grupos"]

        if hay_grupos:
            grupos = {}
            for fila in filas:
                nombre_grupo = (fila.get("grupo") or "Sin grupo").strip()
                if nombre_grupo == "Todos contra todos":
                    nombre_grupo = "Sin grupo"
                grupos.setdefault(nombre_grupo, []).append(fila)

            # La clasificación conserva el orden estadístico calculado por llaves.py,
            # pero la posición visible se reinicia dentro de cada grupo.
            for nombre_grupo in sorted(grupos, key=str.casefold):
                etiqueta = nombre_grupo.upper()
                tabla.insert(
                    "", "end",
                    values=("", etiqueta, "", "", "", ""),
                    tags=("encabezado_grupo",)
                )

                for posicion_grupo, fila in enumerate(grupos[nombre_grupo], 1):
                    if not fila.get("ha_competido"):
                        valores = (
                            f"{posicion_grupo}°", "", "", "", "", ""
                        )
                        tag = "sin_jugar"
                    else:
                        valores = (
                            f"{posicion_grupo}°",
                            fila.get("robot") or "—",
                            fila.get("puntos", 0),
                            fila.get("tiempo_mostrar", "0:00:00"),
                            f'{(fila.get("porcentaje_ataques") or 0):.1f}%',
                            f'{(fila.get("porcentaje_victorias") or 0):.1f}%',
                        )
                        tag = "clasifica" if fila.get("clasifica") else "eliminado"
                    tabla.insert("", "end", values=valores, tags=(tag,))
        else:
            tabla.insert(
                "", "end",
                values=("", "TODOS CONTRA TODOS", "", "", "", ""),
                tags=("encabezado_grupo",)
            )
            for fila in filas:
                if not fila.get("ha_competido"):
                    valores = (
                        f'{fila.get("posicion", "—")}°', "", "", "", "", ""
                    )
                    tag = "sin_jugar"
                else:
                    valores = (
                        f'{fila.get("posicion", "—")}°',
                        fila.get("robot") or "—",
                        fila.get("puntos", 0),
                        fila.get("tiempo_mostrar", "0:00:00"),
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
