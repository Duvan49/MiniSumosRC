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
    ).pack(anchor="w", pady=(0, 6))

    tk.Label(
        principal,
        text="Posiciones actualizadas automáticamente mientras se registran los resultados.",
        font=("Arial", 11), fg=GRIS, bg=FONDO
    ).pack(anchor="w", pady=(0, 14))

    marco_acciones = tk.Frame(principal, bg=FONDO)
    marco_acciones.pack(fill="x", pady=(0, 12))

    boton_avanzar = ttk.Button(marco_acciones, text="GENERAR SIGUIENTE FASE", state="disabled")
    boton_avanzar.pack(side="left")

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

    def avanzar():
        try:
            fase = estado_fase()
        except sqlite3.Error as error:
            messagebox.showerror("Error de base de datos", str(error), parent=contenedor.winfo_toplevel())
            return

        if fase["hay_grupos"]:
            confirmar = messagebox.askyesno(
                "Generar llaves",
                "La fase de grupos terminó. Se calcularán los clasificados y se generará el cuadro eliminatorio. ¿Continuar?",
                parent=contenedor.winfo_toplevel()
            )
            if not confirmar:
                return
            exito, mensaje = generar_llaves_manualmente()
            titulo = "Llaves generadas" if exito else "No se pudieron generar las llaves"
        else:
            confirmar = messagebox.askyesno(
                "Generar final",
                "Todos contra todos terminó. Se generará la final entre los dos mejores de la clasificación. ¿Continuar?",
                parent=contenedor.winfo_toplevel()
            )
            if not confirmar:
                return
            exito, mensaje = generar_final_todos_manualmente()
            titulo = "Final generada" if exito else "No se pudo generar la final"

        if exito:
            messagebox.showinfo(titulo, mensaje, parent=contenedor.winfo_toplevel())
        else:
            messagebox.showwarning(titulo, mensaje, parent=contenedor.winfo_toplevel())
        cargar()

    boton_avanzar.configure(command=avanzar)

    def cargar():
        try:
            filas = obtener_tabla_clasificacion()
            fase = estado_fase()
        except (sqlite3.Error, KeyError, TypeError) as error:
            tabla.delete(*tabla.get_children())
            estado.config(text=f"No se pudo calcular la clasificación: {error}", fg=ROJO)
            boton_avanzar.configure(state="disabled", text="FASE NO DISPONIBLE")
            return

        tabla.delete(*tabla.get_children())
        if not filas:
            estado.config(
                text="Prepara la competencia y registra resultados para ver la clasificación.",
                fg=GRIS
            )
        else:
            hay_grupos = fase["hay_grupos"]
            for fila in filas:
                grupo = fila.get("grupo") or "—"
                valores = (
                    f'{fila.get("posicion_grupo", "—")}°',
                    fila.get("robot") or "—",
                    grupo if hay_grupos else "Todos contra todos",
                    fila.get("puntos", 0),
                    fila.get("tiempo_mostrar", "—"),
                    f'{(fila.get("porcentaje_ataques") or 0):.1f}%',
                    f'{(fila.get("porcentaje_victorias") or 0):.1f}%',
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

        if fase["hay_grupos"]:
            if fase["total_llaves"] > 0:
                boton_avanzar.configure(state="disabled", text="LLAVES YA GENERADAS")
            elif fase["total_grupos"] > 0 and fase["pendientes_grupos"] == 0:
                boton_avanzar.configure(state="normal", text="GENERAR LLAVES")
            else:
                boton_avanzar.configure(state="disabled", text="ESPERANDO FIN DE GRUPOS")
        elif fase["total_todos"] > 0:
            if fase["total_finales"] > 0:
                boton_avanzar.configure(state="disabled", text="FINAL YA GENERADA")
            elif fase["pendientes_todos"] == 0:
                boton_avanzar.configure(state="normal", text="GENERAR FINAL")
            else:
                boton_avanzar.configure(state="disabled", text="ESPERANDO FIN DE TODOS CONTRA TODOS")
        else:
            boton_avanzar.configure(state="disabled", text="NO HAY FASE CLASIFICATORIA")

    def actualizar_periodicamente():
        if not principal.winfo_exists():
            return
        cargar()
        principal.after(2000, actualizar_periodicamente)

    ttk.Button(marco_acciones, text="ACTUALIZAR AHORA", command=cargar).pack(side="left", padx=(10, 0))
    cargar()
    principal.after(2000, actualizar_periodicamente)
