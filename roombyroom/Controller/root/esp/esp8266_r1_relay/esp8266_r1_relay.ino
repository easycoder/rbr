// RBR R1 relay

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 4
#define BAUDRATE 115200
#define WATCHDOG_CHECK_INTERVAL 60
#define UPDATE_CHECK_INTERVAL 3600

// Constants
const IPAddress localIP(192,168,66,1);
const IPAddress subnet(255,255,255,0);

Ticker watchdogTicker;
Ticker updateTicker;
ESP8266WebServer localServer(80);
DynamicJsonDocument config(256);

uint8_t relayPin = 0;
uint8_t ledPin = 2;
uint watchdog = 0;
bool relayPinStatus = LOW;
bool checkForUpdate = false;
char name[40];
char my_ssid[40];
char my_password[40];
char host_ssid[40];
char host_password[20];
char host_ipaddr[20];
char host_gateway[20];
char host_server[20];
char requestVersionURL[40];
char requestUpdateURL[40];
char restarts[10];

// The default page when configured
void onDefault() {
  Serial.println("onDefault");
  char info[500];
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
  strcat(info, ")\nEndpoints:\n");
  strcat(info, "watchdog: Return the number of relay requests in the past minute\n");
  strcat(info, "reset: Restart the device\n");
  strcat(info, "restarts: Return the number of restarts\n");
  strcat(info, "clear: Clear the restart counter\n");
  strcat(info, "on: Turn on relay\n");
  strcat(info, "off: Turn off relay\n");
  Serial.println(info);
  localServer.send(200, "text/plain", info);
}

// The status page when configured
void onStatus() {
  Serial.println("onStatus");
  localServer.send(200, "text/plain", "C");
}

// Check the watchdog
void watchdogCheck() {
    // First check if we've had any requests since the last update. If not, restart.
    Serial.printf("Watchdog count is %d", watchdog);
    if (watchdog == 0) {
      Serial.println(": No requests have arrived in the past minute, so restart");
      restart();
    }
    Serial.println();
    watchdog = 0;
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
  watchdog++;
  localServer.send(200, "text/plain", "Relay ON");
}

void relayOff() {
  relayPinStatus = LOW;
  watchdog++;
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

// Get the watchdog count
void onWatchdog() {
  Serial.println("Watchdog");
  localServer.send(200, "text/plain", String(watchdog));
}

// Reset the system
void onReset() {
  Serial.println("Reset");
  localServer.send(200, "text/plain", "Reset");
  restart();
}

// Do a factory reset
void factoryReset() {
  Serial.println("Factory Reset");
  localServer.send(200, "text/plain", "Factory Reset");
  writeTextToFile("/config", "");
  restart();
}

// Report the number of restarts
void onRestarts() {
  Serial.println("Restarts");
  localServer.send(200, "text/plain", String(restarts));
}

// Clear the restart counter
void onClear() {
  Serial.println("Clear");
  strcpy(restarts, "0");
  writeTextToFile("/restarts", restarts);
  localServer.send(200, "text/plain", String(restarts));
}

// Perform a GET
void httpGET(char* requestURL, char* response) {
  WiFiClient client;
  HTTPClient http;

  http.begin(client, requestURL);

  String payload = "";

  // Send HTTP GET request
  int httpResponseCode = http.GET();

  if (httpResponseCode >= 200 && httpResponseCode < 400) {
    payload = http.getString();
  }
  else {
    if (httpResponseCode < 0) {
      Serial.printf("GET %s: Error: %s\n", requestURL, http.errorToString(httpResponseCode).c_str());
    } else {
      Serial.printf("Error code: %d\n", httpResponseCode);
    }
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

  WiFi.mode(WIFI_AP_STA);
  // Set up our AP
  WiFi.softAPConfig(localIP, localIP, subnet);
  WiFi.softAP(my_ssid, my_password);

  // Connect to the host
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA failed to configure");
  }
  WiFi.begin(host_ssid, host_password);
  Serial.print("Connecting ");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.printf("\nConnected to %s as %s\n", host_ssid, WiFi.localIP().toString().c_str());
  delay(100);

  localServer.on("/", onDefault);
  localServer.on("/status", onStatus);
  localServer.on("/restarts", onRestarts);
  localServer.on("/clear", onClear);
  localServer.on("/on", relayOn);
  localServer.on("/off", relayOff);
  localServer.on("/watchdog", onWatchdog);
  localServer.on("/reset", onReset);
  localServer.on("/factoryreset", factoryReset);
  localServer.onNotFound(notFound);

  localServer.begin();
  localServer.send(200, "text/plain", "Connected");

  strcat(requestVersionURL, "http://");
  strcat(requestVersionURL, host_server);
  strcat(requestVersionURL, "/relay/version");
  strcat(requestUpdateURL, "http://");
  strcat(requestUpdateURL, host_server);
  strcat(requestUpdateURL, "/relay/update");

  // Check the watchdog
  watchdogTicker.attach(WATCHDOG_CHECK_INTERVAL, watchdogCheck);

  // Check periodically for updates
  updateTicker.attach(UPDATE_CHECK_INTERVAL, updateCheck);
  delay(1000);
  // Do an update check now
  updateCheck();
}

// The default page for the unconfigured AP
void onUnconfiguredAPDefault() {
  Serial.println("onAPDefault");
  localServer.send(200, "text/plain", "R1 relay v" + String(CURRENT_VERSION) + ", " + String(my_ssid) + " unconfigured");
}

// The status page for the unconfigured AP
void onUnconfiguredAPStatus() {
  Serial.println("onAPStatus");
  localServer.send(200, "text/plain", "U");
}

// Here when a setup request containing configuration data is received
void onConfigure() {
  Serial.println("Configure the relay");
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

// Go into Unconfigured AP mode
void UnconfiguredAPMode() {
  Serial.println("Unconfigured AP mode");
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(localIP, localIP, subnet);
  char ssid[40];
  strcpy(ssid, my_ssid);
  ssid[4] = 'r';
  WiFi.softAP(ssid);
  delay(100);

  localServer.on("/", onUnconfiguredAPDefault);
  localServer.on("/status", onUnconfiguredAPStatus);
  localServer.on("/setup", onConfigure);
  localServer.onNotFound(notFound);
  localServer.begin();

  updateTicker.attach(2, blink);
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

  // Count restarts
  int nRestarts = 0;
  const char* rs = readFileToText("/restarts");
  if (rs != NULL && rs[0] != '\0') {
    nRestarts = atoi(rs) + 1;
    free((void*)rs);
  }
  sprintf(restarts, "%d", nRestarts);
  writeTextToFile("/restarts", restarts);
  Serial.printf("Restarts: %d\n", nRestarts);

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
  strcpy(my_ssid, ssid.c_str());
  Serial.printf("SoftAP SSID: %s\n", my_ssid);

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
      if (config.containsKey("name")) {
        strcpy(name, config["name"]);
      } else {
        name[0] = '\0';
      }
      if (config.containsKey("my_password")) {
        strcpy(my_password, config["my_password"]);
      } else {
        my_password[0] = '\0';
      }
      if (config.containsKey("ssid")) {
        strcpy(host_ssid, config["ssid"]);
      } else {
        host_ssid[0] = '\0';
      }
      if (config.containsKey("password")) {
        strcpy(host_password, config["password"]);
      } else {
        host_password[0] = '\0';
      }
      if (config.containsKey("ipaddr")) {
        strcpy(host_ipaddr, config["ipaddr"]);
      } else {
        host_ipaddr[0] = '\0';
      }
      if (config.containsKey("gateway")) {
        strcpy(host_gateway, config["gateway"]);
      } else {
        host_gateway[0] = '\0';
      }
      if (config.containsKey("server")) {
        strcpy(host_server, config["server"]);
      } else {
        host_server[0] = '\0';
      }
      if (name[0] == '\0' || my_password[0] == '\0' || host_ssid[0] == '\0' || host_password[0] == '\0'
      || host_ipaddr[0] == '\0' || host_gateway[0] == '\0' || host_server[0] == '\0') {
        Serial.println("Bad config data - resetting");
        factoryReset();
      } else {
        connectToHost();
      }
    }
  } else {
    UnconfiguredAPMode();
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
