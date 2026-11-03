/*
  ESP32 PWM / LEDC Fade Utility
  Demonstração do gerador PWM de hardware do ESP32 (LEDC):
  - Efeito breathing / fade no LED interno (GPIO 2)
  - Medição de tempo e ciclo de trabalho (Duty Cycle)
*/

#include <Arduino.h>

const int LED_PIN = 2;
const int PWM_CHANNEL = 0;
const int PWM_FREQ = 5000;      // 5 kHz
const int PWM_RESOLUTION = 8;    // 8 bits (0 - 255)

void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println("\n[PWM LEDC] Configurando canal PWM 0 na GPIO 2 @ 5kHz (8-bits)...");
  ledcSetup(PWM_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(LED_PIN, PWM_CHANNEL);
  Serial.println("[PWM LEDC] Pronto! Iniciando efeito breathing.");
}

void loop() {
  // Aumenta o brilho
  for (int duty = 0; duty <= 255; duty += 5) {
    ledcWrite(PWM_CHANNEL, duty);
    delay(15);
  }

  // Diminui o brilho
  for (int duty = 255; duty >= 0; duty -= 5) {
    ledcWrite(PWM_CHANNEL, duty);
    delay(15);
  }
}
