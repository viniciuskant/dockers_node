/*
 * ESP32/ESP8266 - Simulador de Sensores via UART
 * 
 * Funcionamento:
 * - Aguarda o comando "readSensors" pela Serial
 * - Quando recebe "readSensors", envia dados de todos os sensores via JSON
 * - Ignora qualquer outro comando
 */

#include <Arduino.h>
#include <ArduinoJson.h>

// ================= CONFIGURAÇÕES =================
#define BAUD_RATE 115200
#define COMANDO_VALIDO "readSensors"   // Comando esperado via UART
#define TAXA_ERRO 0.0                  // Probabilidade de falha na leitura (0.0 a 1.0)

// Lista de sensores disponíveis
const char* SENSORES[] = {
  "temperatura", "umidade", "pressao",
  "co2", "co", "so2", "no2",
  "ozonio", "pm25"
};
const int NUM_SENSORES = sizeof(SENSORES) / sizeof(SENSORES[0]);

// Configurações de cada sensor (limites e precisão)
struct SensorConfig {
  float min;
  float max;
  int decimais;
};

const SensorConfig SENSOR_CONFIGS[] = {
  {-10.0, 45.0, 1},   // temperatura
  {0.0,   100.0, 1},  // umidade
  {950.0, 1050.0, 1}, // pressao
  {300.0, 2000.0, 0}, // co2
  {0.0,   50.0,  1},  // co
  {0.0,   20.0,  1},  // so2
  {0.0,   30.0,  1},  // no2
  {0.0,   10.0,  2},  // ozonio
  {0.0,   500.0, 0}   // pm25
};

// ================= GERADOR DE DADOS =================
/**
 * Gera um valor aleatório para o sensor dado seu índice.
 * Retorna true e preenche 'valor' se sucesso, false se falha (simula erro).
 */
bool gerarValorSensor(int idx, float &valor) {
  // Simula falha com base na TAXA_ERRO
  if (random(100) / 100.0 < TAXA_ERRO) {
    return false;
  }

  const SensorConfig &cfg = SENSOR_CONFIGS[idx];
  valor = random(cfg.min * 100, cfg.max * 100) / 100.0;
  
  // Arredondar para o número de decimais especificado
  float multiplicador = pow(10, cfg.decimais);
  valor = round(valor * multiplicador) / multiplicador;
  return true;
}

/**
 * Constrói uma String JSON com os dados do sensor
 */
String construirPayload(const char* sensor, float valor, bool valido) {
  StaticJsonDocument<256> doc;
  doc["type_msg"] = "data";
  doc["sensor"] = sensor;

  JsonObject message = doc.createNestedObject("message");
  if (valido) {
    message["valor"] = valor;
  } else {
    message["mensagem_erro"] = "Falha na leitura do sensor";
  }

  // Timestamp em millis desde o boot
  message["timestamp"] = String(millis());

  String output;
  serializeJson(doc, output);
  return output;
}

// ================= INTERFACE UART =================
/**
 * Envia dados de todos os sensores pela UART
 */
void enviarDadosTodosSensores() {
  for (int i = 0; i < NUM_SENSORES; i++) {
    float valor;
    bool ok = gerarValorSensor(i, valor);
    String payload = construirPayload(SENSORES[i], valor, ok);
    Serial.println(payload);  // Envia linha JSON pela UART
    delay(10); // Pequena pausa para evitar overrun no receptor
  }
}

/**
 * Processa o comando recebido pela UART.
 * Se for "readSensors", envia todos os dados.
 */
void processarComando(const String &comando) {
  if (comando == COMANDO_VALIDO) {
    enviarDadosTodosSensores();
  }
  // Ignora qualquer outro comando silenciosamente
}

// ================= SETUP E LOOP =================
void setup() {
  Serial.begin(BAUD_RATE);
  
  // Inicializa gerador aleatório
  randomSeed(analogRead(0));
  
  // Para ESP32, use isso se analogRead(0) não funcionar:
  // randomSeed(esp_random());
  
  // Aguarda conexão serial (útil para alguns terminais)
  while (!Serial) {
    delay(10);
  }
  
  Serial.println("ESP Sensor Simulator pronto.");
  Serial.println("Envie 'readSensors' para obter os dados dos sensores.");
}

void loop() {
  static String buffer = "";
  
  while (Serial.available()) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {  // Aceita tanto \n quanto \r como terminador
      if (buffer.length() > 0) {
        processarComando(buffer);
        buffer = "";
      }
    } else {
      buffer += c;
    }
  }
  
  delay(10); // Pequena pausa para evitar alto consumo de CPU
}