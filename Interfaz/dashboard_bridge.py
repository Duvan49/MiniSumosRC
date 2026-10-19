"""Puente no bloqueante entre la interfaz Tkinter y el dashboard web local.

Tkinter sigue siendo la fuente de verdad para batalla/tiempo/estado.
El contador de ataques se conserva en el servidor del dashboard y se consulta
periódicamente para incorporarlo al resultado oficial de Python.
"""
import json
import os
import threading
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

DASHBOARD_URL = os.environ.get("MINISUMOS_DASHBOARD_URL", "http://127.0.0.1:8000").rstrip("/")


class DashboardBridge:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = None
        self._elapsed = 0.0
        self._event_id = 0
        self._event = {"ui_action": "", "ui_action_id": 0}
        self._attacks = (0, 0)
        self._running = True
        self._thread = threading.Thread(target=self._worker, name="MiniSumosDashboardBridge", daemon=True)
        self._thread.start()

    def set_state(self, payload):
        """Actualiza datos de batalla sin bloquear el hilo de Tkinter."""
        with self._lock:
            if self._state is None:
                self._state = {}
            self._state.update(payload)

    def set_time(self, elapsed_seconds):
        try:
            value = max(0.0, float(elapsed_seconds))
        except (TypeError, ValueError):
            value = 0.0
        with self._lock:
            self._elapsed = value

    def trigger(self, action, **payload):
        """Publica una acción visual una sola vez, identificada por secuencia."""
        with self._lock:
            self._event_id += 1
            self._event = {
                "ui_action": str(action),
                "ui_action_id": self._event_id,
                **payload,
            }

    def attacks(self):
        with self._lock:
            return self._attacks

    def _request(self, path, method="GET", payload=None, timeout=0.12):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"} if data is not None else {}
        request = Request(DASHBOARD_URL + path, data=data, headers=headers, method=method)
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
        return json.loads(raw.decode("utf-8")) if raw else {}

    def _worker(self):
        last_time = 0.0
        last_sync = 0.0
        retry_after = 0.0
        while self._running:
            now = time.monotonic()
            with self._lock:
                state = dict(self._state) if self._state is not None else None
                elapsed = self._elapsed
                event = dict(self._event)
            if state is not None and now >= retry_after:
                try:
                    if now - last_time >= 0.08:
                        self._request("/api/python/time", "POST", {"elapsed_seconds": elapsed}, timeout=0.10)
                        last_time = now
                    if now - last_sync >= 0.25:
                        payload = {**state, **event}
                        payload.pop("elapsed_seconds", None)
                        self._request("/api/python/sync", "POST", payload, timeout=0.15)
                        latest = self._request("/api/state", timeout=0.15)
                        try:
                            a1 = max(0, int(latest.get("attacks1", 0)))
                            a2 = max(0, int(latest.get("attacks2", 0)))
                            with self._lock:
                                self._attacks = (a1, a2)
                        except (TypeError, ValueError):
                            pass
                        last_sync = now
                except (URLError, HTTPError, TimeoutError, OSError, ValueError):
                    # El dashboard puede no estar abierto aún. No se bloquea Tkinter;
                    # se reintenta en un segundo sin llenar una cola de peticiones.
                    retry_after = time.monotonic() + 1.0
            time.sleep(0.02)


dashboard_bridge = DashboardBridge()
