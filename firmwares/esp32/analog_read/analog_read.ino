// Leitura de ADC para Sensores e Bateria
void setup() {
  Serial.begin(115200);
  analogReadResolution(12); // 0 a 4095
  analogSetAttenuation(ADC_11db); // Leitura ate ~3.3V
  Serial.println("\n[ADC Monitor] Monitor de Sensores / Bateria Iniciado!");
  Serial.println("Lendo GPIO34, GPIO35 e GPIO36 (VP)...");
}

void loop() {
  int raw34 = analogRead(34);
  int raw35 = analogRead(35);
  int raw36 = analogRead(36);

  float v34 = (raw34 / 4095.0f) * 3.3f;
  float v35 = (raw35 / 4095.0f) * 3.3f;
  float v36 = (raw36 / 4095.0f) * 3.3f;

  Serial.printf("[ADC] GPIO34: %4d (%.2fV) | GPIO35: %4d (%.2fV) | GPIO36: %4d (%.2fV)\n",
                raw34, v34, raw35, v35, raw36, v36);
  delay(1000);
}
