/*
  ESP32 System Telemetry & Benchmark
  Lê e exibe todas as informações de hardware do chip ESP32 pela Serial.
*/

#include <Arduino.h>
#include <WiFi.h>
#include <esp_system.h>
#include <esp_spi_flash.h>

void setup() {
  Serial.begin(115200);
  delay(1000);
}

void loop() {
  Serial.println("\n=======================================================");
  Serial.println("           ESP32 HARDWARE TELEMETRY REPORT             ");
  Serial.println("=======================================================");

  // Chip Info
  esp_chip_info_t chip_info;
  esp_chip_info(&chip_info);

  Serial.printf("Modelo do Chip      : %s (Rev %d)\n", ESP.getChipModel(), ESP.getChipRevision());
  Serial.printf("Nucleos de CPU      : %d cores @ %d MHz\n", chip_info.cores, ESP.getCpuFreqMHz());
  Serial.printf("Features            : %s%s%s\n",
                (chip_info.features & CHIP_FEATURE_WIFI_BGN) ? "WiFi 802.11bgn " : "",
                (chip_info.features & CHIP_FEATURE_BLE) ? "BLE " : "",
                (chip_info.features & CHIP_FEATURE_BT) ? "Classic BT " : "");

  // MAC Address
  Serial.printf("Endereco MAC (WiFi) : %s\n", WiFi.macAddress().c_str());

  // Memória Flash
  Serial.printf("Flash Size          : %u MB (Speed: %u MHz)\n", 
                ESP.getFlashChipSize() / (1024 * 1024), 
                ESP.getFlashChipSpeed() / 1000000);
  Serial.printf("Flash Mode          : %d\n", ESP.getFlashChipMode());

  // Memória RAM (Heap)
  Serial.printf("Heap Total / Livre  : %u KB / %u KB (Min: %u KB)\n",
                ESP.getHeapSize() / 1024,
                ESP.getFreeHeap() / 1024,
                ESP.getMinFreeHeap() / 1024);
  Serial.printf("Maior Bloco Alocavel: %u KB\n", ESP.getMaxAllocHeap() / 1024);

  // Uptime
  uint32_t sec = millis() / 1000;
  Serial.printf("Uptime do Sistema   : %02d:%02d:%02d\n", sec / 3600, (sec % 3600) / 60, sec % 60);

  // Sensor interno de temperatura (se disponível)
  #ifdef SOC_TEMP_SENSOR_SUPPORTED
  Serial.printf("Temperatura Interna : %.1f °C\n", temperatureRead());
  #endif

  Serial.println("=======================================================");
  delay(3000);
}
