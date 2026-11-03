#include <WiFi.h>
#include <WebServer.h>

#define LED_PIN 2

WebServer server(80);
bool ledState = false;

void handleRoot() {
  String html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>ESP32 Bancada</title>";
  html += "<style>body{font-family:sans-serif;text-align:center;background:#1e1e24;color:#eee;padding-top:40px;}";
  html += ".btn{display:inline-block;padding:12px 24px;font-size:18px;color:#fff;background:#0078d4;border-radius:8px;text-decoration:none;margin-top:20px;}";
  html += ".card{background:#2b2b36;padding:20px;margin:auto;max-width:360px;border-radius:12px;box-shadow:0 4px 10px rgba(0,0,0,0.3);}</style></head><body>";
  html += "<div class='card'><h2>ESP32 Bancada Web</h2><p>Ponto de Acesso OK!</p>";
  html += "<p>Estado do LED: <b>" + String(ledState ? "LIGADO" : "DESLIGADO") + "</b></p>";
  html += "<a href='/toggle' class='btn'>Alternar LED</a></div></body></html>";
  server.send(200, "text/html", html);
}

void handleToggle() {
  ledState = !ledState;
  digitalWrite(LED_PIN, ledState ? HIGH : LOW);
  server.sendHeader("Location", "/");
  server.send(303);
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.begin(115200);

  Serial.println("\n[Wi-Fi AP] Criando Ponto de Acesso 'ESP32-BANCADA'...");
  WiFi.softAP("ESP32-BANCADA");
  IPAddress IP = WiFi.softAPIP();

  server.on("/", handleRoot);
  server.on("/toggle", handleToggle);
  server.begin();

  Serial.printf("[Wi-Fi AP] Pronto! Conecte na rede 'ESP32-BANCADA' e acesse http://%s\n", IP.toString().c_str());
}

void loop() {
  server.handleClient();
}
