"""Comunicación serie con el ESP32 para MiniSumos RC.

Protocolo esperado desde el ESP32, una variable por línea:
    TIEMPO=00:25
    ATAQUES1=3
    ATAQUES2=2

También admite mensajes combinados separados por coma o punto y coma.
"""

import threading
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


class ComunicacionESP32:
    def __init__(self, baudrate=115200, timeout=0.2):
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.puerto = None
        self.conectado = False
        self._hilo = None
        self._detener = threading.Event()
        self._lock = threading.Lock()
        self._tiempo = "00:00"
        self._ataques1 = 0
        self._ataques2 = 0

    def listar_puertos(self):
        if list_ports is None:
            return []
        return [p.device for p in list_ports.comports()]

    def conectar(self, puerto="COM4"):
        """Conecta al puerto elegido. Devuelve True si se abre correctamente."""
        if serial is None:
            self.conectado = False
            raise RuntimeError(
                "No está instalado pyserial. Instálalo con: pip install pyserial"
            )

        if self.serial is not None:
            try:
                if self.serial.is_open and self.puerto == puerto:
                    self.conectado = True
                    return True
            except Exception:
                pass
            self.desconectar()

        try:
            conexion = serial.Serial(
                port=puerto,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=1
            )
            # Muchos ESP32 se reinician al abrir el puerto serie.
            time.sleep(1.5)
            try:
                conexion.reset_input_buffer()
            except Exception:
                pass
            self.serial = conexion
            self.puerto = puerto
            self.conectado = True
            self._detener.clear()
            self._hilo = threading.Thread(
                target=self._leer_serie, daemon=True, name="LectorESP32"
            )
            self._hilo.start()
            return True
        except Exception:
            self.serial = None
            self.puerto = None
            self.conectado = False
            raise

    def desconectar(self):
        self._detener.set()
        conexion = self.serial
        self.serial = None
        self.conectado = False
        self.puerto = None
        if conexion is not None:
            try:
                if conexion.is_open:
                    conexion.close()
            except Exception:
                pass

    def _leer_serie(self):
        while not self._detener.is_set():
            conexion = self.serial
            if conexion is None:
                break
            try:
                if not conexion.is_open:
                    break
                linea = conexion.readline().decode("utf-8", errors="ignore").strip()
                if linea:
                    self._procesar_linea(linea)
            except Exception:
                self.conectado = False
                break
        self.conectado = bool(
            self.serial is not None and getattr(self.serial, "is_open", False)
        )

    def _procesar_linea(self, linea):
        # El firmware puede emitir un valor por línea o varios en una misma línea.
        partes = linea.replace(";", ",").split(",")
        with self._lock:
            for parte in partes:
                if "=" not in parte:
                    continue
                clave, valor = parte.split("=", 1)
                clave = clave.strip().upper()
                valor = valor.strip()
                if clave in ("TIEMPO", "TIME"):
                    self._tiempo = valor
                elif clave in ("ATAQUES1", "ATAQUE1", "ATTACKS1", "R1"):
                    try:
                        self._ataques1 = int(float(valor))
                    except ValueError:
                        pass
                elif clave in ("ATAQUES2", "ATAQUE2", "ATTACKS2", "R2"):
                    try:
                        self._ataques2 = int(float(valor))
                    except ValueError:
                        pass

    def obtener_datos(self):
        with self._lock:
            return self._tiempo, self._ataques1, self._ataques2

    def reiniciar_datos(self):
        with self._lock:
            self._tiempo = "00:00"
            self._ataques1 = 0
            self._ataques2 = 0

    def enviar(self, comando):
        conexion = self.serial
        if not self.conectado or conexion is None:
            return False
        try:
            if not conexion.is_open:
                self.conectado = False
                return False
            mensaje = str(comando).strip() + "\n"
            conexion.write(mensaje.encode("utf-8"))
            conexion.flush()
            return True
        except Exception:
            self.conectado = False
            return False


esp32 = ComunicacionESP32()
