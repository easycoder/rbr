// RBR R1 relay

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WebServer.h>
#include <ESP8266httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 9
#define BAUDRATE 115200
#define WATCHDOG_CHECK_INTERVAL 120
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
uint watchdogCheckInterval;
bool relayPinStatus = LOW;
bool checkForUpdate = false;
bool updating = false;
bool relayState;
char name[40];
char my_ssid[40];
char my_password[40];
char host_ssid[40];
char host_password[20];
char host_ipaddr[20];
char host_gateway[20];
char host_server[20];
char restarts[10];

// The default page when configured
void onDefault() {
  Serial.println("onDefault");
  char info[100];
  sprintf(info, "RBR R1 v%d '%s' RSSI=%d %s/%s ",
    CURRENT_VERSION, name, WiFi.RSSI(), host_ssid, host_ipaddr);
  showRelayState(info);
}

void showRelayState(char* info) {
  char buf[20];
  sprintf(buf, "%s Restarts:%s", relayState ? "ON" : "OFF", restarts);
  strcat(info, buf);
  Serial.println(info);
  sendPlain(info);
}

// Check the watchdog
void watchdogCheck() {
    // First check if we've had any requests since the last update. If not, restart.
    Serial.printf("Watchdog count is %d", watchdog);
    if (watchdog == 0) {
      watchdogCheckInterval += WATCHDOG_CHECK_INTERVAL;
      writeWatchdogCheckInterval();
      restart();
    }
    if (watchdogCheckInterval > WATCHDOG_CHECK_INTERVAL) {
      watchdogCheckInterval = WATCHDOG_CHECK_INTERVAL;
      writeWatchdogCheckInterval();
    }
    Serial.println();
    watchdog = 0;
}

void writeWatchdogCheckInterval() {
  char buf[10];
  sprintf(buf, "%d", watchdogCheckInterval);
  writeTextToFile("/watchdog", buf);
}

// Check if an update is available.
void updateCheck() {
  Serial.println("Disconnect");
  WiFi.softAPdisconnect(true);
  checkForUpdate = true;
}

void led(uint8 state) {
  if (ledPin != relayPin) {
    digitalWrite(ledPin, state);
  }
}

void relayOnOff(bool state) {
  relayState = state;
  relayPinStatus = state ? HIGH : LOW;
  watchdog++;
  relayStatus();
}

void relayStatus() {
  char info[40];
  info[0] = '\0';
  showRelayState(info);
}

void relayOn() {
  relayOnOff(true);
}

void relayOff() {
  relayOnOff(false);
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
  led(LOW);
  delay(100);
  led(HIGH);
  delay(100);
  led(LOW);
  delay(100);
  led(HIGH);
}

// Restart the system
void restart() {
  delay(10000);
  ESP.reset();
}

// Reset the system
void onReset() {
  Serial.println("Reset");
  sendPlain("Reset");
  restart();
}

// Do a factory reset
void factoryReset() {
  sendPlain("Factory Reset");
  writeTextToFile("/config", "");
  restart();
}

// Clear the restart counter
void onClear() {
  Serial.println("Clear");
  sendPlain(String(restarts));
  strcpy(restarts, "0");
  writeTextToFile("/restarts", restarts);
}

// Perform a GET
char* httpGET(char* requestURL) {
  Serial.printf("GET %s\n", requestURL);
  WiFiClient client;
  HTTPClient http;
  char* response = (char*)malloc(1);  // Provide something to 'free'
  response[0] = '\0';

  http.begin(client, requestURL);

  // Send HTTP GET request
  int httpResponseCode = http.GET();
//  Serial.printf("Response code %d, %d errors\n", httpResponseCode, errorCount);
  if (httpResponseCode < 0) {
    Serial.printf("GET %s: Error: %s\n", requestURL, http.errorToString(httpResponseCode).c_str());
    http.end();
    client.stop();
    return response;
  } else {
    if (httpResponseCode >= 200 && httpResponseCode < 400) {
      String httpPayload = http.getString();
//      Serial.printf("Payload length: %d\n", httpPayload.length());
      response = (char*)malloc(httpPayload.length() + 1);
      strcpy(response, httpPayload.c_str());
      watchdogCheckInterval = WATCHDOG_CHECK_INTERVAL;
      writeWatchdogCheckInterval();
    }
    else {
//    Serial.printf("Network error %d; restarting...\n", httpResponseCode);
      restart();
    }
  }
  // Free resources
  http.end();
  client.stop();
//  Serial.printf("Response: %s\n", response);
  return response;
}

void connect() {
  WiFi.begin(host_ssid, host_password);
  Serial.print("Connecting ");
  int count = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
    if (++count > 100) {
      restart();
    }
  }
  Serial.printf("\nConnected to %s as %s\n", host_ssid, WiFi.localIP().toString().c_str());
  delay(100);
}

// Connect to the controller network and accept relay commands
void connectToHost() {
  Serial.printf("'%s' %s %s %s %s %s\n", name, host_ssid, host_password, host_ipaddr, my_ssid, my_password);

  // Check IP addresses are well-formed

  IPAddress ipaddr;
  IPAddress gateway;
  IPAddress server;

  if (!ipaddr.fromString(host_ipaddr)) {
    badIP(host_ipaddr);
  }

  if (!gateway.fromString(host_gateway)) {
    badIP(host_gateway);
  }

  if (!server.fromString(host_server)) {
    badIP(host_server);
  }

  WiFi.mode(WIFI_AP_STA);
  // Set up our AP
  WiFi.softAPConfig(localIP, localIP, subnet);
  WiFi.softAP(my_ssid, my_password);
  Serial.println("SoftAP created");

  // Connect to the host
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA config failed");
  }
  connect();
  localServer.on("/", onDefault);
  localServer.on("/clear", onClear);
  localServer.on("/on", relayOn);
  localServer.on("/off", relayOff);
  localServer.on("/status", relayStatus);
  localServer.on("/reset", onReset);
  localServer.on("/factoryreset", factoryReset);
  localServer.onNotFound(notFound);

  localServer.begin();

  // Set up the watchdogs
  watchdogTicker.attach(watchdogCheckInterval, watchdogCheck);
  updateTicker.attach(UPDATE_CHECK_INTERVAL, updateCheck);
}

void badIP(char* ipaddr) {
    Serial.printf("Bad IP '%s'\n", ipaddr);
    factoryReset();
}

// The default page for the unconfigured AP
void onUnconfiguredAPDefault() {
  Serial.println("onAPDefault");
  sendPlain("R1 relay v" + String(CURRENT_VERSION) + ", " + String(my_ssid) + " unconfigured");
}

// Here when a setup request containing configuration data is received
void onConfigure() {
  Serial.println("Configure");
  String config = localServer.arg("config");
  if (config != "") {
    // Serial.printf("Config: %s\n", config.c_str());
    sendPlain(config.c_str());
    writeTextToFile("/config", config.c_str());
    delay(1000);
    restart();
  }
  else {
    sendPlain("Not connected");
  }
}

void sendPlain(String message) {
    localServer.send(200, "text/plain", message);
}

// Read the 'controller' file. If it's not empty, use it to download a new version.
void doUpdate() {
  String config_p = readFileToText("/controller");
  if (config_p != "") {
    writeTextToFile("/controller", "");
    const char* config_s = config_p.c_str();
    StaticJsonDocument<400> config;
    DeserializationError error = deserializeJson(config, config_s);
    if (error) {
      Serial.println("Controller is not valid JSON");
      writeTextToFile("/config", "");
      restart();
    } else {
      getConfigValue(config, "ssid", host_ssid);
      getConfigValue(config, "pwd", host_password);
      Serial.printf("Controller ssid=%s, password=%s\n", host_ssid, host_password);
      if (host_ssid[0] == '\0' || host_password[0] == '\0') {
        Serial.println("Bad config data");
        factoryReset();
      } else {
        WiFi.mode(WIFI_STA);
        connect();
        writeTextToFile("/restarts", "0");
        updating = true;
        WiFiClient client;
        Serial.println("Start the update");
        t_httpUpdate_return ret = ESPhttpUpdate.update(client, "http://172.24.1.1/relay/current");
        switch (ret) {
          case HTTP_UPDATE_FAILED:
            Serial.printf(ESPhttpUpdate.getLastErrorString().c_str());
            restart();
            break;
          case HTTP_UPDATE_NO_UPDATES:
            Serial.println("No update took place");
            break;
          default:
            // This will never be reached as the device has restarted
            break;
        }
      }
    }
  }
}

// Go into Unconfigured AP mode
void UnconfiguredAPMode() {
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(localIP, localIP, subnet);
  char ssid[20];
  strcpy(ssid, my_ssid);
  ssid[4] = 'r';
  Serial.printf("RBR R1 - unconfigured: %s\n", ssid);
  WiFi.softAP(ssid);
  delay(100);

  localServer.on("/", onUnconfiguredAPDefault);
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

  if (!LittleFS.begin()){
    LittleFS.format();
    return;
  }

  doUpdate();

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

  // Deal with the watchdog check interval
  watchdogCheckInterval = WATCHDOG_CHECK_INTERVAL;
  const char* wf = readFileToText("/watchdog");
  if (wf != NULL && wf[0] != '\0') {
    watchdogCheckInterval = atoi(wf);
    free((void*)wf);
  }
  Serial.printf("Watchdog: %d\n", watchdogCheckInterval);

  // writeTextToFile("/config", ""); // Force unconfigured mode

  pinMode(ledPin, OUTPUT);
  pinMode(relayPin, OUTPUT);
  led(HIGH);

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

  String config_p = readFileToText("/config");
  if (config_p != "") {
    const char* config_s = config_p.c_str();
    StaticJsonDocument<400> config;
    DeserializationError error = deserializeJson(config, config_s);
    if (error) {
      Serial.println("LittleFS/config is not valid JSON");
      writeTextToFile("/config", "");
      restart();
    } else {
      Serial.println("RBR R1 Relay");
      getConfigValue(config, "name", name);
      getConfigValue(config, "my_password", my_password);
      getConfigValue(config, "ssid", host_ssid);
      getConfigValue(config, "password", host_password);
      getConfigValue(config, "ipaddr", host_ipaddr);
      getConfigValue(config, "gateway", host_gateway);
      getConfigValue(config, "server", host_server);
      if (name[0] == '\0' || my_password[0] == '\0' || host_ssid[0] == '\0' || host_password[0] == '\0'
      || host_ipaddr[0] == '\0' || host_gateway[0] == '\0' || host_server[0] == '\0') {
        Serial.println("Bad config data");
        factoryReset();
      } else {
        connectToHost();
        checkForUpdate = true;
      }
    }
  } else {
    UnconfiguredAPMode();
  }
}

void getConfigValue(StaticJsonDocument<400> config, String name, char* value) {
  if (config.containsKey(name)) {
    strcpy(value, config[name]);
  } else {
    value[0] = '\0';
  }
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop() {
  if (updating) {
    return;
  }
  localServer.handleClient();

  if (relayPinStatus) {
    digitalWrite(relayPin, LOW);
  }
  else {
    digitalWrite(relayPin, HIGH);
  }

  if (checkForUpdate) {
    checkForUpdate = false;
    char url[80];
    sprintf(url, "http://%s/relay/version", host_server);
    char* response = httpGET(url);
    int newVersion = atoi(response);
    free(response);
    if (newVersion > CURRENT_VERSION) {
      Serial.printf("Update to version %d\n", newVersion);
      sprintf(url, "http://%s/controller", host_server);
      char* controller = httpGET(url);
      writeTextToFile("/controller", controller);
      free(controller);
      restart();
    } else {
      Serial.printf("Version %d: Up to date\n", CURRENT_VERSION);
    }
  }
}
