import os
import sqlite3
from contextlib import closing
import tkinter as tk
from tkinter import ttk

try:
    from .llaves import obtener_datos_llaves
except ImportError:
    from llaves import obtener_datos_llaves

FONDO = "#FFFFFF"
ROJO_OSCURO = "#8E1B1B"
GRIS = "#64748B"
VERDE = "#DCFCE7"
VERDE_TEXTO = "#166534"
BORDE = "#CBD5E1"
TEXTO = "#1F2937"

def mostrar_eliminatorias(contenedor):
    for widget in contenedor.winfo_children():
        widget.destroy()

    principal = tk.Frame(contenedor, bg=FONDO)
    principal.pack(fill="both", expand=True, padx=24, pady=22)

    tk.Label(
        principal, text="ELIMINATORIAS",
        font=("Arial", 20, "bold"), fg=ROJO_OSCURO, bg=FONDO
    ).pack(anchor="w", pady=(0, 5))
    tk.Label(
        principal, text="Cuadro de rondas y avance de los ganadores.",
        font=("Arial", 11), fg=GRIS, bg=FONDO
    ).pack(anchor="w", pady=(0, 14))

    zona = tk.Frame(principal, bg=FONDO)
    zona.pack(fill="both", expand=True)

    canvas = tk.Canvas(zona, bg=FONDO, highlightthickness=0)
    barra_y = ttk.Scrollbar(zona, orient="vertical", command=canvas.yview)
    barra_x = ttk.Scrollbar(zona, orient="horizontal", command=canvas.xview)
    canvas.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    barra_y.grid(row=0, column=1, sticky="ns")
    barra_x.grid(row=1, column=0, sticky="ew")
    zona.grid_rowconfigure(0, weight=1)
    zona.grid_columnconfigure(0, weight=1)

    estado = tk.Label(principal, text="", font=("Arial", 11), bg=FONDO, fg=GRIS)
    estado.pack(anchor="w", pady=(10, 0))

    ancho_tarjeta = 210
    alto_tarjeta = 78
    margen_x = 28
    margen_y = 34
    separacion_x = 54

    def cargar():
        rondas = obtener_datos_llaves()
        canvas.delete("all")
        if not rondas:
            # En torneos de 3 a 5 participantes la siguiente fase es una final,
            # no un cuadro de llaves. Se muestra aquí para mantener Enfrentamientos
            # dedicado exclusivamente al calendario inicial.
            try:
                with closing(sqlite3.connect(os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "BasesDeDatos", "competencia.db"
                ))) as conexion:
                    cursor = conexion.cursor()
                    cursor.execute("""
                        SELECT e.participante1, p1.robot, p1.nombre,
                               e.participante2, p2.robot, p2.nombre,
                               e.ganador, e.estado
                        FROM enfrentamientos e
                        LEFT JOIN participantes p1 ON p1.id = e.participante1
                        LEFT JOIN participantes p2 ON p2.id = e.participante2
                        WHERE e.etapa = 'Final'
                        ORDER BY e.id
                    """)
                    finales = cursor.fetchall()
            except sqlite3.Error:
                finales = []

            if finales:
                ancho = 330
                alto = 112
                centro_x = 230
                centro_y = 210
                canvas.configure(scrollregion=(0, 0, 520, 420))
                canvas.create_text(
                    centro_x, 70, text="FINAL",
                    fill=ROJO_OSCURO, font=("Arial", 15, "bold")
                )
                for indice, final in enumerate(finales):
                    p1_id, robot1, nombre1, p2_id, robot2, nombre2, ganador, estado_final = final
                    y = centro_y + indice * (alto + 18)
                    canvas.create_rectangle(
                        centro_x - ancho / 2, y - alto / 2,
                        centro_x + ancho / 2, y + alto / 2,
                        fill="#FFFFFF", outline=BORDE, width=2
                    )
                    color1 = VERDE_TEXTO if ganador is not None and ganador == p1_id else TEXTO
                    color2 = VERDE_TEXTO if ganador is not None and ganador == p2_id else TEXTO
                    canvas.create_text(
                        centro_x, y - 25,
                        text=f"{robot1 or 'Por definir'}  •  {nombre1 or ''}",
                        fill=color1, font=("Arial", 11, "bold"), width=ancho - 24
                    )
                    canvas.create_text(
                        centro_x, y + 3,
                        text=f"{robot2 or 'Por definir'}  •  {nombre2 or ''}",
                        fill=color2, font=("Arial", 11, "bold"), width=ancho - 24
                    )
                    canvas.create_text(
                        centro_x, y + 36,
                        text="FINALIZADA" if estado_final == "Completado" else (estado_final or "PENDIENTE").upper(),
                        fill=GRIS, font=("Arial", 9, "bold")
                    )
                estado.config(text="Final del torneo • actualización automática cada 2 s", fg=GRIS)
                return

            canvas.configure(scrollregion=(0, 0, 800, 420))
            canvas.create_text(
                400, 190, text="Todavía no hay eliminatorias generadas.\nCuando finalice la fase inicial, genera las llaves desde Clasificaciones.",
                fill=GRIS, font=("Arial", 14), justify="center"
            )
            estado.config(text="Esperando la generación de la siguiente fase.", fg=GRIS)
            return

        alto_visible = max(canvas.winfo_height(), 420)
        primera_cantidad = max(1, len(rondas[0]["combates"]))
        alto_total = max(alto_visible, margen_y * 2 + primera_cantidad * 125)
        ancho_total = margen_x * 2 + len(rondas) * ancho_tarjeta + max(0, len(rondas) - 1) * separacion_x + ancho_tarjeta + separacion_x

        centros_por_ronda = []
        for ronda in rondas:
            combates = ronda["combates"]
            n = max(1, len(combates))
            centros = [alto_total * (i + 1) / (n + 1) for i in range(n)]
            centros_por_ronda.append(centros)

        def tarjeta(x, centro_y, combate):
            y1 = centro_y - alto_tarjeta / 2
            y2 = centro_y + alto_tarjeta / 2
            canvas.create_rectangle(
                x, y1, x + ancho_tarjeta, y2,
                fill="#FFFFFF", outline=BORDE, width=2
            )
            p1 = combate.get("robot1") or "Por definir"
            p2 = combate.get("robot2") or "Por definir"
            ganador = combate.get("ganador")
            id1 = combate.get("participante1")
            id2 = combate.get("participante2")
            estado_comb = combate.get("estado", "Pendiente")
            c1 = VERDE_TEXTO if ganador is not None and ganador == id1 else TEXTO
            c2 = VERDE_TEXTO if ganador is not None and ganador == id2 else TEXTO
            canvas.create_text(
                x + 9, centro_y - 17, text=p1, anchor="w",
                fill=c1, font=("Arial", 10, "bold"), width=ancho_tarjeta - 18
            )
            canvas.create_text(
                x + 9, centro_y + 3, text=p2, anchor="w",
                fill=c2, font=("Arial", 10, "bold"), width=ancho_tarjeta - 18
            )
            estado_texto = "FINALIZADO" if estado_comb == "Completado" else estado_comb.upper()
            canvas.create_text(
                x + 9, centro_y + 28, text=estado_texto, anchor="w",
                fill=GRIS, font=("Arial", 8)
            )

        for indice, ronda in enumerate(rondas):
            x = margen_x + indice * (ancho_tarjeta + separacion_x)
            canvas.create_text(
                x + ancho_tarjeta / 2, 15, text=ronda["nombre"].upper(),
                fill=ROJO_OSCURO, font=("Arial", 10, "bold")
            )
            for i, combate in enumerate(ronda["combates"]):
                cy = centros_por_ronda[indice][i]
                tarjeta(x, cy, combate)
                if indice > 0:
                    previo = centros_por_ronda[indice - 1]
                    # Conecta cada combate con los dos combates que lo alimentan.
                    indice_previo_1 = min(2 * i, len(previo) - 1)
                    indice_previo_2 = min(2 * i + 1, len(previo) - 1)
                    x_anterior = x - separacion_x
                    for py in (previo[indice_previo_1], previo[indice_previo_2]):
                        canvas.create_line(
                            x_anterior, py, x, cy,
                            fill=BORDE, width=2
                        )

        ultima = rondas[-1]["combates"]
        campeon = next((c for c in ultima if c.get("ganador") is not None and c.get("estado") == "Completado"), None)
        if campeon:
            ganador_id = campeon.get("ganador")
            ganador_robot = campeon.get("robot1") if ganador_id == campeon.get("participante1") else campeon.get("robot2")
            x = margen_x + len(rondas) * (ancho_tarjeta + separacion_x)
            cy = alto_total / 2
            canvas.create_text(
                x + ancho_tarjeta / 2, 15, text="CAMPEÓN",
                fill=ROJO_OSCURO, font=("Arial", 10, "bold")
            )
            canvas.create_rectangle(
                x, cy - alto_tarjeta / 2, x + ancho_tarjeta, cy + alto_tarjeta / 2,
                fill=VERDE, outline="#86EFAC", width=2
            )
            canvas.create_text(
                x + ancho_tarjeta / 2, cy,
                text=ganador_robot or "CAMPEÓN",
                fill=VERDE_TEXTO, font=("Arial", 13, "bold"),
                width=ancho_tarjeta - 18
            )

        canvas.configure(scrollregion=(0, 0, ancho_total, alto_total + 40))
        estado.config(
            text=f"{len(rondas)} rondas • {sum(len(r['combates']) for r in rondas)} enfrentamientos eliminatorios • actualización automática cada 2 s",
            fg=GRIS
        )

    def actualizar_periodicamente():
        if not principal.winfo_exists():
            return
        cargar()
        principal.after(2000, actualizar_periodicamente)

    ttk.Button(principal, text="ACTUALIZAR AHORA", command=cargar).pack(anchor="e", pady=(8, 0))
    cargar()
    principal.after(2000, actualizar_periodicamente)
