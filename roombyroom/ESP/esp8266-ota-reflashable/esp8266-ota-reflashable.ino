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

uint8_t ledPin = 2;
bool checkVersion = false;
bool connected = false;
int eepromPointer = 0;
String name = "";
IPAddress ipaddr;
IPAddress gateway;
String server;

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
void reset() {
  localServer.send(200, "text/plain", "Reset");
  WiFi.softAPdisconnect(true);
  writeToEEPROM("");
  delay(100);
  setup();
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

// Connect to the controller network and accept relay commands
void connectToHost(String name_s, String ssid, String password, String ipaddr_s, String gateway_s, String server_s) {
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

  server = server_s;

  // Connect to the controller's wi-fi network
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  WiFi.softAP(ssid);
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA failed to configure");
  }
  WiFi.begin(ssid, password);

  // Check we're connected to wi-fi network
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.print("\nWiFi connected with ipaddr "); Serial.println(WiFi.localIP());
  delay(100);

  // Here is where you add extra endpoints you need to handle
  localServer.on("/reset", reset);
  localServer.onNotFound(notFound);

  localServer.begin();
  localServer.send(200, "text/plain", "Connected");
  connected = true;

  ticker.attach(60, check);
}

// Here the configuration data arrives as a GET message
// i.e. http://{my-ip}/setup?name={name}&ssid={ssid}&password={password}&ipaddr={ipaddr}&gateway={gateway}&server={server}
void onAPConnect() {
  Serial.println("onAPConnect");
  String name = localServer.arg("name");
  String ssid = localServer.arg("ssid");
  String password = localServer.arg("password");
  String ipaddr = localServer.arg("ipaddr");
  String gateway = localServer.arg("gateway");
  String server = localServer.arg("server");

  if (name != "" && ssid != "" && password != "" && ipaddr != "" && gateway != "" && server != "") {
    localServer.send(200, "text/plain", "OK");
    writeToEEPROM(name + "\n" + ssid + "\n" + password + "\n" + ipaddr + "\n" + gateway + "\n" + server);
    delay(10000);  // Force a restart
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
  ledOff();

  // Check if there's anything stored in EEPROM
  eepromPointer = 0;
  EEPROM.begin(512);
  writeToEEPROM("");
  String name = readFromEEPROM();
  if (name != "") {
    Serial.println("Client mode");
    String ssid = readFromEEPROM();
    String password = readFromEEPROM();
    String ipaddr = readFromEEPROM();
    String gateway = readFromEEPROM();
    String server = readFromEEPROM();
    connectToHost(name, ssid, password, ipaddr, gateway, server);
  }
  else {
    // Set up the soft AP
    Serial.println("Soft AP mode");
    String mac = WiFi.macAddress();
    String ssid = "RBR-R1-000000";
    ssid[7] = mac[6];
    ssid[8] = mac[7];
    ssid[9] = mac[9];
    ssid[10] = mac[10];
    ssid[11] = mac[12];
    ssid[12] = mac[13];
    WiFi.mode(WIFI_AP);
    WiFi.softAPConfig(localIP, localIP, subnet);
    WiFi.softAP(ssid);
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

  if (checkVersion) {
    checkVersion = false;
    return;
    String requestURL = "Check for update at http://" + server + "/relay/version";
    Serial.println(requestURL);
    String response = httpGETRequest(requestURL.c_str());
    response.trim();
    int newVersion = response.toInt();
    if (newVersion > currentVersion) {
      Serial.printf("Installing version %d\n", newVersion);
      WiFiClient client;
      ESPhttpUpdate.update(client, server, 80, "/relay/binary");
    }
  }
}