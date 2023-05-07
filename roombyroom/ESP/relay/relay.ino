#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266httpUpdate.h>
#include <EEPROM.h>
#include <Ticker.h>

const uint currentVersion = 0;

// Local IP Address
const IPAddress localIP(192,168,23,1);
const IPAddress subnet(255,255,255,0);

// Serial baud rate
const int baudRate = 115200;

uint8_t relayPin = 0;
uint8_t ledPin = 2;
bool relayPinStatus = LOW;
bool checkForUpdate = false;
bool connected = false;
int eepromPointer = 0;
String name = "";
String softap_ssid;
String host_ssid;
String host_password;
String host_ipaddr;
String host_gateway;
String host_server;

Ticker ticker;

ESP8266WebServer localServer(80);

// Checks if an update is available
void updateCheck() {
  if (connected) {
    checkForUpdate = true;
  }
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

// Write a string to EEPROM
void writeToEEPROM(String word) {
  delay(10);

  for (int i = 0; i < word.length(); ++i) {
    EEPROM.write(i, word[i]);
  }

  EEPROM.write(word.length(), '\0');
  EEPROM.commit();
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

// Checks eevery 60 minutes if an update is available
void check() {
  if (connected) {
    checkForUpdate = true;
  }
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
  writeToEEPROM("");
  restart();
}

// Perform a GET
String httpGETRequest(const char* serverName) {
  WiFiClient client;
  HTTPClient http;
    
  http.begin(client, serverName);
  
  // Send HTTP GET request
  int httpResponseCode = http.GET();
  
  String payload = "{}"; 
  
  if (httpResponseCode >= 200 && httpResponseCode < 400) {
    payload = http.getString();
  }
  else {
    Serial.printf("Error code: %d\n", httpResponseCode);
    restart();
  }
  // Free resources
  http.end();

  return payload;
}

// Connect to the controller network and accept relay commands
void connectToHost() {
  Serial.println("Connection parameters:");
  Serial.println(name + "\n" + softap_ssid
  + "\n" + host_ssid + "\n" + host_password
  + "\n" + host_ipaddr + "\n" + host_gateway + "\n" + host_server);

  // Check IP addresses are well-formed

  IPAddress ipaddr;
  IPAddress gateway;

  if (!ipaddr.fromString(host_ipaddr)) {
    Serial.println("UnParsable IP '" + host_ipaddr + "'");
    factoryReset();
  }

  if (!gateway.fromString(host_gateway)) {
    Serial.println("UnParsable IP '" + host_gateway + "'");
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

  Serial.printf("\nWiFi connected to %s with ipaddr %s\n", host_ssid.c_str(), WiFi.localIP().toString().c_str());
  delay(100);

  localServer.on("/", relayOff);
  localServer.on("/on", relayOn);
  localServer.on("/off", relayOff);
  localServer.on("/reset", factoryReset);
  localServer.onNotFound(notFound);

  localServer.begin();
  localServer.send(200, "text/plain", "Connected");
  connected = true;

  // Check for updates every 10 minutes
  ticker.attach(60, updateCheck);
}

// The default page for the AP
void onAPDefault() {
  Serial.println("onAPDefault");
  localServer.send(200, "text/plain", softap_ssid + " in unconfigured mode");
}

// Here when a setup request containing configuration data is received
void onAPSetup() {
  Serial.println("onAPSetup");
  name = localServer.arg("name");
  host_ssid = localServer.arg("ssid");
  host_password = localServer.arg("password");
  host_ipaddr = localServer.arg("ipaddr");
  host_gateway = localServer.arg("gateway");
  host_server = localServer.arg("server");

  if (name != "" && host_ssid != "" && host_password != ""
  && host_ipaddr != "" && host_gateway != "" && host_server != "") {
    localServer.send(200, "text/plain", "OK");
    writeToEEPROM(name + "\n" + host_ssid + "\n" + host_password
    + "\n" + host_ipaddr + "\n" + host_gateway + "\n" + host_server);
    restart();
  }
  else {
    localServer.send(200, "text/plain", "Not connected");
  }
}

///////////////////////////////////////////////////////////////////////////////
// Start here
void setup() {
  Serial.begin(baudRate);
  delay(500);
  Serial.printf("\nFlash size: %d\n",ESP.getFlashChipRealSize());
  Serial.printf("Version: %d\n",currentVersion);

  pinMode(ledPin, OUTPUT);
  pinMode(relayPin, OUTPUT);
  ledOff();

  // Build the SoftAp SSID
  String mac = WiFi.macAddress();
  Serial.printf("MAC: %s\n", mac.c_str());
  softap_ssid = "RBR-R1-XXXXXX";
  softap_ssid[7] = mac[9];
  softap_ssid[8] = mac[10];
  softap_ssid[9] = mac[12];
  softap_ssid[10] = mac[13];
  softap_ssid[11] = mac[15];
  softap_ssid[12] = mac[16];
  Serial.printf("SoftAP SSID: %s\n", softap_ssid.c_str());

  // Check if there's anything stored in EEPROM
  eepromPointer = 0;
  EEPROM.begin(512);
//  writeToEEPROM("");
  name = readFromEEPROM();
  if (name != "") {
    Serial.println("Client mode");
    host_ssid = readFromEEPROM();
    host_password = readFromEEPROM();
    host_ipaddr = readFromEEPROM();
    host_gateway = readFromEEPROM();
    host_server = readFromEEPROM();
    if (host_password != "" && host_ipaddr != "" && host_gateway != "" && host_server != "") {
      connectToHost();
    } else {
      Serial.println("Bad EEPROM data - resetting");
      factoryReset();
    }
  }
  else {
    // Set up the soft AP
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

  if (checkForUpdate) {
    checkForUpdate = false;
    String requestURL = "http://" + host_server + "/relay/version";
    Serial.println("Check for update at " + requestURL);
    String response = httpGETRequest(requestURL.c_str());
    response.trim();
    int newVersion = response.toInt();
    if (newVersion > currentVersion) {
      WiFiClient client;
      requestURL = "http://" + host_server + "/relay/update";
      Serial.printf("Installing version %d from %s\n", newVersion, requestURL.c_str());
      t_httpUpdate_return ret = ESPhttpUpdate.update(client, requestURL.c_str());
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
