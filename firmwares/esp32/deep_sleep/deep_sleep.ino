/*
  ESP32 Deep Sleep Utility
  Demonstra economia de energia:
  - Acorda a cada 10 segundos OU quando o botão BOOT (GPIO 0) for pressionado.
  - Exibe motivo do wake-up e contagem de boots na memória RTC.
*/

#include <Arduino.h>

RTC_DATA_ATTR int bootCount = 0;

void print_wakeup_reason() {
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();

  switch(wakeup_reason) {
    case ESP_SLEEP_WAKEUP_EXT0 : Serial.println("Acordou por: Botao externo (GPIO0 / BOOT)"); break;
    case ESP_SLEEP_WAKEUP_TIMER : Serial.println("Acordou por: Timer (10s)"); break;
    default : Serial.printf("Acordou por: Inicializacao / Outro (%d)\n", wakeup_reason); break;
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);

  bootCount++;
  Serial.println("\n====================================");
  Serial.printf("ESP32 Deep Sleep - Ciclo de Boot #%d\n", bootCount);
  Serial.println("====================================");

  print_wakeup_reason();

  // Pisca o LED indicador (GPIO 2)
  pinMode(2, OUTPUT);
  for(int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(100);
    digitalWrite(2, LOW);
    delay(100);
  }

  Serial.println("Entrando em Deep Sleep por 10 segundos...");
  Serial.println("(Dica: Pressione o botao BOOT no ESP32 para acordar imediatamente)\n");
  Serial.flush();

  // Configura wakeup por timer (10 segundos em microssegundos)
  esp_sleep_enable_timer_wakeup(10 * 1000000ULL);

  // Configura wakeup pelo botão BOOT (GPIO 0 nível baixo)
  esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0);

  // Dorme
  esp_deep_sleep_start();
}

void loop() {
  // Nunca alcancado no modo Deep Sleep
}
