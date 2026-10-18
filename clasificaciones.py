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
    tabla = ttk.Treeview(marco, columns=columnas, show="headings", height=16)
    for col, titulo, ancho in [
        ("posicion", "POSICIÓN", 150),
        ("robot", "ROBOT", 220),
        ("puntos", "PUNTOS", 100),
        ("tiempo", "TIEMPO PROM.", 140),
        ("ataques", "% ATAQUES", 135),
        ("victorias", "% VICTORIAS", 135),
    ]:
        tabla.heading(col, text=titulo)
        tabla.column(col, width=ancho, anchor="center", stretch=True)

    estilo = ttk.Style()
    estilo.configure(
        "Clasificaciones.Treeview",
        rowheight=30,
        borderwidth=1,
        relief="solid",
        background="#FFFFFF",
        fieldbackground="#FFFFFF",
        foreground="#1F2937",
        font=("Arial", 10),
    )
    estilo.configure(
        "Clasificaciones.Treeview.Heading",
        borderwidth=1,
        relief="raised",
        font=("Arial", 10, "bold"),
    )
    tabla.configure(style="Clasificaciones.Treeview")

    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)
    tabla.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")

    tabla.tag_configure("clasifica", background="#DCFCE7", foreground="#166534")
    tabla.tag_configure("eliminado", background="#FEE2E2", foreground="#991B1B")
    tabla.tag_configure("pendiente", background="#FFFFFF", foreground="#1F2937")
    tabla.tag_configure("sin_jugar", background="#FFFFFF", foreground="#64748B")
    colores_grupo = [
        "#DBEAFE", "#FEF3C7", "#DCFCE7", "#FCE7F3", "#EDE9FE",
        "#FFEDD5", "#CCFBF1", "#F1F5F9", "#ECFCCB", "#F3F4F6",
    ]
    for indice, color in enumerate(colores_grupo):
        tabla.tag_configure(
            f"encabezado_grupo_{indice}",
            background=color,
            foreground="#1F2937",
            font=("Arial", 10, "bold"),
        )

    leyenda = tk.Frame(principal, bg=FONDO)
    leyenda.pack(anchor="w", pady=(12, 0))
    tk.Label(
        leyenda, text="■ Clasifica", bg=FONDO, fg="#166534",
        font=("Arial", 10, "bold")
    ).pack(side="left", padx=(0, 18))
    tk.Label(
        leyenda, text="■ No clasifica", bg=FONDO, fg="#991B1B",
        font=("Arial", 10, "bold")
    ).pack(side="left")

    def clave_grupo(fila):
        # Durante la fase en curso, quienes aún no han competido quedan al final.
        if not fila.get("ha_competido"):
            return (1, 0, 0, float("inf"), 0, fila.get("id", 0))
        tiempo = fila.get("tiempo_promedio")
        return (
            0,
            -float(fila.get("puntos") or 0),
            -float(fila.get("porcentaje_ataques") or 0),
            float("inf") if tiempo is None else float(tiempo),
            -float(fila.get("porcentaje_victorias") or 0),
            fila.get("id", 0),
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
            fase_terminada = (
                estado["total_grupos"] > 0
                and estado["pendientes_grupos"] == 0
            )
        else:
            fase_terminada = (
                estado["total_todos"] > 0
                and estado["pendientes_todos"] == 0
            )

        if hay_grupos:
            grupos = {}
            for fila in filas:
                nombre_grupo = (fila.get("grupo") or "Sin grupo").strip()
                if nombre_grupo == "Todos contra todos":
                    nombre_grupo = "Sin grupo"
                grupos.setdefault(nombre_grupo, []).append(fila)

            for indice, nombre_grupo in enumerate(sorted(grupos, key=str.casefold)):
                etiqueta = nombre_grupo.upper()
                tabla.insert(
                    "", "end",
                    values=(etiqueta, "", "", "", "", ""),
                    tags=(f"encabezado_grupo_{indice % len(colores_grupo)}",)
                )

                filas_grupo = sorted(grupos[nombre_grupo], key=clave_grupo)
                for posicion_grupo, fila in enumerate(filas_grupo, 1):
                    valores = (
                        f"{posicion_grupo}°",
                        fila.get("robot") or "—",
                        fila.get("puntos", 0) if fila.get("ha_competido") else "—",
                        fila.get("tiempo_mostrar", "0:00:00") if fila.get("ha_competido") else "—",
                        f'{(fila.get("porcentaje_ataques") or 0):.1f}%' if fila.get("ha_competido") else "—",
                        f'{(fila.get("porcentaje_victorias") or 0):.1f}%' if fila.get("ha_competido") else "—",
                    )
                    if not fase_terminada:
                        tag = "pendiente"
                    elif not fila.get("ha_competido"):
                        tag = "eliminado"
                    else:
                        tag = "clasifica" if fila.get("clasifica") else "eliminado"
                    tabla.insert("", "end", values=valores, tags=(tag,))
        else:
            tabla.insert(
                "", "end",
                values=("TODOS CONTRA TODOS", "", "", "", "", ""),
                tags=("encabezado_grupo_0",)
            )
            for fila in filas:
                valores = (
                    f'{fila.get("posicion", "—")}°',
                    fila.get("robot") or "—",
                    fila.get("puntos", 0) if fila.get("ha_competido") else "—",
                    fila.get("tiempo_mostrar", "0:00:00") if fila.get("ha_competido") else "—",
                    f'{(fila.get("porcentaje_ataques") or 0):.1f}%' if fila.get("ha_competido") else "—",
                    f'{(fila.get("porcentaje_victorias") or 0):.1f}%' if fila.get("ha_competido") else "—",
                )
                if not fase_terminada:
                    tag = "pendiente"
                elif not fila.get("ha_competido"):
                    tag = "eliminado"
                else:
                    tag = "clasifica" if fila.get("clasifica") else "eliminado"
                tabla.insert("", "end", values=valores, tags=(tag,))

    def actualizar_periodicamente():
        if not principal.winfo_exists():
            return
        cargar()
        principal.after(1000, actualizar_periodicamente)

    cargar()
    principal.after(1000, actualizar_periodicamente)
