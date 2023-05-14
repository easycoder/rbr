// RBR R1 relay

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 2
#define BAUDRATE 115200
#define UPDATE_CHECK_INTERVAL 3600

// Constants
const IPAddress localIP(192,168,23,1);
const IPAddress subnet(255,255,255,0);

Ticker ticker;
ESP8266WebServer localServer(80);
DynamicJsonDocument config(256);

uint8_t relayPin = 0;
uint8_t ledPin = 2;
bool relayPinStatus = LOW;
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

// The default page when configured
void onDefault() {
  Serial.println("onDefault");
  char info[80];
  char buf[8];
  sprintf(buf, "%d", CURRENT_VERSION);
  strcpy(info, "RBR R1 relay V");
  strcat(info, buf);
  strcat(info, " ");
  strcat(info, name);
  strcat(info, " (");
  strcat(info, host_ssid);
  strcat(info, "/");
  strcat(info, host_ipaddr);
  strcat(info, ") RSSI: ");
  sprintf(buf, "%d", WiFi.RSSI());
  strcat(info, buf);
  Serial.println(info);
  localServer.send(200, "text/plain", info);
}

// Check if an update is available
void updateCheck() {
  checkForUpdate = true;
}

void ledOn() {
  if (ledPin != relayPin) {
    digitalWrite(ledPin, LOW);
  }
}

void ledOff() {
  if (ledPin != relayPin) {
    digitalWrite(ledPin, HIGH);
  }
}

void relayOn() {
  relayPinStatus = HIGH;
  localServer.send(200, "text/plain", "Relay ON");
}

void relayOff() {
  relayPinStatus = LOW;
  localServer.send(200, "text/plain", "Relay Off");
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
  ledOn();
  delay(100);
  ledOff();
  delay(100);
  ledOn();
  delay(100);
  ledOff();
}

// Restart the system
void restart() {
  delay(10000);
  ESP.reset();
}

// Reset the system
void factoryReset() {
  Serial.print("Factory Reset");
  localServer.send(200, "text/plain", "Factory Reset");
  writeTextToFile("/config", "");
  restart();
}

// Perform a GET
void httpGET(char* serverName, char* response) {
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
  strcpy(response, payload.c_str());
}

// Connect to the controller network and accept relay commands
void connectToHost() {
  Serial.printf("name: %s\n", name);
  Serial.printf("host_ssid: %s\n", host_ssid);
  Serial.printf("host_password: %s\n", host_password);
  Serial.printf("host_ipaddr: %s\n", host_ipaddr);
  Serial.printf("host_gateway: %s\n", host_gateway);
  Serial.printf("host_server: %s\n", host_server);

  // Check IP addresses are well-formed

  IPAddress ipaddr;
  IPAddress gateway;
  IPAddress server;

  if (!ipaddr.fromString(host_ipaddr)) {
    Serial.println("UnParsable IP '" + String(host_ipaddr) + "'");
    factoryReset();
  }

  if (!gateway.fromString(host_gateway)) {
    Serial.println("UnParsable IP '" + String(host_gateway) + "'");
    factoryReset();
  }

  if (!server.fromString(host_server)) {
    Serial.println("UnParsable IP '" + String(host_server) + "'");
    factoryReset();
  }

  // Connect to the controller's wifi network
  WiFi.mode(WIFI_STA);
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA failed to configure");
  }
  WiFi.begin(host_ssid, host_password);

  // Check we are connected to wifi network
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.printf("\nConnected to %s as %s\n", host_ssid, WiFi.localIP().toString().c_str());
  delay(100);

  localServer.on("/", onDefault);
  localServer.on("/on", relayOn);
  localServer.on("/off", relayOff);
  localServer.on("/reset", factoryReset);
  localServer.onNotFound(notFound);

  localServer.begin();
  localServer.send(200, "text/plain", "Connected");

  strcat(requestVersionURL, "http://");
  strcat(requestVersionURL, host_server);
  strcat(requestVersionURL, "/relay/version");
  strcat(requestUpdateURL, "http://");
  strcat(requestUpdateURL, host_server);
  strcat(requestUpdateURL, "/relay/update");

  // Check periodically for updates
  ticker.attach(UPDATE_CHECK_INTERVAL, updateCheck);
  delay(1000);
  // Do an update check now
  updateCheck();
}

// The default page for the AP
void onAPDefault() {
  Serial.println("onAPDefault");
  localServer.send(200, "text/plain", "R1 relay " + String(softap_ssid) + " unconfigured");
}

// Here when a setup request containing configuration data is received
void onAPSetup() {
  Serial.println("onAPSetup");
  String config = localServer.arg("config");
  if (config != "") {
    Serial.printf("Config: %s\n", config.c_str());
    localServer.send(200, "text/plain", config.c_str());
    writeTextToFile("/config", config.c_str());
    delay(1000);
    restart();
  }
  else {
    localServer.send(200, "text/plain", "Not connected");
  }
}

// Go into SoftAP mode
void softAPMode() {
  Serial.println("Soft AP mode");
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(localIP, localIP, subnet);
  WiFi.softAP(softap_ssid);
  delay(100);

  localServer.on("/", onAPDefault);
  localServer.on("/setup", onAPSetup);
  localServer.onNotFound(notFound);
  localServer.begin();

  ticker.attach(2, blink);
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
    return;
  }

//  writeTextToFile("/config", "");

  pinMode(ledPin, OUTPUT);
  pinMode(relayPin, OUTPUT);
  ledOff();

  // Build the SoftAp SSID
  String mac = WiFi.macAddress();
  Serial.println("MAC: " + mac);
  String ssid = "RBR-R1-XXXXXX";
  ssid[7] = mac[9];
  ssid[8] = mac[10];
  ssid[9] = mac[12];
  ssid[10] = mac[13];
  ssid[11] = mac[15];
  ssid[12] = mac[16];
  strcpy(softap_ssid, ssid.c_str());
  Serial.printf("SoftAP SSID: %s\n", softap_ssid);

  Serial.println("Read config from LittleFS/config");
  String config_p = readFileToText("/config");
  Serial.println("Config = " + config_p);
  if (config_p != "") {
    const char* config_s = config_p.c_str();
    StaticJsonDocument<400> config;
    DeserializationError error = deserializeJson(config, config_s);
    if (error) {
      Serial.println("LittleFS/config is not valid JSON");
      writeTextToFile("/config", "");
      restart();
    } else {
      Serial.println("Client mode");
      strcpy(name, config["name"]);
      strcpy(host_ssid, config["ssid"]);
      strcpy(host_password, config["password"]);
      strcpy(host_ipaddr, config["ipaddr"]);
      strcpy(host_gateway, config["gateway"]);
      strcpy(host_server, config["server"]);
      if (name[0] == '\0' || host_ssid[0] == '\0' || host_password[0] == '\0'
      || host_ipaddr[0] == '\0' || host_gateway[0] == '\0' || host_server[0] == '\0') {
        Serial.println("Bad config data - resetting");
        factoryReset();
      } else {
        connectToHost();
      }
    }
  } else {
    softAPMode();
  }
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop() {
  localServer.handleClient();

  if (relayPinStatus) {
    digitalWrite(relayPin, LOW);
  }
  else {
    digitalWrite(relayPin, HIGH);
  }

  char response[4];
  if (checkForUpdate) {
    checkForUpdate = false;
    Serial.printf("Check for update at %s\n", requestVersionURL);
    httpGET(requestVersionURL, response);
    int newVersion = atoi(response);
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
