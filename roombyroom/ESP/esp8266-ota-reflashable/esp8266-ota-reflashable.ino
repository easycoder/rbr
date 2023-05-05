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
bool checkVersion = false;
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

void ledOn() {
  digitalWrite(ledPin, LOW);
}

void ledOff() {
  digitalWrite(ledPin, HIGH);
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

// Checks every 60 minutes if an update is available
void check() {
  if (connected) {
    checkVersion = true;
  }
}

// Reset the system
void factoryReset() {
  Serial.print("Factory Reset");
  localServer.send(200, "text/plain", "Factory Reset");
  writeToEEPROM("");
  delay(10000);
  ESP.reset();
}

// Perform a GET
String httpGETRequest(const char* requestURL) {
  WiFiClient client;
  HTTPClient http;
    
  // Your IP address with path or Domain name with URL path 
  http.begin(client, requestURL);
  
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

// Connect to the controller network and accept requests with known endpoint formats
void connectToHost() {
  Serial.println("");
  Serial.println("Connection parameters:");
  Serial.println(name + "\n" + softap_ssid
  + "\n" + host_ssid + "\n" + host_password
  + "\n" + host_ipaddr + "\n" + host_gateway + "\n" + host_server);

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

  Serial.print("\nWiFi connected with ipaddr "); Serial.println(WiFi.localIP());
  delay(100);

  localServer.on("/reset", factoryReset);
  localServer.onNotFound(notFound);

  localServer.begin();
  localServer.send(200, "text/plain", "Connected");
  connected = true;

  ticker.attach(60, check);
}

// Here when a setup request containing configuration data is received
void onAPConnect() {
  Serial.println("onAPConnect");
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
    delay(10000);  // Force a restart
    ESP.reset(); // Just in case it failed
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
  softap_ssid = "RBR-XX-XXXXXX";
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
      writeToEEPROM("");
      delay(10000);
      ESP.reset();
    }
  }
  else {
    // Set up the soft AP
    Serial.println("Soft AP mode");
    WiFi.mode(WIFI_AP);
    WiFi.softAPConfig(localIP, localIP, subnet);
    WiFi.softAP(softap_ssid);
    delay(100);

    localServer.on("/setup", onAPConnect);
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

  if (checkVersion) {
    checkVersion = false;
    String requestURL = "Check for update at http://" + host_server + "/relay/version";
    Serial.println(requestURL);
    String response = httpGETRequest(requestURL.c_str());
    response.trim();
    int newVersion = response.toInt();
    if (newVersion > currentVersion) {
      Serial.printf("Installing version %d\n", newVersion);
      WiFiClient client;
      ESPhttpUpdate.update(client, host_server, 80, "/relay/binary");
    }
  }
}
