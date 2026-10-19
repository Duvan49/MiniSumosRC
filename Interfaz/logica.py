"""Lógica local de las batallas MiniSumos RC, sin conexión con ESP32."""

import time


def _a_segundos(valor):
    """Convierte M:SS:CC o HH:MM:SS a segundos acumulados."""
    try:
        partes = str(valor or "0:00:00").split(":")
        if len(partes) != 3:
            return 0.0
        primero, segundo, tercero = (float(p) for p in partes)
        # Formato de la interfaz: minutos:segundos:centésimas.
        return max(0.0, primero * 60 + segundo + tercero / 100)
    except (TypeError, ValueError):
        return 0.0


class RelojBatalla:
    """Cronómetro acumulativo con inicio, pausa, reanudación y finalización."""

    def __init__(self, tiempo_inicial="0:00:00"):
        self._acumulado = _a_segundos(tiempo_inicial)
        self._inicio_tramo = None
        self.estado = "Pendiente"

    def reiniciar(self):
        self._acumulado = 0.0
        self._inicio_tramo = None
        self.estado = "Pendiente"

    def iniciar(self):
        if self.estado not in ("Pendiente",):
            return
        self._inicio_tramo = time.monotonic()
        self.estado = "En curso"

    def pausar(self):
        if self.estado == "En curso" and self._inicio_tramo is not None:
            self._acumulado += time.monotonic() - self._inicio_tramo
            self._inicio_tramo = None
            self.estado = "Pausada"

    def continuar(self):
        if self.estado == "Pausada":
            self._inicio_tramo = time.monotonic()
            self.estado = "En curso"

    def finalizar(self):
        if self.estado == "En curso" and self._inicio_tramo is not None:
            self._acumulado += time.monotonic() - self._inicio_tramo
        self._inicio_tramo = None
        self.estado = "Finalizada"

    def segundos(self):
        total = self._acumulado
        if self.estado == "En curso" and self._inicio_tramo is not None:
            total += time.monotonic() - self._inicio_tramo
        return max(0.0, total)

    def obtener_tiempo(self):
        centesimas_total = int(self.segundos() * 100)
        minutos, resto = divmod(centesimas_total, 6000)
        segundos, centesimas = divmod(resto, 100)
        return f"{minutos}:{segundos:02d}:{centesimas:02d}"
