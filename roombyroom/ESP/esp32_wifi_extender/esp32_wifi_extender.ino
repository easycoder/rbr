// Wifi extender

#include <WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncWebServer.h>
#include <ESP32httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 19
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
uint onoffCount = 0;
uint pingCount = 0;
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
    if (logLevel > LOG_LEVEL_LOW && logLevel < LOG_LEVEL_HIGH) {
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

// Do a watchdog check
void watchdogCheck() {
    // First check if we've had any requests since the last update. If not, restart.
    if (logLevel >= LOG_LEVEL_LOW) {
      Serial.printf("Onoff %d, ping %d\n", onoffCount, pingCount);
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
        WiFi.reconnect();
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

// Reset the system
void reset() {
  Serial.println("Forcing a reset...");
  ESP.restart();
}

// Endpoint: GET http://{ipaddr}/reset
void handle_reset(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: reset");
  request->send(200, "text/plain", "Reset");
  reset();
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
  sprintf(info, "RBR WiFi extender v%d %s/%s Restarts:%s", CURRENT_VERSION, host_ssid, host_ipaddr, restarts);
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
  Serial.printf("Set the log level to %d\n", level);
  logLevel = level;
  char buf[10];
  sprintf(buf, "%d", logLevel);
  writeTextToFile("/logLevel", buf);
  request->send(200, "text/plain", String(logLevel));
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

  IPAddress ipaddr;
  IPAddress gateway;
  IPAddress server;

  ipaddr.fromString(host_ipaddr);
  if (!ipaddr) {
    Serial.println("UnParsable IP '" + String(host_ipaddr) + "'");
    ESP.restart();
  }
  gateway.fromString(host_gateway);
  if (!gateway) {
    Serial.println("UnParsable IP '" + String(host_gateway) + "'");
    ESP.restart();
  }
  server.fromString(host_server);
  if (!server) {
    Serial.println("UnParsable IP '" + String(host_server) + "'");
    ESP.restart();
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
    handle_default(request);
  });

  localServer.on("/ping", HTTP_GET, [](AsyncWebServerRequest *request) {
    pingCount++;
    request->send(200, "text/plain", String(pingCount));
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
      relayFlag[id] = true;
      int n = RELAY_DELAY;
      while (--n > 0) {
        delay(10);
        if (!relayFlag[id]) {
          onoffCount++;
          break;
        }
      }
      if (logLevel >= LOG_LEVEL_MEDIUM) {
        Serial.printf("Relay %d: ", id);
        if (n == 0) {
          Serial.println("Timeout");
        } else {
          Serial.printf("%d (%dms): %s\n", n, (RELAY_DELAY - n) * 10, relayResponse[id]);
        }
      }
      if (n > 0) {
        showStatus(request, id);
      } else {
        request->send(404, "text/plain", "Timeout");
      }
    }
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

  sprintf(restartedURL, "http://%s/extender/restarted/%s", host_server, host_ipaddr);
  sprintf(requestVersionURL, "http://%s/extender/version", host_server);
  sprintf(requestUpdateURL, "http://%s/extender/update", host_server);

  // Call the watchdog regularly
  watchdogTicker.attach(watchdogCheckInterval, watchdogCheck);

  // Check for updates periodically
  updateTicker.attach(UPDATE_CHECK_INTERVAL, requestUpdateCheck);
  delay(1000);
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
    char* httpPayload = httpGET(requestVersionURL, true);
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
        ESPhttpUpdate.update(requestUpdateURL);
        // This is never reached
      } else {
        Serial.printf("Firmware version %d\n", CURRENT_VERSION);
      }
    }
    //Get the relay version number
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

    updateTicker.attach(2, blink);
  } else {
    // Here if we are already configured
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

  if (!busyStartingUp && !busyUpdatingClient) {
    for (uint n = 0; n < 10; n++) {
      if (relayFlag[n]) {
        uint id = n + 100;
        strcpy(deviceURL, deviceRoot);
        sprintf(deviceURL, "%s%d%s", deviceRoot, id, relayCommand[n]);
        char* httpPayload = httpGET(deviceURL, false);
        if (logLevel >= LOG_LEVEL_HIGH) {
          Serial.printf("Relay %d: %s - Status: %s\n", n, deviceURL, deviceURL, httpPayload);
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
//    char* httpPayload = httpGET(restartedURL, false);
//    free(httpPayload);
    Serial.println(String(softap_ssid) + " configured and running");
  }
}
