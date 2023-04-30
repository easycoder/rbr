/* Wifi extender
*/

#include <WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncWebServer.h>
#include <EEPROM.h>
#include <Ticker.h>

#include "ESP32httpUpdate.h"

const uint currentVersion = 1;

// Local IP Address
const IPAddress localIP(192,168,4,1);
const IPAddress subnet(255,255,255,0);
String wifi_network_ssid = "";
String wifi_network_password = "";
String soft_ap_ssid = "";
String soft_ap_password = "";
String host_ipaddr;
String host_gateway;
String host_server;
bool connected = false;

// Serial baud rate
const int baudRate = 115200;

bool checkForUpdate = false;
int eepromPointer = 0;

Ticker ticker;

AsyncWebServer localServer(80);

// Write a string to EEPROM
void writeToEEPROM(String word) {
  delay(10);

  for (int i = 0; i < word.length(); ++i) {
    EEPROM.write(i, word[i]);
  }

  EEPROM.write(word.length(), '\0');
  EEPROM.commit();
}

void clearEEPROM() {
  writeToEEPROM("");
}

// Read a word (space delimited) from EEPROM
String readFromEEPROM() {
  String word = "";

  while (true) {
    char readChar = char(EEPROM.read(eepromPointer++));
    delay(10);
    if (readChar == '\n' || readChar == '\0') {
      break;
    }
    word += readChar;
  }
  return word;
}

// Checks if an update is available
void updateCheck() {
  checkForUpdate = true;
}

void setupLocalServer() {
  localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
  
    int paramsNr = request->params();
    Serial.println(paramsNr);

    for(int i=0;i<paramsNr;i++){

        AsyncWebParameter* p = request->getParam(i);
        Serial.print("Param name: ");
        Serial.println(p->name());
        Serial.print("Param value: ");
        Serial.println(p->value());
        Serial.println("------");
    }

    request->send(200, "text/plain", "message received");
  });

  localServer.on("/reset", HTTP_GET, [](AsyncWebServerRequest *request){
    Serial.println("Reset");
    connected= false;
//  WiFi.softAPdisconnect(true);
//  writeToEEPROM("");
    request->send(200, "text/plain", "reset");
    delay(100);
//  setup();
  });

  localServer.on("/info", HTTP_GET, [](AsyncWebServerRequest *request){
    Serial.println("Endpoint: info");
    if (connected) {
      request->send(200, "text/plain", "Extender up and running");
    } else {
      request->send(200, "text/plain", "Not connected");
    }
  });

  localServer.on("/setup", HTTP_GET, [](AsyncWebServerRequest *request) {
    Serial.println("setup");
    if (!connected) {
      request->send(200, "text/plain", "OK");

      if(request->hasParam("wifi_network_ssid")) {
        AsyncWebParameter* p = request->getParam("wifi_network_ssid");
        wifi_network_ssid = p->value();
        Serial.println(wifi_network_ssid);
      }
      if (request->hasParam("wifi_network_password")) {
        AsyncWebParameter* p = request->getParam("wifi_network_password");
        wifi_network_password = p->value();
        Serial.println(wifi_network_password);
      }
      if (request->hasParam("soft_ap_ssid")) {
        AsyncWebParameter* p = request->getParam("soft_ap_ssid");
        soft_ap_ssid = p->value();
        Serial.println(soft_ap_ssid);
      }
      if (request->hasParam("soft_ap_password")) {
        AsyncWebParameter* p = request->getParam("soft_ap_password");
        soft_ap_password = p->value();
        Serial.println(soft_ap_password);
      }
      if (request->hasParam("host_ipaddr")) {
        AsyncWebParameter* p = request->getParam("host_ipaddr");
        host_ipaddr = p->value();
        Serial.println(host_ipaddr);
      }
      if (request->hasParam("host_gateway")) {
        AsyncWebParameter* p = request->getParam("host_gateway");
        host_gateway = p->value();
        Serial.println(host_gateway);
      }
      if (request->hasParam("host_server")) {
        AsyncWebParameter* p = request->getParam("host_server");
        host_server = p->value();
        Serial.println(host_server);
      }
      String configData = wifi_network_ssid + "\n" + wifi_network_password + "\n"
        + soft_ap_ssid + "\n" + soft_ap_password + "\n"
        + host_ipaddr + "\n" + host_gateway + "\n" + host_server;
  //    writeToEEPROM(configData);

      if (wifi_network_ssid != "" && wifi_network_password != "" 
      && soft_ap_ssid != "" && soft_ap_password != "" 
      && host_ipaddr != "" && host_gateway != "" && host_server != "") {
        setupNetwork();
      }
    } else {
      request->send(404, "text/plain", "Invalid request.");
    }
  });

  localServer.onNotFound([](AsyncWebServerRequest *request){
    request->send(404, "text/plain", "The content you are looking for was not found.");
  });

  localServer.begin();
}

void setupNetwork() {
  IPAddress ipaddr;
  IPAddress gateway;
  IPAddress server;
  ipaddr.fromString(host_ipaddr);
  if (!ipaddr) {
    Serial.println("UnParsable IP '" + host_ipaddr + "'");
//    onReset();
  }
  gateway.fromString(host_gateway);
  if (!gateway) {
    Serial.println("UnParsable IP '" + host_gateway + "'");
//    onReset();
  }
  server.fromString(host_server);
  if (!server) {
    Serial.println("UnParsable IP '" + host_server + "'");
//    onReset();
  }
  Serial.println("Disconnecting AP");
  delay(100);
  WiFi.softAPdisconnect(true);
  delay(100);
  WiFi.mode(WIFI_AP_STA);
  Serial.println("\n[*] Creating ESP32 AP");
  WiFi.softAP(soft_ap_ssid.c_str(), soft_ap_password.c_str());
  Serial.print("[+] AP Created with IP Gateway ");
  Serial.println(WiFi.softAPIP());

  WiFi.disconnect();
  delay(100);

  //connect to the controller's wi-fi network
  WiFi.mode(WIFI_STA);
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA failed to configure");
  }
  WiFi.begin(wifi_network_ssid.c_str(), wifi_network_password.c_str());
  while (WiFi.status() != WL_CONNECTED) {
      Serial.print(".");
      delay(100);
  }
  Serial.printf("\nConnected to %s as ", wifi_network_ssid); Serial.print(WiFi.localIP());
  Serial.print(" with RSSI "); Serial.println(WiFi.RSSI());
  delay(100);

  connected = true;

  // Check for updates every 10 minutes
  ticker.attach(600, updateCheck);
}

// Perform a GET
String httpGETRequest(const char* serverName) {
  WiFiClient client;
  HTTPClient http;
    
  http.begin(client, serverName);
  
  // Send HTTP GET request
  int httpResponseCode = http.GET();
  
  String payload = "{}"; 
  
  if (httpResponseCode>0) {
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);
    payload = http.getString();
  }
  else {
    Serial.print("Error code: ");
    Serial.println(httpResponseCode);
  }
  // Free resources
  http.end();

  return payload;
}

///////////////////////////////////////////////////////////////////////////////
// Start here
void setup() {
  Serial.begin(baudRate);
  delay(500);
  Serial.printf("\nVersion: %d\n",currentVersion);

  // Check if there's anything stored in EEPROM
  eepromPointer = 0;
  EEPROM.begin(512);
//  clearEEPROM();
  String wifi_network_ssid = ""; //readFromEEPROM();
  if (wifi_network_ssid != "") {
    Serial.println("WIFI_AP_STA mode");
    wifi_network_password = readFromEEPROM();
    soft_ap_ssid = readFromEEPROM();
    soft_ap_password = readFromEEPROM();
    host_ipaddr = readFromEEPROM();
    host_gateway = readFromEEPROM();
    host_server = readFromEEPROM();
    setupNetwork();
  }
  else {
    // Set up the soft AP
    Serial.println("Soft AP mode");
    String mac = WiFi.macAddress();
    String ssid = "RBR-000000";
    ssid[4] = mac[6];
    ssid[5] = mac[7];
    ssid[6] = mac[9];
    ssid[7] = mac[10];
    ssid[8] = mac[12];
    ssid[9] = mac[13];
    WiFi.softAPConfig(localIP, localIP, subnet);
    WiFi.softAP(ssid);
    delay(100);

//    localServer.on("/info", onInfo);
//    localServer.on("/setup", onSetup);
//    localServer.onNotFound(notFound);

    setupLocalServer();
  }
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop() {
//  localServer.handleClient();
  if (checkForUpdate) {
    Serial.println("Check for update");
    checkForUpdate = false;
    String serverPath = "http://" + host_server + "/extender/version";
    Serial.println(serverPath);
    String response = httpGETRequest(serverPath.c_str());
    response.trim();
    int newVersion = response.toInt();
    Serial.printf("Current version is %d, installed version is %d\n", currentVersion, newVersion);
    if (newVersion > currentVersion) {
      Serial.printf("Installing version %d\n", newVersion);
      WiFiClient client;
      ESPhttpUpdate.update("http://" + host_server + "/extender/binary");
    } else {
      Serial.println("No update needed");
    }
  }
}
