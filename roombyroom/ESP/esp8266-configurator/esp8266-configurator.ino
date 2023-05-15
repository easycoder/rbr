// RBR Configurator

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 1
#define BAUDRATE 115200
#define UPDATE_CHECK_INTERVAL 3600

// Constants
const IPAddress localIP(192,168,23,1);
const IPAddress subnet(255,255,255,0);

Ticker ticker;
ESP8266WebServer localServer(80);
DynamicJsonDocument config(256);

uint8_t ledPin = 2;
bool checkForUpdate = false;
char name[40];
char softap_ssid[40];
char host_ssid[40];
char host_password[20];
char host_ipaddr[20];
char host_gateway[20];
char host_server[20];
char requestVersionURL[40];
char requestUpdateURL[40];
char httpResponse[40];

// Check if an update is available
void updateCheck() {
  checkForUpdate = true;
}

void notFound(){
  localServer.send(404, "text/plain", "Not found");
}

// Write text to a LittleFS file
void writeTextToFile(const char* filename, const char* text) {
  auto file = LittleFS.open(filename, "w");
  file.print(text);
  delay(10);
  file.close();
}

// Read a LittleFS file into text
const char* readFileToText(const char* filename) {
  auto file = LittleFS.open(filename, "r");
  if (!file) {
    Serial.println("file open failed");
    return "";
  }
  size_t filesize = file.size();
  char* text = new char[filesize + 1];
  String data = file.readString();
  file.close();
  strcpy(text, data.c_str());
  return text;
}

void blink()
{
  digitalWrite(ledPin, LOW);
  delay(100);
  digitalWrite(ledPin, HIGH);
  delay(100);
  digitalWrite(ledPin, LOW);
  delay(100);
  digitalWrite(ledPin, HIGH);
}

// Restart the system
void restart() {
  delay(10000);
  ESP.reset();
}

// Reset the system
void doFactoryReset() {
  Serial.print("Factory Reset");
  localServer.send(200, "text/plain", "Factory Reset");
  writeTextToFile("/config", "");
  restart();
}

// Scan networks
void doScan() {
  Serial.print("Scan");
  Serial.println("Scan start");
  // WiFi.scanNetworks will return the number of networks found
  int n = WiFi.scanNetworks();
  Serial.println("Scan done");
  
  if (n == 0)
  {
    Serial.println("no networks found");
  }
  else
  {
    Serial.print(n);
    Serial.println(" networks found");
    for (int i = 0; i < n; ++i)
    {
      // Print SSID and RSSI for each network found
      Serial.print(i + 1);
      Serial.print(": ");
      Serial.print(WiFi.SSID(i));
      Serial.print(" (");
      Serial.print(WiFi.RSSI(i));
      Serial.print(")");
      Serial.println((WiFi.encryptionType(i) == ENC_TYPE_NONE)?" ":"*");
      delay(10);
    }
  }
  Serial.println("");
  localServer.send(200, "text/plain", "OK");
}

// The default page
void onDefault() {
  Serial.println("onAPDefault");
  localServer.send(200, "text/plain", "RBR configurator " + String(softap_ssid));
}

// Perform a GET
void httpGET(char* serverName) {
  WiFiClient client;
  HTTPClient http;
    
  http.begin(client, serverName);

  String payload = "";
  
  // Send HTTP GET request
  int httpResponseCode = http.GET();
  
  if (httpResponseCode >= 200 && httpResponseCode < 400) {
    payload = http.getString();
  }
  else {
    Serial.printf("Error code: %d\n", httpResponseCode);
    restart();
  }
  // Free resources
  http.end();

  payload.trim();
  strcpy(httpResponse, payload.c_str());
}

///////////////////////////////////////////////////////////////////////////////
// Start here
void setup() {
  Serial.begin(BAUDRATE);
  delay(500);
  Serial.printf("\nFlash size: %d\n",ESP.getFlashChipRealSize());
  Serial.printf("Version: %d\n",CURRENT_VERSION);

  if (!LittleFS.begin()){
    LittleFS.format();
    restart();
  }

//  writeTextToFile("/config", "");

  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, HIGH);

  // Build the SoftAp SSID
  String mac = WiFi.macAddress();
  Serial.println("MAC: " + mac);
  String ssid = "RBR-CF-XXXXXX";
  ssid[7] = mac[9];
  ssid[8] = mac[10];
  ssid[9] = mac[12];
  ssid[10] = mac[13];
  ssid[11] = mac[15];
  ssid[12] = mac[16];
  strcpy(softap_ssid, ssid.c_str());
  Serial.printf("SoftAP SSID: %s\n", softap_ssid);

  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(localIP, localIP, subnet);
  WiFi.softAP(softap_ssid);
  delay(100);

  localServer.on("/", onDefault);
  localServer.on("/reset", doFactoryReset);
  localServer.on("/scan", doScan);
  localServer.onNotFound(notFound);
  localServer.begin();

  ticker.attach(2, blink);
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop() {
  localServer.handleClient();

  if (checkForUpdate && requestVersionURL) {
    checkForUpdate = false;
    Serial.printf("Check for update at %s\n", requestVersionURL);
    httpGET(requestVersionURL);
    int newVersion = atoi(httpResponse);
    Serial.printf("Version %d is available\n", newVersion);
    if (newVersion > CURRENT_VERSION) {
      WiFiClient client;
      Serial.printf("Installing version %d from %s\n", newVersion, requestUpdateURL);
      t_httpUpdate_return ret = ESPhttpUpdate.update(client, requestUpdateURL);
      switch (ret) {
        case HTTP_UPDATE_FAILED:
           Serial.println("Update failed");
           break;
        case HTTP_UPDATE_NO_UPDATES:
           Serial.println("No update took place");
           break;
      }
    } else {
      Serial.println("Firmware is up to date");
    }
  }
}
