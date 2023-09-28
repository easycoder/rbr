// Wifi extender

#include <WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncWebServer.h>
#include <ESP32httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 25
#define BAUDRATE 115200
#define WATCHDOG_CHECK_INTERVAL 120
#define UPDATE_CHECK_INTERVAL 3600
#define RELAY_DELAY 30
#define RELAY_ERROR_LIMIT 100
#define ERROR_MAX 10
#define FORMAT_LITTLEFS_IF_FAILED true
#define LED_PIN 2
#define LOG_LEVEL_NONE 0
#define LOG_LEVEL_LOW 1
#define LOG_LEVEL_MEDIUM 2
#define LOG_LEVEL_HIGH 3
#define RELAY_REQ_IDLE 0
#define RELAY_REQ_REQ 1
#define RELAY_REQ_ACTIVE 2

// Local IP Address
const IPAddress localIP(192,168,32,1);
const IPAddress subnet(255,255,255,0);
IPAddress ipaddr;
IPAddress gateway;
IPAddress server;
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
uint relayErrors[10];
uint relayFlag[10];
uint totalErrors;
uint relayVersion = 0;
uint logLevel = LOG_LEVEL_NONE;
uint onoffCount = 0;
uint pingCount = 0;
uint rid = 0;
uint watchdogCheckInterval;
bool busyStartingUp = true;
bool busyGettingUpdates = false;
bool busyDoingGET = false;
bool busyDoingRelay = false;
bool updateCheck = false;
bool errorCount = false;
bool running = false;
char info[80];
char deviceURL[40];
char restarts[10];

Ticker watchdogTicker;
Ticker updateTicker;

AsyncWebServer localServer(80);

 #ifdef __cplusplus
  extern "C" {
 #endif

  uint8_t temprature_sens_read();

#ifdef __cplusplus
}
#endif

// Perform a GET
char* httpGET(char* requestURL, bool restartOnError = false) {
  if (logLevel == LOG_LEVEL_HIGH) {
    Serial.printf("GET %s\n", requestURL);
  }
  busyDoingGET = true;
  WiFiClient client;
  HTTPClient http;
  char* response;

  http.begin(client, requestURL);

  // Send HTTP GET request
  int httpResponseCode = http.GET();
  if (logLevel == LOG_LEVEL_HIGH) {
    Serial.printf("Response code %d, %d errors\n", httpResponseCode, errorCount);
  }
  if (httpResponseCode < 0) {
    response = (char*)malloc(1);  // Provide something to 'free'
    response[0] = '\0';
    if (logLevel > LOG_LEVEL_LOW && logLevel < LOG_LEVEL_HIGH) {
      Serial.printf("GET %s: Error: %s\n", requestURL, http.errorToString(httpResponseCode).c_str());
    }
  } else {  // Happy flow
    if (httpResponseCode >= 200 && httpResponseCode < 400) {
      String httpPayload = http.getString();
      if (logLevel == LOG_LEVEL_HIGH) {
        Serial.printf("Payload length: %d\n", httpPayload.length());
      }
      response = (char*)malloc(httpPayload.length() + 1);
      strcpy(response, httpPayload.c_str());
      errorCount = 0;
    }
    else {  // Here if an error occurred
      response = (char*)malloc(1);  // Provide something to 'free'
      response[0] = '\0';
      if (restartOnError) {
        if (logLevel == LOG_LEVEL_HIGH) {
          Serial.printf("Network error %d; restarting...\n", httpResponseCode);
        }
        ESP.restart();
      } else {
        errorCount = errorCount + 1;
        if (logLevel == LOG_LEVEL_HIGH) {
          Serial.printf("Error %d (%d)\n", httpResponseCode, errorCount);
        }
        if (errorCount == ERROR_MAX) {
          reset();
        }
      }
    }
  }
  if (logLevel == LOG_LEVEL_HIGH) {
    Serial.printf("Response: %s\n", response);
  }
  // Free resources
  http.end();
  client.stop();
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

// Do a watchdog check
void watchdogCheck() {
  // Ping the system controller. Reset if no reply
  char request[80];
  sprintf(request, "http://%s/resources/php/rest.php/ping", host_server);
  char* httpPayload = httpGET(request, false);
  httpPayload[2] = '\0';
  if (strcmp(httpPayload, "OK") != 0) {
    Serial.println("Server ping failed");
    reset();
  }
  free(httpPayload);
  totalErrors = 0;
  // Count the number of relay errors. If more than the limit, reset.
  for (int n = 0; n < 10; n++) {
    totalErrors += relayErrors[n];
  }
  if (totalErrors > RELAY_ERROR_LIMIT) {
    Serial.println("Too many relay errors");
    reset();
  }
  // Check if we've had any requests since the last update. If not, restart.
  if (logLevel >= LOG_LEVEL_LOW) {
    Serial.printf("Onoff %d, ping %d, mem %d, errors %d\n", onoffCount, pingCount, esp_get_free_heap_size(), totalErrors);
  }
  if (onoffCount == 0 || pingCount == 0) {
    Serial.println("No recent requests");
    watchdogCheckInterval += WATCHDOG_CHECK_INTERVAL;
    writeWatchdogCheckInterval();
    if ((WiFi.status() == WL_CONNECTED))  {
      reset();
    } else {
      Serial.println("Reconnecting to WiFi...");
      WiFi.disconnect();
      WiFi.mode(WIFI_AP_STA);
      WiFi.softAPConfig(localIP, localIP, subnet);
      // WiFi.reconnect();
      setupHotspot();
    }
  }
  if (watchdogCheckInterval > WATCHDOG_CHECK_INTERVAL) {
    Serial.println("Reset watchdog interval");
    watchdogCheckInterval = WATCHDOG_CHECK_INTERVAL;
    writeWatchdogCheckInterval();
  }
  onoffCount = 0;
  pingCount = 0;
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

char* getUnconfiguredStatus() {
  int temperature = (int)round((temprature_sens_read() - 32) / 1.8);
  strcpy(info, (String(softap_ssid) + " unconfigured; temp=" + temperature).c_str());
  return info;
}

char* getConfiguredStatus() {
  int temperature = (int)round((temprature_sens_read() - 32) / 1.8);
  sprintf(info, "RBR WiFi extender v%d %s/%s Temp:%d Restarts:%s", CURRENT_VERSION, host_ssid, host_ipaddr, temperature, restarts);
  return info;
}

// Endpoint: GET http://{ipaddr}/reset
void handle_reset(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: reset");
  reset();
}

// Reset the system
void reset() {
  Serial.println("Forcing a reset...");
  delay(10);
  writeTextToFile("/restart", "Y");
  ESP.restart();
}

// Endpoint: GET http://{ipaddr}/factory-reset
void handle_factory_reset(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: factory-reset");
  writeTextToFile("/config", "");
  request->send(200, "text/plain", "Factory reset");
  reset();
}

// Endpoint: GET http://{ipaddr}/
void handle_default(AsyncWebServerRequest *request) {
  char info[200];
  int temperature = (int)round((temprature_sens_read() - 32) / 1.8);
  sprintf(info, "RBR WiFi extender v%d %s/%s Temp:%d Restarts:%s", CURRENT_VERSION, host_ssid, host_ipaddr, temperature, restarts);
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
    ESP.restart();
  }
}

// Set the log level
void setLogLevel(AsyncWebServerRequest *request, int level) {
  setTheLogLevel(level);
  request->send(200, "text/plain", String(logLevel));
}

// Set the log level
void setTheLogLevel(int level) {
  Serial.printf("Set the log level to %d\n", level);
  logLevel = level;
  char buf[10];
  sprintf(buf, "%d", logLevel);
  writeTextToFile("/logLevel", buf);
}

// Do a relay on or off request
void doOnOff(AsyncWebServerRequest *request) {
  if (!busyGettingUpdates) {
    AsyncWebParameter* p = request->getParam("id");
    const char* id_s = p->value().c_str();
    uint id = atoi(id_s) - 100;
    p = request->getParam("command");
    String str = p->value();
    str.replace(" ", "%20");
    const char* command = str.c_str();
    relayResponse[id][0] = '\0';
    strcpy(relayCommand[id], command);
    relayFlag[id] = RELAY_REQ_REQ;
    int n = RELAY_DELAY;
    while (--n > 0) {
      delay(100);
      if (relayFlag[id] == RELAY_REQ_IDLE) {
        onoffCount++;
        break;
      }
    }
    if (logLevel >= LOG_LEVEL_MEDIUM) {
      Serial.printf("Relay %d: ", id);
      if (n == 0) {
        Serial.println("Timeout");
      } else {
        Serial.printf("%d (%dms): %s\n", n, (RELAY_DELAY - n) * 100, relayResponse[id]);
      }
    }
    if (n > 0) {
      showStatus(request, id);
    } else {
      request->send(404, "text/plain", "Timeout");
    }
  } else {
    request->send(404, "text/plain", "-none-");
  }
}

// Show the status of a relay
void showStatus(AsyncWebServerRequest *request, uint id) {
  if (logLevel >= LOG_LEVEL_HIGH) {
    Serial.printf("Relay %d response: %s\n", id, relayResponse[id]);
  }
  request->send(200, "text/plain", relayResponse[id]);
}

// Set up the network and the local server
void setupNetwork() {
  Serial.printf("Network SSID: %s\nNetwork password: %s\nSoft AP SSID: %s\nSoft AP password: %s\nHost ipaddr: %s\nHost gateway: %s\nHost server: %s\n",
    host_ssid, host_password, softap_ssid, softap_password, host_ipaddr, host_gateway, host_server);

  ipaddr.fromString(host_ipaddr);
  if (!ipaddr) {
    Serial.println("UnParsable IP '" + String(host_ipaddr) + "'");
    reset();
  }
  gateway.fromString(host_gateway);
  if (!gateway) {
    Serial.println("UnParsable IP '" + String(host_gateway) + "'");
    reset();
  }
  server.fromString(host_server);
  if (!server) {
    Serial.println("UnParsable IP '" + String(host_server) + "'");
    reset();
  }

  setupHotspot();
}

// Set up the local hotspot and connect to the host
void setupHotspot() {
  // Set up the soft AP with up to 10 connections
  WiFi.softAP(softap_ssid, softap_password, 1, 0, 10);
  Serial.printf("Soft AP %s/%s created with IP %s\n", softap_ssid, softap_password, WiFi.softAPIP().toString().c_str());

  //connect to the controller's wi-fi network
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA failed to configure");
  }
  WiFi.begin(host_ssid, host_password);
  Serial.printf("Connecting to %s", host_ssid);
  int counter = 0;
  while (WiFi.status() != WL_CONNECTED) {
    if (++counter > 60) {
      reset();
    }
    Serial.print(".");
    delay(1000);
  }
  Serial.printf("\nConnected as %s with RSSI %d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  delay(100);

  // Set up the local HTTP server
  Serial.println("Set up the local server");

  localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_default(request);
  });

  localServer.on("/ping", HTTP_GET, [](AsyncWebServerRequest *request) {
    pingCount++;
    request->send(200, "text/plain", String(pingCount));
    if (logLevel >= LOG_LEVEL_MEDIUM) {
      Serial.printf("Ping %d\n", pingCount);
    }
  });

  localServer.on("/clear", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain", String(restarts));
    strcpy(restarts, "0");
    writeTextToFile("/restarts", restarts);
    Serial.println("Clear");
  });

  localServer.on("/blink", HTTP_GET, [](AsyncWebServerRequest *request) {
    blink();
    request->send(200, "text/plain", "OK");
  });

  localServer.on("/reset", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain", "Reboot requested");
    handle_reset(request);
  });

  localServer.on("/factory-reset", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain", "Factory reset requested");
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
    doOnOff(request);
  });

  localServer.on("/status", HTTP_GET, [](AsyncWebServerRequest *request) {
     AsyncWebParameter* p = request->getParam("id");
      const char* id_s = p->value().c_str();
      uint id = atoi(id_s) - 100;
      showStatus(request, id);
  });

  localServer.on("/relay/version", HTTP_GET, [](AsyncWebServerRequest *request) {
    Serial.printf("Version request from %s\n", request->client()->remoteIP().toString().c_str());
    request->send(200, "text/plain", ((String)relayVersion).c_str());
    // watchdog++;
  });

  localServer.on("/controller", HTTP_GET, [](AsyncWebServerRequest *request) {
    char buf[80];
    sprintf(buf, "{\"ssid\":\"%s\",\"pwd\":\"%s\"}", host_ssid, host_password);
    request->send(200, "text/plain", buf);
  });

  localServer.onNotFound([](AsyncWebServerRequest *request){
    request->send(404, "text/plain", "The content you are looking for was not found.");
  });

  localServer.begin();

  // Call the watchdog regularly
  watchdogTicker.attach(watchdogCheckInterval, watchdogCheck);

  // Check for updates periodically
  updateTicker.attach(UPDATE_CHECK_INTERVAL, requestUpdateCheck);
  // delay(1000);
  // Check now
  updateCheck = true;
}

// Check for updated extender and relay firmware
void checkForUpdates() {
  if (updateCheck) {
    updateCheck = false;
    busyGettingUpdates = true;

    if (logLevel >= LOG_LEVEL_LOW) {
      Serial.println("Check for update");
    }
    WiFiClient client;
    char request[40];
    sprintf(request, "http://%s/extender/version", host_server);
    delay(10);
    char* httpPayload = httpGET(request, true);
    int newVersion = atoi(httpPayload);
    free(httpPayload);
    if (newVersion == 0) {
      if (errorCount > 10) {
        Serial.println("Bad version number from host, so resetting");
        reset();
      }
    } else {
      if (newVersion > CURRENT_VERSION) {
        Serial.printf("Updating from %d to %d\n\n\n", CURRENT_VERSION, newVersion);
        writeTextToFile("/restarts", "0");
        WiFiClient client;
        sprintf(request, "http://%s/extender/current", host_server);
        ESPhttpUpdate.update(request);
        // This is never reached
      } else {
        Serial.printf("Firmware version %d\n", CURRENT_VERSION);
      }
    }
    // Get the relay version number
    char url[40];
    sprintf(url, "http://%s/relay/version", host_server);
    httpPayload = httpGET(url, true);
    relayVersion = atoi(httpPayload);
    free(httpPayload);
    Serial.printf("Relay version %d\n", relayVersion);
    if (relayVersion == 0) {
      reset();
    }
  }
  busyGettingUpdates = false;
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

// Process a message from the serial port (development only)
void processMessage(const char* msg) {
  char* message = (char*)malloc(strlen(msg) + 1);
  strcpy(message, msg);
  char* ptr = strchr(message, '=');
  if (ptr == NULL) {
    if (busyStartingUp) {
      Serial.printf("%s\n", getUnconfiguredStatus());
    } else {
      Serial.printf("%s\n", getConfiguredStatus());
    }
  } else {
    *ptr = '\0';
    ptr++;
    // Serial.printf("%s %s\n", message, ptr);
    if (strcmp(message, "ping") == 0) {
      Serial.println("ping OK");
    }
    else if (strcmp(message, "clear") == 0) {
      Serial.println("clear");
      strcpy(restarts, "0");
      writeTextToFile("/restarts", restarts);
    }
    else if (strcmp(message, "blink") == 0) {
      blink();
    }
    else if (strcmp(message, "log") == 0) {
      setTheLogLevel(atoi(ptr));
    }
    else if (strcmp(message, "reset") == 0) {
      reset();
    }
    else if (strcmp(message, "factory-reset") == 0) {
      writeTextToFile("/config", "");
      reset();
    }
  }
  free(message);

/*  
  localServer.on("/onoff", HTTP_GET, [](AsyncWebServerRequest *request) {
    doOnOff(request);
  });

  localServer.on("/relay/version", HTTP_GET, [](AsyncWebServerRequest *request) {
    Serial.printf("Version request from %s\n", request->client()->remoteIP().toString().c_str());
    request->send(200, "text/plain", ((String)relayVersion).c_str());
    // watchdog++;
  });

  localServer.on("/controller", HTTP_GET, [](AsyncWebServerRequest *request) {
    char buf[80];
    sprintf(buf, "{\"ssid\":\"%s\",\"pwd\":\"%s\"}", host_ssid, host_password);
    request->send(200, "text/plain", buf);
  });
*/
}

///////////////////////////////////////////////////////////////////////////////
// Start here
void setup(void) {
  Serial.begin(BAUDRATE);
  delay(500);
  pinMode(LED_PIN, OUTPUT);

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

  // Check if reboot
  char reboot = 'N';
  const char* rb = readFileToText("/reboot");
  if (rb != NULL && rb[0] != '\0') {
    reboot = rb[0];
    free((void*)rb);
  }
  if (reboot == 'Y') {
    Serial.println("Reboot requested");
    delay(10000);
  }
  writeTextToFile("/reboot", "N");

  // Count restarts
  int nRestarts = 0;
  const char* rs = readFileToText("/restarts");
  if (rs != NULL && rs[0] != '\0') {
    nRestarts = (atoi(rs) + 1) % 1000;
    free((void*)rs);
  }
  sprintf(restarts, "%d", nRestarts);
  writeTextToFile("/restarts", restarts);

  // Deal with the watchdog check interval
  watchdogCheckInterval = WATCHDOG_CHECK_INTERVAL;
  const char* wf = readFileToText("/watchdog");
  if (wf != NULL && wf[0] != '\0') {
    watchdogCheckInterval = atoi(wf);
    free((void*)wf);
  }

  // Init the relay flags
  for (uint n = 0; n < 10; n++) {
    relayFlag[n] == RELAY_REQ_IDLE;
    relayErrors[n] = 0;
  }

//  Uncoment the next line to force a return to unconfigured mode
//  writeTextToFile("/config", "");

  String ssid = "RBR-EX-000000";
  String mac = WiFi.macAddress();
  ssid[7] = mac[9];
  ssid[8] = mac[10];
  ssid[9] = mac[12];
  ssid[10] = mac[13];
  ssid[11] = mac[15];
  ssid[12] = mac[16];
  strcpy(softap_ssid, ssid.c_str());
  Serial.printf("\n\n\nMAC: %s, SSID: %s\n", mac.c_str(), String(softap_ssid));
  Serial.printf("Version %d Watchdog: %d, restarts: %d\n", CURRENT_VERSION, watchdogCheckInterval, nRestarts);

  // Set up the soft AP
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  delay(100);
  Serial.println("Read config from LittleFS/config");
  const char* config_s = readFileToText("/config");
  if (config_s[0] != '\0') {
    StaticJsonDocument<400> config;
    DeserializationError error = deserializeJson(config, config_s);
    if (error) {
      Serial.printf("Config = %s\n", config_s);
      Serial.println("Not valid JSON");
      writeTextToFile("/config", "");
      ESP.restart();
    }
    strcpy(host_ssid, config["host_ssid"]);
    strcpy(host_password, config["host_password"]);
    strcpy(softap_password, config["softap_password"]);
    strcpy(host_ipaddr, config["host_ipaddr"]);
    strcpy(host_gateway, config["host_gateway"]);
    strcpy(host_server, config["host_server"]);
  }
  free((void*)config_s);
  if (host_ssid[0] == '\0' || host_password[0] == '\0' || softap_password[0] == '\0'
    || host_ipaddr[0] == '\0' || host_gateway[0] == '\0' || host_server[0] == '\0') {
    Serial.println("Missing config data");
    softap_ssid[4] = 'e';
    softap_ssid[5] = 'x';
    WiFi.softAP(softap_ssid);
    Serial.printf("Soft AP %s created with IP ", softap_ssid); Serial.println(WiFi.softAPIP());

    localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
      Serial.println("onAPDefault");
      request->send(200, "text/plain", getUnconfiguredStatus());
    });

    localServer.on("/setup", HTTP_GET, [](AsyncWebServerRequest *request) {
      handle_setup(request);
    });

    localServer.onNotFound([](AsyncWebServerRequest *request) {
      request->send(404, "text/plain", "The content you are looking for was not found.");
    });

    localServer.begin();
    Serial.println(getUnconfiguredStatus());

    updateTicker.attach(2, blink);
  } else {
    // Here if we are already configured
    setupNetwork();
    busyStartingUp = false;
  }
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop(void) {
  if (Serial.available()) {     //wait for data available
    String teststr = Serial.readString();  //read until timeout
    teststr.trim();                        // remove any \r \n whitespace at the end of the String
    processMessage(teststr.c_str());
  }

  if (busyStartingUp || busyGettingUpdates || busyDoingGET) {
    return;
  }

  if (!busyStartingUp && !busyDoingRelay) {
    busyDoingRelay = true;
    if (relayFlag[rid] == RELAY_REQ_REQ) {
      relayFlag[rid] = RELAY_REQ_ACTIVE;
      uint id = rid + 100;
      strcpy(deviceURL, deviceRoot);
      sprintf(deviceURL, "%s%d%s", deviceRoot, id, relayCommand[rid]);
      char* httpPayload = httpGET(deviceURL, false);
      if (httpPayload[0] == '\0') {
        relayErrors[rid]++;
        if (logLevel >= LOG_LEVEL_LOW) {
          Serial.printf("No response from relay %d (%d)\n", rid, relayErrors[rid]);
        }
      } else {
        relayErrors[rid] = 0;
      }
      delay(10);
      if (logLevel >= LOG_LEVEL_HIGH) {
        Serial.printf("Relay %d: %s - Status: %s\n", rid, deviceURL, deviceURL, httpPayload);
      }
      strcpy(relayResponse[rid], httpPayload);
      free(httpPayload);
      relayFlag[rid] = RELAY_REQ_IDLE;
    }
    rid = ++rid % 10;
    busyDoingRelay = false;
  }

  checkForUpdates();

  if (!running) {
    running = true;
    char request[80];
    sprintf(request, "http://%s/resources/php/rest.php/ex-restarts/%s", host_server, restarts);
    char* httpPayload = httpGET(request, false);
    free(httpPayload);
    Serial.println(String(softap_ssid) + " configured and running");
  }
}
