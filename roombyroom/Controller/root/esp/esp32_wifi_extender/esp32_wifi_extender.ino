// Wifi extender

#include <WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncWebServer.h>
#include <ESP32httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 12
#define BAUDRATE 115200
#define WATCHDOG_CHECK_INTERVAL 120
#define UPDATE_CHECK_INTERVAL 3600
#define RELAY_DELAY 300
#define ERROR_MAX 10
#define FORMAT_LITTLEFS_IF_FAILED true
#define LED_PIN 2
#define LOG_LEVEL_NONE 0
#define LOG_LEVEL_LOW 1
#define LOG_LEVEL_MEDIUM 2
#define LOG_LEVEL_HIGH 3

// Local IP Address
const IPAddress localIP(192,168,32,1);
const IPAddress subnet(255,255,255,0);
const char* deviceRoot("http://192.168.32.");

char softap_ssid[40];
char softap_password[40];
char host_ssid[40];
char host_password[40];
char host_ipaddr[40];
char host_gateway[40];
char host_server[40];
char relayResponse[20][200];
char relayCommand[10][20];
char relayType[10][10];
bool relayState[10];
bool relayFlag[10];
uint relayVersion = 0;
uint logLevel = LOG_LEVEL_NONE;
uint watchdog = 0;
uint watchdogCheckInterval;
bool busyStartingUp = true;
bool busyGettingUpdates = false;
bool busyUpdatingClient = false;
bool busyDoingGET = false;
bool updateCheck = false;
bool errorCount = false;
bool restarted = false;
char restartedURL[60];
char requestVersionURL[40];
char requestUpdateURL[40];
char requestRelayVersionURL[40];
char requestRelayUpdaterURL[40];
char requestRelayUpdateURL[40];
char deviceURL[40];
char restarts[10];

Ticker watchdogTicker;
Ticker updateTicker;

AsyncWebServer localServer(80);

// Perform a GET
char* httpGET(char* requestURL, bool restartOnError = false) {
  if (logLevel == LOG_LEVEL_HIGH) {
    Serial.printf("GET %s\n", requestURL);
  }
  busyDoingGET = true;
  WiFiClient client;
  HTTPClient http;
  char* response = (char*)malloc(1);  // Provide something to 'free'
  response[0] = '\0';
    
  http.begin(client, requestURL);
  
  // Send HTTP GET request
  int httpResponseCode = http.GET();
  if (logLevel == LOG_LEVEL_HIGH) {
    Serial.printf("Response code %d, %d errors\n", httpResponseCode, errorCount);
  }
  if (httpResponseCode < 0) {
    if (logLevel > LOG_LEVEL_NONE && logLevel < LOG_LEVEL_HIGH) {
      Serial.printf("GET %s: Error: %s\n", requestURL, http.errorToString(httpResponseCode).c_str());
    }
    http.end();
    client.stop();
    busyDoingGET = false;
    return response;
  } else {
    if (httpResponseCode >= 200 && httpResponseCode < 400) {
      String httpPayload = http.getString();
      if (logLevel == LOG_LEVEL_HIGH) {
        Serial.printf("Payload length: %d\n", httpPayload.length());
      }
      response = (char*)malloc(httpPayload.length() + 1);
      strcpy(response, httpPayload.c_str());
      errorCount = 0;
    }
    else {
      if (restartOnError) {
        if (logLevel == LOG_LEVEL_HIGH) {
          Serial.printf("Network error %d; restarting...\n", httpResponseCode);
        }
        restart();
      } else {
        errorCount = errorCount + 1;
        if (logLevel == LOG_LEVEL_HIGH) {
          Serial.printf("Error %d (%d)\n", httpResponseCode, errorCount);
        }
        if (errorCount == ERROR_MAX) {
          restart();
        }
      }
    }
  }
  // Free resources
  http.end();
  client.stop();
  if (logLevel == LOG_LEVEL_HIGH) {
    Serial.printf("Response: %s\n", response);
  }
  busyDoingGET = false;
  return response;
}

void ledOn() {
  digitalWrite(LED_PIN, HIGH);
}

void ledOff() {
  digitalWrite(LED_PIN, LOW);
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
    if (logLevel >= LOG_LEVEL_MEDIUM) {
      Serial.println("file open failed");
    }
    char* empty = (char*)malloc(1);
    empty[0] = '\0';
    return empty;
  }
  size_t filesize = file.size();
  char* text = (char*)malloc(filesize + 1);
  String data = file.readString();
  file.close();
  strcpy(text, data.c_str());
  return text;
}

// Request a watchdog check
void requestWatchdogCheck() {
    // First check if we've had any requests since the last update. If not, restart.
    if (logLevel >= LOG_LEVEL_LOW) {
      Serial.printf("Watchdog count is %d", watchdog);
    }
    if (watchdog == 0) {
      Serial.println(": No recent requests");
      watchdogCheckInterval += WATCHDOG_CHECK_INTERVAL;
      delay(10);
      writeWatchdogCheckInterval();
      restart();
    }
    if (watchdogCheckInterval > WATCHDOG_CHECK_INTERVAL) {
      watchdogCheckInterval = WATCHDOG_CHECK_INTERVAL;
      writeWatchdogCheckInterval();
    }
    if (logLevel >= LOG_LEVEL_LOW) {
      Serial.println();
    }
    watchdog = 0;
}

void writeWatchdogCheckInterval() {
  char buf[10];
  sprintf(buf, "%d", watchdogCheckInterval);
  writeTextToFile("/watchdog", buf);
}

// Request an update check
void requestUpdateCheck() {
  updateCheck = true;
}

// Restart the system
void restart() {
  Serial.println("Forcing a restart...");
  delay(10000); // Forces the watchdog to trigger
  ESP.restart();
}

// Endpoint: GET http://{ipaddr}/reset
void handle_reset(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: reset");
  request->send(200, "text/plain", "Reset");
  restart();
}

// Endpoint: GET http://{ipaddr}/factory-reset
void handle_factory_reset(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: factory-reset");
  writeTextToFile("/config", "");
  request->send(200, "text/plain", "Factory reset");
  restart();
}

// Endpoint: GET http://{ipaddr}/
void handle_root(AsyncWebServerRequest *request) {
  char info[500];
  char buf[8];
  sprintf(buf, "%d", CURRENT_VERSION);
  strcpy(info, "RBR WiFi extender v");
  strcat(info, buf);
  strcat(info, " (");
  strcat(info, host_ssid);
  strcat(info, "/");
  strcat(info, host_ipaddr);
  strcat(info,"), ");
  sprintf(buf, "%s", String(restarts));
  strcat(info, buf);
  strcat(info, " restarts");
  Serial.println(info);
  request->send(200, "text/plain", info);
}

// Endpoint: GET http://{ipaddr}/setup?(params)
void handle_setup(AsyncWebServerRequest *request) {
  Serial.println("handle_setup");
  request->send(200, "text/plain", "OK");

  if(request->hasParam("config")) {
    AsyncWebParameter* p = request->getParam("config");
    String config = p->value();
    Serial.print(config);
    writeTextToFile("/config", config.c_str());
    restart();
  }
}

// Endpoint: GET http://{ipaddr}/relay/update
void handle_relay_updater(AsyncWebServerRequest *request) {
  if (busyUpdatingClient) {
    return;
  }
  busyUpdatingClient = true;
  Serial.printf("Received updater request from %s\n", request->client()->remoteIP().toString().c_str());
  request->send(LittleFS, "/updater.bin", "application/octet");
  Serial.print("Relay updater code sent to ");
  Serial.println(request->client()->remoteIP());
  busyUpdatingClient = false;
  delay(100);
}

// Endpoint: GET http://{ipaddr}/relay/current
void handle_relay_update(AsyncWebServerRequest *request) {
  if (busyUpdatingClient) {
    return;
  }
  busyUpdatingClient = true;
  Serial.printf("Received update request from %s\n", request->client()->remoteIP().toString().c_str());
  request->send(LittleFS, "/relay.bin", "application/octet");
  Serial.print("Relay code sent to ");
  Serial.println(request->client()->remoteIP());
  busyUpdatingClient = false;
  delay(100);
}

// Set the log level
void setLogLevel(AsyncWebServerRequest *request, int level) {
  Serial.printf("Set the log level to %d\n", level);
  logLevel = level;
  char buf[10];
  sprintf(buf, "%d", logLevel);
  writeTextToFile("/logLevel", buf);
  request->send(200, "text/plain", String(logLevel));
}

// Show the status of a relay
void showStatus(AsyncWebServerRequest *request, uint id) {
  if (logLevel >= LOG_LEVEL_MEDIUM) {
    Serial.printf("Relay %d response: %s\n", id, relayResponse[id]);
  }
  request->send(200, "text/plain", relayResponse[id]);
}

// Set up the network and the local server
void setupNetwork() {
  Serial.print("Network SSID: "); Serial.println(host_ssid);
  Serial.print("Network password: "); Serial.println(host_password);
  Serial.print("Soft AP SSID: "); Serial.println(softap_ssid);
  Serial.print("Soft AP password: "); Serial.println(softap_password);
  Serial.print("Host ipaddr: "); Serial.println(host_ipaddr);
  Serial.print("Host gateway: "); Serial.println(host_gateway);
  Serial.print("Host server: "); Serial.println(host_server);

  IPAddress ipaddr;
  IPAddress gateway;
  IPAddress server;

  ipaddr.fromString(host_ipaddr);
  if (!ipaddr) {
    Serial.println("UnParsable IP '" + String(host_ipaddr) + "'");
    restart();
  }
  gateway.fromString(host_gateway);
  if (!gateway) {
    Serial.println("UnParsable IP '" + String(host_gateway) + "'");
    restart();
  }
  server.fromString(host_server);
  if (!server) {
    Serial.println("UnParsable IP '" + String(host_server) + "'");
    restart();
  }
  
  // Set up the soft AP with up to 10 connections
  WiFi.softAP(softap_ssid, softap_password, 1, 0, 10);
  Serial.printf("Soft AP %s/%s created with IP ", softap_ssid, softap_password); Serial.println(WiFi.softAPIP());

  //connect to the controller's wi-fi network
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA failed to configure");
  }
  WiFi.begin(host_ssid, host_password);
  Serial.printf("Connecting to %s", host_ssid);
  while (WiFi.status() != WL_CONNECTED) {
      Serial.print(".");
      delay(100);
  }
  Serial.printf("\nConnected as %s with RSSI %d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  delay(100);

  // Set up the local HTTP server
  Serial.println("Set up the local server");

  localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_root(request);
  });

  localServer.on("/watchdog", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain", String(watchdog));
  });

  localServer.on("/clear", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain", String(restarts));
    strcpy(restarts, "0");
    writeTextToFile("/restarts", restarts);
  });

  localServer.on("/reset", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_reset(request);
  });

  localServer.on("/factory-reset", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_factory_reset(request);
  });

  localServer.on("/log/0", HTTP_GET, [](AsyncWebServerRequest *request) {
    setLogLevel(request, 0);
  });

  localServer.on("/log/1", HTTP_GET, [](AsyncWebServerRequest *request) {
    setLogLevel(request, 1);
  });

  localServer.on("/log/2", HTTP_GET, [](AsyncWebServerRequest *request) {
    setLogLevel(request, 2);
  });

  localServer.on("/log/3", HTTP_GET, [](AsyncWebServerRequest *request) {
    setLogLevel(request, 3);
  });

  localServer.on("/onoff", HTTP_GET, [](AsyncWebServerRequest *request) {
    AsyncWebParameter* p = request->getParam("id");
    const char* id_s = p->value().c_str();
    uint id = atoi(id_s) - 100;
    p = request->getParam("command");
    String str = p->value();
    str.replace(" ", "%20");
    const char* command = str.c_str();
    relayResponse[id][0] = '\0';
    strcpy(relayCommand[id], command);
    relayFlag[id] = true;
    watchdog++;
    int n = RELAY_DELAY;
    while (--n > 0) {
      delay(10);
      if (!relayFlag[id]) {
        break;
      }
    }
    if (logLevel >= LOG_LEVEL_MEDIUM) {
      Serial.printf("%dms: ", n * 10);
    }
    if (n > 0) {
      showStatus(request, id);
    } else {
      request->send(404, "text/plain", "Timeout");
    }
  });

  localServer.on("/relay/version", HTTP_GET, [](AsyncWebServerRequest *request) {
    Serial.printf("Received version request from %s\n", request->client()->remoteIP().toString().c_str());
    request->send(200, "text/plain", ((String)relayVersion).c_str());
    watchdog++;
  });

  localServer.on("/relay/update", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_relay_updater(request);
  });

  localServer.on("/relay/current", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_relay_update(request);
  });

  localServer.onNotFound([](AsyncWebServerRequest *request){
    request->send(404, "text/plain", "The content you are looking for was not found.");
  });

  localServer.begin();

  strcat(restartedURL, "http://");
  strcat(restartedURL, host_server);
  strcat(restartedURL, "/extender/restarted/");
  strcat(restartedURL, host_ipaddr);
  strcat(requestVersionURL, "http://");
  strcat(requestVersionURL, host_server);
  strcat(requestVersionURL, "/extender/version");
  strcat(requestUpdateURL, "http://");
  strcat(requestUpdateURL, host_server);
  strcat(requestUpdateURL, "/extender/update");
  strcat(requestRelayVersionURL, "http://");
  strcat(requestRelayVersionURL, host_server);
  strcat(requestRelayVersionURL, "/relay/version");
  strcat(requestRelayUpdaterURL, "http://");
  strcat(requestRelayUpdaterURL, host_server);
  strcat(requestRelayUpdaterURL, "/relay/update");
  strcat(requestRelayUpdateURL, "http://");
  strcat(requestRelayUpdateURL, host_server);
  strcat(requestRelayUpdateURL, "/relay/current");

  // Call the watchdog regularly
  watchdogTicker.attach(watchdogCheckInterval, requestWatchdogCheck);

  // Check for updates periodically
  updateTicker.attach(UPDATE_CHECK_INTERVAL, requestUpdateCheck);
  delay(1000);
  Serial.println("Run update check");
  requestUpdateCheck();
}

// Check for updated relay firmware
void checkRelayUpdate() {
  if (logLevel >= LOG_LEVEL_MEDIUM) {
    Serial.println("checkRelayUpdate");
  }
  bool error = false;
  if (logLevel >= LOG_LEVEL_MEDIUM) {
    Serial.printf("Check for relay update at %s\n", requestRelayVersionURL);
  }
  char* httpPayload = httpGET(requestRelayVersionURL, true);
  int newRelayVersion = atoi(httpPayload);
  free(httpPayload);
//  if (logLevel >= LOG_LEVEL_MEDIUM) {
  if (logLevel >= LOG_LEVEL_NONE) {
    Serial.printf("Current relay version is %d, new version is %d\n", relayVersion, newRelayVersion);
  }
  if (newRelayVersion > relayVersion) {
    if (logLevel >= LOG_LEVEL_MEDIUM) {
      Serial.printf("Get relay updater from %s\n",requestRelayUpdaterURL);
    }
    // Download the loader
    error = downloadFile(requestRelayUpdaterURL, "/updater.bin");
    if (error) {
      if (logLevel >= LOG_LEVEL_LOW) {
        Serial.println("An error occurred while downloading the relay updater");
      }
    }
    if (logLevel >= LOG_LEVEL_MEDIUM) {
      Serial.printf("Get relay update from %s\n",requestRelayUpdateURL);
    }
    // Download the binary
    error = downloadFile(requestRelayUpdateURL, "/relay.bin");
    if (error) {
      if (logLevel >= LOG_LEVEL_LOW) {
        Serial.println("An error occurred while downloading the relay binary");
      }
    }
  }
  if (newRelayVersion > relayVersion) {
    updateRelayVersion(newRelayVersion);
  }
}

// Download a file from the server
bool downloadFile(char* url, char* fileName) {
  bool error = false;
  WiFiClient wifi;
  HTTPClient client;
  client.begin(wifi, url);
  // Send HTTP GET request
  int httpResponseCode = client.GET();
  int len = client.getSize();
  if (len <= 0) {
    Serial.println("Download is empty");
    updateRelayVersion(0);
    restart();
  }
  Serial.printf("Writing %d bytes to LittleFS\n", len);
  File file = LittleFS.open(fileName, FILE_WRITE);
  if (!file) {
    if (logLevel >= LOG_LEVEL_LOW) {
      Serial.printf("There was an error opening %s for writing\n, fileName");
    }
  } else {
    // create buffer for read
    uint8_t buff[128] = { 0 };
    // get tcp stream
    WiFiClient * stream = client.getStreamPtr();
    // read all data from server
    while (client.connected() && (len > 0 || len == -1)) {
      // get available data size
      size_t size = stream->available();
      if (size) {
          // read up to 128 byte
          int c = stream->readBytes(buff, ((size > sizeof(buff)) ? sizeof(buff) : size));
          // write it to LitleFS
          if (!file.write(buff, c)) {
              error = true;
          }
          if (len > 0) {
            len -= c;
          }
      } 
      yield();
    }
    if (logLevel == LOG_LEVEL_HIGH) {
      Serial.println("Writing complete");
    }
    file.close();
    client.end();
  }
  return error;
}

void updateRelayVersion(int newVersion) {
  relayVersion = newVersion;
  char buf[10];
  sprintf(buf, "%d", relayVersion);
  writeTextToFile("/relay.version", buf);
}

// Check for updated extender and relay firmware
void checkForUpdates() {
  if (updateCheck) {
    updateCheck = false;
    busyGettingUpdates = true;

    // Now check for firmware update
    if (logLevel >= LOG_LEVEL_LOW) {
      Serial.printf("Check for update at %s\n", requestVersionURL);
    }
    char* httpPayload = httpGET(requestVersionURL, true);
    int newVersion = atoi(httpPayload);
    free(httpPayload);
    if (newVersion == 0) {
      if (errorCount > 10) {
        Serial.println("Update check: bad response from host, so restarting");
        restart();
      }
    } else {
      if (logLevel >= LOG_LEVEL_LOW) {
        Serial.printf("Installed version is %d, new version is %d\n", CURRENT_VERSION, newVersion);
      }
      if (newVersion > CURRENT_VERSION) {
        Serial.printf("Installing version %d\n", newVersion);
        WiFiClient client;
        ESPhttpUpdate.update(requestUpdateURL);
      }
    }
    checkRelayUpdate();
  }
  busyGettingUpdates = false;
  busyUpdatingClient = false;
  busyDoingGET = false;
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
 
///////////////////////////////////////////////////////////////////////////////
// Start here
void setup(void) {
  Serial.begin(BAUDRATE);
  delay(500);
  Serial.printf("\nVersion: %d\n",CURRENT_VERSION);

  if (!LittleFS.begin(FORMAT_LITTLEFS_IF_FAILED)){
    Serial.println("LITTLEFS begin Failed");
    return;
  }

  // Get the log level
  const char* ll = readFileToText("/logLevel");
  if (ll != NULL && ll[0] != '\0') {
    logLevel = atoi(ll);
    free((void*)ll);
  }
  char buf[10];
  sprintf(buf, "%d", logLevel);
  writeTextToFile("/logLevel", buf);

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

  const char* ver = readFileToText("/relay.version");
  relayVersion = atoi(ver);

//  writeTextToFile("/config", "");
// updateRelayVersion(0);

  String ssid = "RBR-EX-000000";
  String mac = WiFi.macAddress();
  Serial.println("MAC: " + mac);
  ssid[7] = mac[9];
  ssid[8] = mac[10];
  ssid[9] = mac[12];
  ssid[10] = mac[13];
  ssid[11] = mac[15];
  ssid[12] = mac[16];
  strcpy(softap_ssid, ssid.c_str());
  Serial.printf("SSID: %s\n", String(softap_ssid));

  // Set up the soft AP
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  delay(100);
  Serial.println("Read config from LittleFS/config");
  const char* config_s = readFileToText("/config");
  Serial.printf("Config = %s\n", config_s);
  if (config_s[0] != '\0') {
    StaticJsonDocument<400> config;
    DeserializationError error = deserializeJson(config, config_s);
    if (error) {
      Serial.println("LittleFS/config is not valid JSON");
      writeTextToFile("/config", "");
      restart();
    }
    strcpy(host_ssid, config["host_ssid"]);
    strcpy(host_password, config["host_password"]);
    strcpy(softap_password, config["softap_password"]);
    strcpy(host_ipaddr, config["host_ipaddr"]);
    strcpy(host_gateway, config["host_gateway"]);
    strcpy(host_server, config["host_server"]);
  }
  free((void*)config_s);
  Serial.println("Check the parameters");
  if (host_ssid[0] == '\0' || host_password[0] == '\0' || softap_password[0] == '\0'
    || host_ipaddr[0] == '\0' || host_gateway[0] == '\0' || host_server[0] == '\0') {
    Serial.println("Missing config data");
    softap_ssid[4] = 'e';
    softap_ssid[5] = 'x';
    WiFi.softAP(softap_ssid);
    Serial.printf("Soft AP %s created with IP ", softap_ssid); Serial.println(WiFi.softAPIP());
  
    localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
      Serial.println("onAPDefault");
      request->send(200, "text/plain", String(softap_ssid) + " in unconfigured mode");
    });

    localServer.on("/setup", HTTP_GET, [](AsyncWebServerRequest *request) {
      handle_setup(request);
    });

    localServer.onNotFound([](AsyncWebServerRequest *request) {
      request->send(404, "text/plain", "The content you are looking for was not found.");
    });

    localServer.begin();
    Serial.println(String(softap_ssid) + " not configured");

    pinMode(LED_PIN, OUTPUT);
    updateTicker.attach(2, blink);
  } else {
    // Here if we are already configured
    Serial.println("Good to go");
    setupNetwork();
    restarted = true;
    busyStartingUp = false;
  }
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop(void) {
  if (busyGettingUpdates || busyUpdatingClient || busyDoingGET) {
    return;
  }

  if (!busyStartingUp) {
    for (uint n = 0; n < 10; n++) {
      if (relayFlag[n]) {
        uint id = n + 100;
        strcpy(deviceURL, deviceRoot);
        char idbuf[5];
        sprintf(idbuf, "%d", id);
        strcat(deviceURL, idbuf);
        strcat(deviceURL, relayCommand[n]);
        if (logLevel >= LOG_LEVEL_MEDIUM) {
          Serial.printf("Relay %d: %s - ", n, deviceURL);
        }
        char* httpPayload = httpGET(deviceURL, false);
        if (logLevel >= LOG_LEVEL_MEDIUM) {
          Serial.printf("Status: %s\n", httpPayload);
        }
        strcpy(relayResponse[n], httpPayload);
        free(httpPayload);
        relayFlag[n] = false;
      }
    }
  }

  checkForUpdates();

  if (restarted) {
    restarted = false;
    char* httpPayload = httpGET(restartedURL, false);
    free(httpPayload);
    Serial.println(String(softap_ssid) + " configured and running");
  }
}