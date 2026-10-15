/*
  codigo.ino - Firmware inicial de comunicación para MiniSumos RC
  Placa: ESP32-WROOM-32
  Puerto serie: 115200 baudios

  Botones:
    - GPIO 18: ataque del Robot 1 (conectar pulsador entre GPIO18 y GND)
    - GPIO 19: ataque del Robot 2 (conectar pulsador entre GPIO19 y GND)

  Los pines usan INPUT_PULLUP y detección FALLING.
  No se imprime desde las interrupciones; los contadores se actualizan allí
  y se envían por Serial desde loop().

  Protocolo desde Python:
    INICIAR|<id_batalla>|<robot1>|<robot2>
    PAUSAR
    CONTINUAR
    PAUSA_FIN
    FINALIZAR|<ganador>|<criterio>

  Protocolo hacia Python:
    TIEMPO=mm:ss
    ATAQUES1=n
    ATAQUES2=n
*/

#include <Arduino.h>

// -------------------- CONFIGURACIÓN --------------------

constexpr uint8_t PIN_BOTON_R1 = 18;
constexpr uint8_t PIN_BOTON_R2 = 19;
constexpr uint32_t ANTIRREBOTE_US = 180000;  // 180 ms
constexpr uint32_t INTERVALO_ENVIO_MS = 250;

// -------------------- ESTADO DE LA BATALLA --------------------

enum EstadoBatalla {
  ESPERANDO,
  EN_CURSO,
  PAUSADA,
  PAUSA_FIN,
  FINALIZADA
};

EstadoBatalla estado = ESPERANDO;

String idBatalla = "";
String robot1 = "";
String robot2 = "";

volatile uint32_t ataques1 = 0;
volatile uint32_t ataques2 = 0;
volatile uint32_t ultimoPulso1 = 0;
volatile uint32_t ultimoPulso2 = 0;
volatile bool conteoHabilitado = false;

uint64_t tiempoAcumuladoMs = 0;
uint32_t inicioTramoMs = 0;
uint32_t ultimoEnvioMs = 0;

// -------------------- INTERRUPCIONES --------------------

void IRAM_ATTR contarAtaqueR1() {
  const uint32_t ahora = micros();

  if (!conteoHabilitado) return;
  if (static_cast<uint32_t>(ahora - ultimoPulso1) < ANTIRREBOTE_US) return;

  ultimoPulso1 = ahora;
  ataques1++;
}

void IRAM_ATTR contarAtaqueR2() {
  const uint32_t ahora = micros();

  if (!conteoHabilitado) return;
  if (static_cast<uint32_t>(ahora - ultimoPulso2) < ANTIRREBOTE_US) return;

  ultimoPulso2 = ahora;
  ataques2++;
}

// -------------------- TIEMPO --------------------

uint64_t obtenerTiempoMs() {
  if (estado == EN_CURSO) {
    return tiempoAcumuladoMs + static_cast<uint32_t>(millis() - inicioTramoMs);
  }
  return tiempoAcumuladoMs;
}

String tiempoComoTexto(uint64_t tiempoMs) {
  const uint64_t totalSegundos = tiempoMs / 1000ULL;
  const uint64_t minutos = totalSegundos / 60ULL;
  const uint64_t segundos = totalSegundos % 60ULL;

  char texto[24];
  snprintf(texto, sizeof(texto), "%02llu:%02llu",
           static_cast<unsigned long long>(minutos),
           static_cast<unsigned long long>(segundos));
  return String(texto);
}

void congelarTiempo() {
  if (estado == EN_CURSO) {
    tiempoAcumuladoMs += static_cast<uint32_t>(millis() - inicioTramoMs);
  }
  conteoHabilitado = false;
}

void reiniciarContadores() {
  noInterrupts();
  ataques1 = 0;
  ataques2 = 0;
  interrupts();
}

// -------------------- ENVÍO DE DATOS --------------------

void enviarDatos() {
  uint32_t copiaAtaques1;
  uint32_t copiaAtaques2;

  noInterrupts();
  copiaAtaques1 = ataques1;
  copiaAtaques2 = ataques2;
  interrupts();

  Serial.print("TIEMPO=");
  Serial.println(tiempoComoTexto(obtenerTiempoMs()));
  Serial.print("ATAQUES1=");
  Serial.println(copiaAtaques1);
  Serial.print("ATAQUES2=");
  Serial.println(copiaAtaques2);
}

void imprimirInicio() {
  Serial.print("Inicio: BATALLA ");
  Serial.print(idBatalla);
  Serial.print(" - ");
  Serial.print(robot1);
  Serial.print(" vs ");
  Serial.println(robot2);
}

// -------------------- COMANDOS SERIE --------------------

void procesarComando(String linea) {
  linea.trim();
  if (linea.length() == 0) return;

  const int separador1 = linea.indexOf('|');
  String comando = separador1 >= 0 ? linea.substring(0, separador1) : linea;
  comando.trim();
  comando.toUpperCase();

  if (comando == "INICIAR") {
    // Formato: INICIAR|id|robot1|robot2
    if (separador1 < 0) {
      Serial.println("ERROR=Faltan id y nombres de robots");
      return;
    }

    const int separador2 = linea.indexOf('|', separador1 + 1);
    const int separador3 = separador2 >= 0 ? linea.indexOf('|', separador2 + 1) : -1;

    if (separador2 < 0 || separador3 < 0) {
      Serial.println("ERROR=Formato INICIAR incorrecto");
      return;
    }

    idBatalla = linea.substring(separador1 + 1, separador2);
    robot1 = linea.substring(separador2 + 1, separador3);
    robot2 = linea.substring(separador3 + 1);
    idBatalla.trim();
    robot1.trim();
    robot2.trim();

    if (robot1.length() == 0 || robot2.length() == 0) {
      Serial.println("ERROR=Los nombres de los robots no pueden estar vacios");
      return;
    }

    congelarTiempo();
    tiempoAcumuladoMs = 0;
    reiniciarContadores();
    estado = EN_CURSO;
    inicioTramoMs = millis();
    conteoHabilitado = true;
    imprimirInicio();
    enviarDatos();
    ultimoEnvioMs = millis();
    return;
  }

  if (comando == "PAUSAR") {
    if (estado == EN_CURSO) {
      congelarTiempo();
      estado = PAUSADA;
      Serial.println("Pausado");
      enviarDatos();
    } else {
      Serial.println("AVISO=La batalla no estaba en curso");
    }
    return;
  }

  if (comando == "CONTINUAR") {
    if (estado == PAUSADA) {
      inicioTramoMs = millis();
      estado = EN_CURSO;
      conteoHabilitado = true;
      Serial.println("Reanudado");
      enviarDatos();
    } else {
      Serial.println("AVISO=La batalla no esta pausada");
    }
    return;
  }

  if (comando == "PAUSA_FIN") {
    if (estado == EN_CURSO) {
      congelarTiempo();
    }
    if (estado == EN_CURSO || estado == PAUSADA) {
      estado = PAUSA_FIN;
      conteoHabilitado = false;
      Serial.println("Finalizado - A la espera del ganador");
      enviarDatos();
    } else if (estado == PAUSA_FIN) {
      Serial.println("AVISO=Esperando el registro del ganador");
    } else {
      Serial.println("AVISO=No hay una batalla activa para finalizar");
    }
    return;
  }

  if (comando == "FINALIZAR") {
    // Formato: FINALIZAR|ganador|criterio
    const int separador2 = separador1 >= 0 ? linea.indexOf('|', separador1 + 1) : -1;
    if (estado != PAUSA_FIN) {
      Serial.println("AVISO=Use PAUSA_FIN antes de registrar el resultado");
      return;
    }
    if (separador1 < 0 || separador2 < 0) {
      Serial.println("ERROR=Formato FINALIZAR incorrecto");
      return;
    }

    String ganador = linea.substring(separador1 + 1, separador2);
    String criterio = linea.substring(separador2 + 1);
    ganador.trim();
    criterio.trim();

    estado = FINALIZADA;
    conteoHabilitado = false;

    Serial.print("Ganador: ");
    Serial.println(ganador);
    Serial.print("Tiempo final: ");
    Serial.println(tiempoComoTexto(tiempoAcumuladoMs));
    Serial.print("Criterio: ");
    Serial.println(criterio);
    enviarDatos();
    Serial.println("Batalla cerrada");
    return;
  }

  Serial.print("ERROR=Comando desconocido: ");
  Serial.println(comando);
}

// -------------------- SETUP / LOOP --------------------

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BOTON_R1, INPUT_PULLUP);
  pinMode(PIN_BOTON_R2, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(PIN_BOTON_R1), contarAtaqueR1, FALLING);
  attachInterrupt(digitalPinToInterrupt(PIN_BOTON_R2), contarAtaqueR2, FALLING);

  Serial.println("ESP32 lista - MiniSumos RC");
  Serial.println("Boton R1: GPIO18 | Boton R2: GPIO19");
}

void loop() {
  while (Serial.available() > 0) {
    String linea = Serial.readStringUntil('\n');
    procesarComando(linea);
  }

  const uint32_t ahora = millis();
  if (estado != ESPERANDO && estado != FINALIZADA &&
      static_cast<uint32_t>(ahora - ultimoEnvioMs) >= INTERVALO_ENVIO_MS) {
    ultimoEnvioMs = ahora;
    enviarDatos();
  }
}
