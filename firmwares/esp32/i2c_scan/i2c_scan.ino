#include <Wire.h>

void setup() {
  Wire.begin(21, 22);
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[I2C Scanner] Inicializado nos pinos SDA=21, SCL=22");
}

void loop() {
  byte error, address;
  int nDevices = 0;

  Serial.println("\n[I2C] Escaneando barramento...");
  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0) {
      Serial.printf("  -> Dispositivo encontrado no endereco 0x%02X!\n", address);
      nDevices++;
    } else if (error == 4) {
      Serial.printf("  -> Erro desconhecido no endereco 0x%02X\n", address);
    }
  }

  if (nDevices == 0) {
    Serial.println("Nenhum dispositivo I2C encontrado.");
  } else {
    Serial.printf("Concluido! %d dispositivos I2C detectados.\n", nDevices);
  }

  delay(4000);
}
