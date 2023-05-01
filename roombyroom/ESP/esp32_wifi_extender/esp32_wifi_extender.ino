/* Wifi extender
*/

#include <WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncWebServer.h>
#include <ESP32httpUpdate.h>
#include <EEPROM.h>
#include <Ticker.h>

const uint currentVersion = 1;

// Local IP Address
const IPAddress localIP(192,168,23,1);
const IPAddress subnet(255,255,255,0);
String network_ssid;
String network_password;
String softap_ssid;
String softap_password;
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
  if (connected) {
    checkForUpdate = true;
  }
}

// Endpoint: GET http://(ipaddr)/
void handle_root(AsyncWebServerRequest *request) {
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

    request->send(200, "text/plain", "Message received");
}

// Endpoint: GET http://(ipaddr)/info
void handle_info(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: info");
  if (connected) {
    request->send(200, "text/plain", "Extender up and running");
  } else {
    request->send(200, "text/plain", "Not connected");
  }
}

// Do the reset
void reset() {
  Serial.println("Reset");
  delay(10000); // Forces the watchdog to trigger
}

// Endpoint: GET http://(ipaddr)/reset
void handle_reset(AsyncWebServerRequest *request) {
  writeToEEPROM("");
  request->send(200, "text/plain", "reset");
  delay(100);
  reset();
}

// Endpoint: GET http://(ipaddr)/setup?(params)
void handle_setup(AsyncWebServerRequest *request) {
  if (!connected) {
    Serial.println("setup");
    request->send(200, "text/plain", "OK");

    if(request->hasParam("network_ssid")) {
      AsyncWebParameter* p = request->getParam("network_ssid");
      network_ssid = p->value();
    }
    if (request->hasParam("network_password")) {
      AsyncWebParameter* p = request->getParam("network_password");
      network_password = p->value();
    }
    if (request->hasParam("softap_password")) {
      AsyncWebParameter* p = request->getParam("softap_password");
      softap_password = p->value();
    }
    if (request->hasParam("host_ipaddr")) {
      AsyncWebParameter* p = request->getParam("host_ipaddr");
      host_ipaddr = p->value();
    }
    if (request->hasParam("host_gateway")) {
      AsyncWebParameter* p = request->getParam("host_gateway");
      host_gateway = p->value();
    }
    if (request->hasParam("host_server")) {
      AsyncWebParameter* p = request->getParam("host_server");
      host_server = p->value();
    }
    String configData = network_ssid + "\n" + network_password+ "\n" + softap_password + "\n"
      + host_ipaddr + "\n" + host_gateway + "\n" + host_server;
    writeToEEPROM(configData);
    Serial.println("Data written to EEPROM");

    if (network_ssid != "" && network_password != "" && softap_password != ""
    && host_ipaddr != "" && host_gateway != "" && host_server != "") {
      reset();
    }
  } else {
    request->send(404, "text/plain", "Invalid request.");
  }
}

// Set up endpoints and start the local server
void setupLocalServer() {
  Serial.println("Set up the local server");

  localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_root(request);
  });

  localServer.on("/info", HTTP_GET, [](AsyncWebServerRequest *request){
    handle_info(request);
  });

  localServer.on("/setup", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_setup(request);
  });

  localServer.on("/reset", HTTP_GET, [](AsyncWebServerRequest *request){
    handle_reset(request);
  });

  localServer.onNotFound([](AsyncWebServerRequest *request){
    request->send(404, "text/plain", "The content you are looking for was not found.");
  });

  localServer.begin();
  // Check for updates every 10 minutes
  ticker.attach(60, updateCheck);
}

// Set up the network
void setupNetwork() {
  Serial.print("Network SSID: "); Serial.println(network_ssid);
  Serial.print("Network password: "); Serial.println(network_password);
  Serial.print("Soft AP password: "); Serial.println(softap_password);
  Serial.print("Host ipaddr: "); Serial.println(host_ipaddr);
  Serial.print("Host gateway: "); Serial.println(host_gateway);
  Serial.print("Host server: "); Serial.println(host_server);
  Serial.print("Soft AP SSID: "); Serial.println(softap_ssid);
  IPAddress ipaddr;
  IPAddress gateway;
  IPAddress server;
  ipaddr.fromString(host_ipaddr);
  if (!ipaddr) {
    Serial.println("UnParsable IP '" + host_ipaddr + "'");
    reset();
  }
  gateway.fromString(host_gateway);
  if (!gateway) {
    Serial.println("UnParsable IP '" + host_gateway + "'");
    reset();
  }
  server.fromString(host_server);
  if (!server) {
    Serial.println("UnParsable IP '" + host_server + "'");
    reset();
  }
  WiFi.softAP(softap_ssid, softap_password);
  Serial.printf("Soft AP %s/%s created with IP ", softap_ssid, softap_password); Serial.println(WiFi.softAPIP());

  delay(100);

  //connect to the controller's wi-fi network
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA failed to configure");
  }
  WiFi.begin(network_ssid.c_str(), network_password.c_str());
  Serial.printf("Connecting to %s", network_ssid);
  while (WiFi.status() != WL_CONNECTED) {
      Serial.print(".");
      delay(100);
  }
  Serial.printf("\nConnected to %s as ", network_ssid); Serial.print(WiFi.localIP());
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
  // Set up the soft AP
  softap_ssid = "RBR-000000";
  String mac = WiFi.macAddress();
  softap_ssid[4] = mac[6];
  softap_ssid[5] = mac[7];
  softap_ssid[6] = mac[9];
  softap_ssid[7] = mac[10];
  softap_ssid[8] = mac[12];
  softap_ssid[9] = mac[13];
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  delay(100);
  Serial.println("Read EPROM");
  network_ssid = readFromEEPROM();
  if (network_ssid != "") {
    Serial.println("Use saved configuration");
    network_password = readFromEEPROM();
    softap_password = readFromEEPROM();
    host_ipaddr = readFromEEPROM();
    host_gateway = readFromEEPROM();
    host_server = readFromEEPROM();
    setupNetwork();
    delay(100);
  } else {
    WiFi.softAP(softap_ssid);
    Serial.printf("Soft AP %s created with IP ", softap_ssid); Serial.println(WiFi.softAPIP());
    Serial.println("Not configured");
  }
  setupLocalServer();
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop() {
  if (checkForUpdate) {
    Serial.println("Check for update");
    checkForUpdate = false;
    String serverPath = "http://" + host_server + "/extender/version";
    Serial.println(serverPath);
    String response = httpGETRequest(serverPath.c_str());
    response.trim();
    int newVersion = response.toInt();
    Serial.printf("Installed version is %d, current version is %d\n", currentVersion, newVersion);
    if (newVersion > currentVersion) {
      Serial.printf("Installing version %d\n", newVersion);
      WiFiClient client;
      ESPhttpUpdate.update("http://" + host_server + "/extender/binary");
    } else {
      Serial.println("No update needed");
    }
  }
}