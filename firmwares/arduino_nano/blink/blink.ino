// Blink com Log Serial para Arduino Nano / Uno
#define LED_PIN 13

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("\n[ARDUINO] Blink Pronto!");
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  Serial.println("[ARDUINO] LED 13 LIGADO");
  delay(500);
  digitalWrite(LED_PIN, LOW);
  Serial.println("[ARDUINO] LED 13 DESLIGADO");
  delay(500);
}
