#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

int scanTime = 5; // Em segundos
BLEScan* pBLEScan;

class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
      String name = advertisedDevice.getName().c_str();
      String addr = advertisedDevice.getAddress().toString().c_str();
      int rssi = advertisedDevice.getRSSI();
      if (name.length() > 0) {
        Serial.printf("  [BLE] '%s' (%s) RSSI: %d dBm\n", name.c_str(), addr.c_str(), rssi);
      } else {
        Serial.printf("  [BLE] (Sem Nome) (%s) RSSI: %d dBm\n", addr.c_str(), rssi);
      }
    }
};

void setup() {
  Serial.begin(115200);
  Serial.println("\n[BLE Scanner] Inicializando Bluetooth Low Energy...");
  BLEDevice::init("ESP32-Scanner");
  pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(true);
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
  Serial.println("[BLE Scanner] Pronto para escanear!");
}

void loop() {
  Serial.println("\n[BLE] Iniciando varredura de 5 segundos...");
  BLEScanResults foundDevices = pBLEScan->start(scanTime, false);
  Serial.printf("[BLE] Varredura finalizada. %d dispositivos encontrados.\n", foundDevices.getCount());
  pBLEScan->clearResults();
  delay(3000);
}
