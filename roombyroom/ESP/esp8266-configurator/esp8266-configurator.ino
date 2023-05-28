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
char httpResponse[40];
char requestVersionURL[40];  // the URL of the request for the firmware version number
char requestUpdateURL[40];   // the URL of the update firmware binary

///////////////////////////////////////////////////////////////////////////////
// Standard stuff here.

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

  buildSSID();

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  WiFi.softAP(softap_ssid);
  delay(100);

  appSpecificSetup();

  localServer.on("/reset", doFactoryReset);
  localServer.onNotFound(notFound);
  localServer.begin();

  ticker.attach(2, blink);
  completeSetup();
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

///////////////////////////////////////////////////////////////////////////////
// This is the application-specific code.

// Build the SoftAp SSID
void buildSSID() {
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
}

// Complete the setup
void completeSetup() {
  doScan();
}

// Scan networks
void doScan() {
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
    int rlen = 20;
    char* networks = (char*)malloc((n * rlen) * sizeof(char));
      int count = 0;
      for (int i = 0; i < n; ++i) {
        if (strstr(WiFi.SSID(i).c_str(), "RBR-EX-")) {
          strcpy(&networks[i * rlen], WiFi.SSID(i).c_str());
          count = count + 1;
        } else {
          networks[i * rlen] = '\0';
        }
      }
    Serial.printf("%d extender(s) found\n", count);
    delay(10);
    if (count > 0) {
      int* indices = (int*)malloc(count * sizeof(int));
      count = 0;
      for (int i = 0; i < n; i++) {
        if (networks[i * rlen] != '\0') {
          indices[count] = i;
          count = count + 1;
        }
      }
      for (int i = 0; i < count; i++) {
        printf("%s\n", &networks[indices[i] * rlen]);
      }
      free(indices);
      delay(10);
    }
    free(networks);
  }
  localServer.send(200, "text/plain", "OK");
}

// The default page
void onDefault() {
  Serial.println("onAPDefault");
  localServer.send(200, "text/plain", "RBR configurator " + String(softap_ssid));
}

// Set up endpoints for this application and do any other special initialization that's needed.
void appSpecificSetup() {
  localServer.on("/", onDefault);
  localServer.on("/scan", doScan);
}
