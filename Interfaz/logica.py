"""Lógica local de las batallas MiniSumos RC, sin conexión con ESP32."""

import time


def _a_segundos(valor):
    """Convierte M:SS:CC a segundos acumulados."""
    try:
        partes = str(valor or "0:00:00").split(":")
        if len(partes) != 3:
            return 0.0
        minutos, segundos, centesimas = (float(p) for p in partes)
        return max(0.0, minutos * 60 + segundos + centesimas / 100)
    except (TypeError, ValueError):
        return 0.0


def _formatear(segundos):
    centesimas_total = int(max(0.0, segundos) * 100)
    minutos, resto = divmod(centesimas_total, 6000)
    segundos, centesimas = divmod(resto, 100)
    return f"{minutos}:{segundos:02d}:{centesimas:02d}"


class RelojBatalla:
    """Cronómetro acumulativo recuperable al salir y volver a la pestaña."""

    def __init__(self, tiempo_inicial="0:00:00", inicio_epoch=None):
        self._acumulado = _a_segundos(tiempo_inicial)
        self._inicio_tramo = float(inicio_epoch) if inicio_epoch else None
        self.estado = "En curso" if self._inicio_tramo is not None else "Pendiente"

    def reiniciar(self):
        self._acumulado = 0.0
        self._inicio_tramo = None
        self.estado = "Pendiente"

    def iniciar(self):
        if self.estado == "Pendiente":
            self._inicio_tramo = time.time()
            self.estado = "En curso"

    def pausar(self):
        if self.estado == "En curso" and self._inicio_tramo is not None:
            self._acumulado += max(0.0, time.time() - self._inicio_tramo)
            self._inicio_tramo = None
            self.estado = "Pausada"

    def continuar(self):
        if self.estado == "Pausada":
            self._inicio_tramo = time.time()
            self.estado = "En curso"

    def finalizar(self, limite_segundos=None):
        if self.estado == "En curso" and self._inicio_tramo is not None:
            self._acumulado += max(0.0, time.time() - self._inicio_tramo)
        if limite_segundos is not None:
            self._acumulado = min(self._acumulado, float(limite_segundos))
        self._inicio_tramo = None
        self.estado = "Finalizada"

    def segundos(self):
        total = self._acumulado
        if self.estado == "En curso" and self._inicio_tramo is not None:
            total += max(0.0, time.time() - self._inicio_tramo)
        return total

    def obtener_tiempo(self):
        return _formatear(self.segundos())

    def obtener_tiempo_base(self):
        """Tiempo acumulado guardado antes del tramo que sigue corriendo."""
        return _formatear(self._acumulado)

    def inicio_epoch(self):
        """Marca temporal persistible del tramo activo, o None si está detenido."""
        return self._inicio_tramo
