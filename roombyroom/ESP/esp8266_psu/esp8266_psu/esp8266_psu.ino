// RBR smart power supply

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266httpUpdate.h>
#include <WiFiClientSecureBearSSL.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 1
#define BAUDRATE 115200
#define REQUEST_CHECK_INTERVAL 30
#define UPDATE_CHECK_INTERVAL 600

// Constants
const IPAddress localIP(192,168,66,1);
const IPAddress subnet(255,255,255,0);

Ticker requestTicker;
Ticker updateTicker;
ESP8266WebServer localServer(80);
DynamicJsonDocument config(256);

uint8_t relayPin = 0;
uint8_t ledPin = 2;
bool relayPinStatus = LOW;
bool checkForRequest = false;
bool checkForUpdate = false;
bool busy = false;
bool updating = false;
bool power = false;
char my_ssid[40];
char my_password[40];
char host_ssid[40];
char host_password[20];
char server[120];
char rest[120];
char myid[18];
char pass[30];
char restarts[10];

// The default page when configured
void onDefault() {
  char info[100];
  sprintf(info, "RBR PS V%d %s %d %s ", CURRENT_VERSION, host_ssid, WiFi.RSSI(), restarts);
  strcat(info, power ? "ON" : "OFF");
  Serial.println(info);
  sendPlain(info);
}

// Check if a request is waiting.
void requestCheck() {
  checkForRequest = true;
}

// Check if an update is available.
void updateCheck() {
  checkForUpdate = true;
}

void led(uint8 state) {
  if (ledPin != relayPin) {
    digitalWrite(ledPin, state);
  }
}

void relay(uint8 state) {
  digitalWrite(relayPin, state);
  power = state;
  Serial.printf("Relay %s\n", state ? "OFF" : "ON");
}

void relayOn() {
  relay(LOW);
  led(LOW);
}

void relayOff() {
  relay(HIGH);
  led(HIGH);
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

void blink() {
  for (int n = 0; n < 3; n++) {
    led(LOW);
    delay(100);
    led(HIGH);
    delay(100);
  };
}

// Restart the system
void restart() {
  // delay(10000);
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
  strcpy(restarts, "0");
  writeTextToFile("/restarts", restarts);
  onDefault();
}

// Perform a GET
char* httpGET(char* requestURL) {
  // Serial.printf("GET %s\n", requestURL);
  BearSSL::WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  char* response = (char*)malloc(1);  // Provide something to 'free'
  response[0] = '\0';

  http.begin(client, requestURL);

  // Send HTTP GET request
  int httpResponseCode = http.GET();
  // Serial.printf("Response code %d\n", httpResponseCode);
  if (httpResponseCode < 0) {
    Serial.printf("GET %s: Error: %s\n", requestURL, http.errorToString(httpResponseCode).c_str());
    http.end();
    client.stop();
    return response;
  } else {
    if (httpResponseCode >= 200 && httpResponseCode < 400) {
      String httpPayload = http.getString();
      // Serial.printf("Payload length: %d\n", httpPayload.length());
      response = (char*)malloc(httpPayload.length() + 1);
      strcpy(response, httpPayload.c_str());
    }
    else {
      Serial.printf("Network error %d; restarting...\n", httpResponseCode);
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
      Serial.printf("\nCould not connect to %s/%s\n", host_ssid, host_password);
      delay(1000);
      restart();
    }
  }
  Serial.printf("\nConnected to %s as %s\n", host_ssid, WiFi.localIP().toString().c_str());
  delay(100);
}

// Connect to the controller network and accept relay commands
void connectToHost() {
  Serial.printf("%s %s %s %s\n", host_ssid, host_password, my_ssid, my_password);

  WiFi.mode(WIFI_AP_STA);
  // Set up our AP
  WiFi.softAPConfig(localIP, localIP, subnet);
  WiFi.softAP(my_ssid, my_password);
  Serial.println("SoftAP created");

  // Connect to the host
  connect();
  localServer.on("/", onDefault);
  localServer.on("/clear", onClear);
  localServer.on("/on", relayOn);
  localServer.on("/off", relayOff);
  localServer.on("/reset", onReset);
  localServer.on("/factoryreset", factoryReset);
  localServer.onNotFound(notFound);

  localServer.begin();

  requestTicker.attach(REQUEST_CHECK_INTERVAL, requestCheck);
  updateTicker.attach(UPDATE_CHECK_INTERVAL, updateCheck);
}

void badIP(char* ipaddr) {
    Serial.printf("Bad IP '%s'\n", ipaddr);
    factoryReset();
}

// The default page for the unconfigured AP
void onUnconfiguredAPDefault() {
  Serial.println("onAPDefault");
  sendPlain("RBR PS V" + String(CURRENT_VERSION) + ", " + String(my_ssid) + " unconfigured");
}

// Here when a setup request containing configuration data is received
void onConfigure() {
  Serial.println("Configure");
  String config = localServer.arg("config");
  if (config != "") {
    // Serial.printf("Config: %s\n", config.c_str());
    sendPlain(config.c_str());
    writeTextToFile("/config", config.c_str());
    Serial.println("Config string written to file");
    delay(1000);
    restart();
  }
  else {
    sendPlain("Not connected");
  }
}

void sendPlain(String message) {
  Serial.println(message);
  localServer.send(200, "text/plain", message);
}

// Go into Unconfigured AP mode
void UnconfiguredAPMode() {
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(localIP, localIP, subnet);
  char ssid[20];
  strcpy(ssid, my_ssid);
  ssid[4] = 'p';
  ssid[5] = 's';
  Serial.printf("RBR PSU - unconfigured: %s\n", ssid);
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

  pinMode(ledPin, OUTPUT);
  pinMode(relayPin, OUTPUT);
  relayOff();

  if (!LittleFS.begin()){
    LittleFS.format();
    return;
  }

  Serial.println("\n\n");

  // Count restarts
  int nRestarts = 0;
  const char* rs = readFileToText("/restarts");
  if (rs != NULL && rs[0] != '\0') {
    nRestarts = (atoi(rs) + 1) % 1000;
    free((void*)rs);
  }
  sprintf(restarts, "%d", nRestarts);
  writeTextToFile("/restarts", restarts);
  Serial.printf("\nRestarts: %d\n", nRestarts);
  // writeTextToFile("/config", ""); // Force unconfigured mode

  // Build the SoftAp SSID
  String myMAC = WiFi.macAddress();
  Serial.println("MAC: " + myMAC);
  String ssid = "RBR-PS-XXXXXX";
  ssid[7] = myMAC[9];
  ssid[8] = myMAC[10];
  ssid[9] = myMAC[12];
  ssid[10] = myMAC[13];
  ssid[11] = myMAC[15];
  ssid[12] = myMAC[16];
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
      Serial.println("RBR PSU");
      getConfigValue(config, "my_password", my_password);
      getConfigValue(config, "ssid", host_ssid);
      getConfigValue(config, "password", host_password);
      getConfigValue(config, "server", server);
      getConfigValue(config, "rest", rest);
      getConfigValue(config, "myid", myid);
      getConfigValue(config, "pass", pass);
      if (my_password[0] == '\0' || host_ssid[0] == '\0' || host_password[0] == '\0'
      || server[0] == '\0' || rest[0] == '\0' || myid[0] == '\0' || pass[0] == '\0') {
        Serial.println("Bad config data");
        factoryReset();
      } else {
        connectToHost();
        // checkForUpdate = true;
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

  if (checkForRequest) {
    checkForRequest = false;
    if (!busy) {
      busy = true;
      char query_url[200];
      sprintf(query_url,"https://%s/%s/%s/%s", server, rest, myid, pass);
      // Serial.printf("Check %s\n", query_url);
      char* response = httpGET(query_url);
      Serial.printf("Request: %s\n", response);
      if (response[0] == 'S') {
        Serial.println("Power on");
        relay(HIGH);
        led(HIGH);
      }
      else if (response[0] == 'H') {
        delay(90000);
        Serial.println("Power off");
        relay(LOW);
        led(LOW);
      }
      else if (response[0] == 'R') {
        delay(90000);
        Serial.println("Power off");
        relay(LOW);
        led(LOW);
        delay(10000);
        Serial.println("Power on");
        relay(HIGH);
        led(HIGH);
      }
      free(response);
      busy = false;
    }
  }

  if (checkForUpdate) {
    checkForUpdate = false;
    char buf[80];
    sprintf(buf, "https://%s/psu/version", server);
    Serial.printf("Get version from %s\n", buf);
    char* response = httpGET(buf);
    int newVersion = atoi(response);
    free(response);
    if (newVersion == 0) {
      restart();
    }
    if (newVersion > CURRENT_VERSION) {
      Serial.printf("Update to version %d\n", newVersion);
      updating = true;
      WiFiClient client;
      sprintf(buf, "http://%s/psu/download", server);
      Serial.printf("Download from %s\n", buf);
      t_httpUpdate_return ret = ESPhttpUpdate.update(client, buf);
      switch (ret) {
        case HTTP_UPDATE_FAILED:
          Serial.printf(ESPhttpUpdate.getLastErrorString().c_str());
          break;
        case HTTP_UPDATE_NO_UPDATES:
          Serial.println("No update took place");
          break;
        default:
          // This will never be reached as the device has restarted
          break;
      }
      updating = false;
    } else {
      Serial.printf("Version %d: Up to date\n", CURRENT_VERSION);
    }
  }
}
