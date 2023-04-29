#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266httpUpdate.h>
#include <EEPROM.h>
#include <Ticker.h>

const uint currentVersion = 2;

// Local IP Address
const IPAddress localIP(192,168,4,1);
const IPAddress subnet(255,255,255,0);

// Serial baud rate
const int baudRate = 115200;

uint8_t relayPin = 0;
uint8_t ledPin = 2;
bool relayPinStatus = LOW;
bool checkVersion = false;
int eepromPointer = 0;
String name = "";
IPAddress ipaddr;
IPAddress gateway;

Ticker ticker;

ESP8266WebServer server(80);

void notFound(){
  server.send(404, "text/plain", "Not found");
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
  server.send(200, "text/plain", "Relay ON");
}

void relayOff() {
  relayPinStatus = LOW;
  server.send(200, "text/plain", "Relay Off");
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
  checkVersion = true;
}

// Connect to the controller network and accept relay commands
void connectToHost(String name_s, String ssid, String password, String ipaddr_s, String gateway_s) {
  Serial.println("");
  Serial.println("Connection parameters:");
  Serial.println(name_s + "\n" + ssid + "\n" + password + "\n" + ipaddr_s + "\n" + gateway_s);

  name = name_s;

  if (!ipaddr.fromString(ipaddr_s)) {
    Serial.println("UnParsable IP '" + ipaddr_s + "'");
    reset();
  }

  if (!gateway.fromString(gateway_s)) {
    Serial.println("UnParsable IP '" + gateway_s + "'");
    reset();
  }

  //connect to the controller's wi-fi network
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA Failed to configure");
  }
  WiFi.begin(ssid, password);

  //check wi-fi is connected to wi-fi network
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("Got IP: "); Serial.println(WiFi.localIP());
  delay(100);

  server.on("/", relayOff);
  server.on("/on", relayOn);
  server.on("/off", relayOff);
  server.on("/reset", reset);
  server.onNotFound(notFound);

  server.begin();
  server.send(200, "text/plain", "Connected");

  ticker.attach(3600, check);
}

// Reset the system
void reset() {
  WiFi.softAPdisconnect(true);
  writeToEEPROM("");
  delay(100);
  setup();
}

// Here when the configurator sends the ssid and password of the controller network
void onAPConnect() {
  String name = server.arg("name");
  String ssid = server.arg("ssid");
  String password = server.arg("password");
  String ipaddr = server.arg("ipaddr");
  String gateway = server.arg("gateway");
  String configData = name + "\n" + ssid + "\n" + password + "\n" + ipaddr + "\n" + gateway;
  writeToEEPROM(configData);

  if (name != "" && ssid != "" && password != "" && ipaddr != "" && gateway != "") {
    Serial.println("Disconnecting AP");
    ticker.detach();
    WiFi.softAPdisconnect(true);
    delay(100);
    connectToHost(name, ssid, password, ipaddr, gateway);
  }
  else {
    server.send(200, "text/plain", "Not connected");
  }
}

// Perform a GET
String httpGETRequest(const char* serverName) {
  WiFiClient client;
  HTTPClient http;
    
  // Your IP address with path or Domain name with URL path 
  http.begin(client, serverName);
  
  // Send HTTP POST request
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
  Serial.printf("\nFlash size: %d\n",ESP.getFlashChipRealSize());
  Serial.printf("Version: %d\n",currentVersion);

  pinMode(ledPin, OUTPUT);
  pinMode(relayPin, OUTPUT);
  ledOff();

  // Check if there's anything stored in EEPROM
  eepromPointer = 0;
  EEPROM.begin(512);
//  writeToEEPROM("");
  String name = readFromEEPROM();
  if (name != "") {
    Serial.println("Client mode");
    String ssid = readFromEEPROM();
    String password = readFromEEPROM();
    String ipaddr = readFromEEPROM();
    String gateway = readFromEEPROM();
    connectToHost(name, ssid, password, ipaddr, gateway);
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

    server.on("/", onAPConnect);
    server.onNotFound(notFound);

    server.begin();

    ticker.attach(2, blink);
  }
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop() {
  server.handleClient();

  if (relayPinStatus) {
    digitalWrite(relayPin, LOW);
  }
  else {
    digitalWrite(relayPin, HIGH);
  }

  if (checkVersion) {
    checkVersion = false;
    String serverPath = "http://" + gateway.toString() + "/relay/version";
    Serial.println(serverPath);
    String response = httpGETRequest(serverPath.c_str());
    response.trim();
    int newVersion = response.toInt();
    if (newVersion > currentVersion) {
      Serial.printf("Installing version %d\n", newVersion);
      WiFiClient client;
      ESPhttpUpdate.update(client, gateway.toString(), 80, "/relay/binary");
    }
  }
}
