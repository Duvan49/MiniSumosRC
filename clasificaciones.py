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

    marco_acciones = tk.Frame(principal, bg=FONDO)
    marco_acciones.pack(fill="x", pady=(0, 12))

    estado_texto = tk.Label(
        marco_acciones, text="", font=("Arial", 10),
        bg=FONDO, fg=GRIS, anchor="w"
    )
    estado_texto.pack(side="left", fill="x", expand=True)

    boton_continuar = tk.Button(
        marco_acciones, text="", font=("Arial", 10, "bold"),
        bg=ROJO, fg="#FFFFFF", activebackground=ROJO_OSCURO,
        activeforeground="#FFFFFF", relief="flat", bd=0,
        cursor="hand2", padx=16, pady=9
    )

    marco = tk.Frame(principal, bg=FONDO)
    marco.pack(fill="both", expand=True)

    columnas = ("posicion", "grupo", "robot", "puntos", "tiempo", "ataques", "victorias")
    tabla = ttk.Treeview(marco, columns=columnas, show="headings")
    for col, titulo, ancho in [
        ("posicion", "POS.", 70),
        ("grupo", "GRUPO", 100),
        ("robot", "ROBOT", 220),
        ("puntos", "PTS.", 90),
        ("tiempo", "TIEMPO PROM.", 165),
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

    def continuar_fase(tipo):
        if tipo == "llaves":
            exito, mensaje = generar_llaves_manualmente()
        else:
            exito, mensaje = generar_final_todos_manualmente()

        if exito:
            messagebox.showinfo("Fase preparada", mensaje, parent=contenedor.winfo_toplevel())
            mostrar_clasificaciones(contenedor)
        else:
            messagebox.showwarning("No se pudo continuar", mensaje, parent=contenedor.winfo_toplevel())

    def actualizar_acciones(estado):
        boton_continuar.pack_forget()
        estado_texto.config(text="")
        if estado["hay_grupos"]:
            if estado["total_grupos"] and estado["pendientes_grupos"] == 0 and not estado["total_llaves"]:
                estado_texto.config(text="La fase de grupos terminó. Revisa la clasificación y genera las llaves.")
                boton_continuar.config(
                    text="GENERAR LLAVES",
                    command=lambda: continuar_fase("llaves")
                )
                boton_continuar.pack(side="right")
            elif estado["total_llaves"]:
                estado_texto.config(text="Las llaves ya están preparadas. Abre Eliminatorias para revisar el cuadro y continuar.")
            elif estado["total_grupos"]:
                estado_texto.config(text="La clasificación se actualiza a medida que se completan las batallas de grupos.")
        elif estado["total_todos"] and estado["pendientes_todos"] == 0 and not estado["total_finales"]:
            estado_texto.config(text="Todos contra todos terminó. Revisa la clasificación antes de generar la final.")
            boton_continuar.config(
                text="CONTINUAR CON LA FINAL",
                command=lambda: continuar_fase("final")
            )
            boton_continuar.pack(side="right")
        elif estado["total_finales"] and estado["total_todos"]:
            estado_texto.config(text="La final está preparada. Abre Batallas para disputarla.")
        elif estado["total_todos"]:
            estado_texto.config(text="La clasificación se actualiza a medida que se completan los combates.")

    def cargar():
        try:
            filas = obtener_tabla_clasificacion() or []
            estado = estado_fase()
        except (sqlite3.Error, KeyError, TypeError) as error:
            print(f"No se pudo actualizar la clasificación: {error}")
            return

        actualizar_acciones(estado)
        tabla.delete(*tabla.get_children())
        hay_grupos = estado["hay_grupos"]

        for fila in filas:
            if hay_grupos:
                grupo = (fila.get("grupo") or "").replace("Grupo ", "")
                if grupo == "Todos contra todos":
                    grupo = ""
                if not fila.get("ha_competido"):
                    grupo = ""
            else:
                grupo = "N/A"

            if not fila.get("ha_competido"):
                valores = (
                    f'{fila.get("posicion", fila.get("posicion_grupo", "—"))}°',
                    grupo, fila.get("robot") or "—", "", "", "", ""
                )
                tag = "sin_jugar"
            else:
                valores = (
                    f'{fila.get("posicion", fila.get("posicion_grupo", "—"))}°',
                    grupo,
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
