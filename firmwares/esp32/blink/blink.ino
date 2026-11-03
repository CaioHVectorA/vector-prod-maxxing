// Blink com Log Serial para ESP32
#define LED_PIN 2

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("\n=================================");
  Serial.println("  ESP32 Flash Suite: Blink OK!");
  Serial.println("=================================");
}

void loop() {
  digitalWrite(LED_PIN, HIGH);
  Serial.println("[ESP32] LED ON");
  delay(500);
  digitalWrite(LED_PIN, LOW);
  Serial.println("[ESP32] LED OFF");
  delay(500);
}
