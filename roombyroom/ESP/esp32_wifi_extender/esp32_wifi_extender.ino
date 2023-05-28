// Wifi extender

#include <WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncWebServer.h>
#include <ESP32httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 6
#define BAUDRATE 115200
#define UPDATE_CHECK_INTERVAL 3600
#define ERROR_MAX 10
#define FORMAT_LITTLEFS_IF_FAILED true

// Local IP Address
const IPAddress localIP(192,168,23,1);
const IPAddress subnet(255,255,255,0);
const char* deviceRoot("http://192.168.23.");

char softap_ssid[40];
char softap_password[40];
char host_ssid[40];
char host_password[40];
char host_ipaddr[40];
char host_gateway[40];
char host_server[40];
char relayResponse[10][200];
char relayType[10][10];
bool relayState[10];
bool relayFlag[10];
uint relayVersion = 0;
bool busyStartingUp = true;
bool busyGettingUpdates = false;
bool busyUpdatingClient = false;
bool busyDoingGET = false;
bool updateCheck = false;
bool errorCount = false;
AsyncWebServerRequest *relayVersionRequest;
AsyncWebServerRequest *relayUpdateRequest;
char requestVersionURL[40];
char requestUpdateURL[40];
char requestRelayVersionURL[40];
char requestRelayUpdateURL[40];
char httpPayload[200];
char deviceURL[40];
char restarts[10];

Ticker ticker;

AsyncWebServer localServer(80);

// Perform a GET
void httpGET(char* requestURL, bool restartOnError) {
//  Serial.printf("%s\n", requestURL);
  busyDoingGET = true;
  WiFiClient client;
  HTTPClient http;
    
  http.begin(client, requestURL);

  httpPayload[0] = '\0';
  
  // Send HTTP GET request
  int httpResponseCode = http.GET();
//  Serial.printf("%d, %d\n", httpResponseCode, errorCount);
  if (httpResponseCode >= 200 && httpResponseCode < 400) {
    strncpy(httpPayload, http.getString().c_str(), 199);
    errorCount = 0;
  }
  else {
    if (restartOnError) {
      Serial.print("Network error. ");
      restart();
    } else {
      errorCount = errorCount + 1;
      Serial.printf("Error %d (%d)\n", httpResponseCode, errorCount);
      if (errorCount == ERROR_MAX) {
        restart();
      }
    }
  }
  // Free resources
  http.end();

  // Strip trailing white space
  int len = strlen(httpPayload);
  for (int n = 0; n < len; n++) {
    if (httpPayload[n] < ' ') {
      httpPayload[n] = '\0';
      break;
    }
  }
//  Serial.println(httpPayload);
  busyDoingGET = false;
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

// Request an update check
void requestUpdateCheck() {
  updateCheck = true;
}

// Restart the system
void restart() {
  Serial.println("Restarting...");
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
  char ver[8];
  sprintf(ver, "%d", CURRENT_VERSION);
  strcpy(info, "RBR WiFi extender V");
  strcat(info, ver);
  strcat(info, " (");
  strcat(info, host_ssid);
  strcat(info, "/");
  strcat(info, host_ipaddr);
  strcat(info, ")\nEndpoints:\n");
  strcat(info, "status: U or C\n");
  strcat(info, "reset: Restart the device\n");
  strcat(info, "restarts: Return the number of restarts\n");
  strcat(info, "clear: Clear the restart counter\n");
  strcat(info, "on/{n}: Turn on relay {n}\n");
  strcat(info, "off/{n}: Turn off relay {n}\n");
  strcat(info, "relay/version: Get the current relay firmware version\n");
  strcat(info, "relay/update: Get the current relay firmware");
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

// Endpoint: GET http://{ipaddr}/on?id={id}
void handle_on(AsyncWebServerRequest *request, const char* type, const char* id_s) {
  uint id = atoi(id_s) - 100;
  strcpy(relayType[id], type);
  relayState[id] = true;
  relayFlag[id] = true;
  request->send(200, "text/plain", relayResponse[id]);
}

// Endpoint: GET http://{ipaddr}/off?id={id}
void handle_off(AsyncWebServerRequest *request, const char* type, const char* id_s) {
  uint id = atoi(id_s) - 100;
  strcpy(relayType[id], type);
  relayState[id] = false;
  relayFlag[id] = true;
  request->send(200, "text/plain", relayResponse[id]);
}

// Endpoint: GET http://{ipaddr}/relay/version
void handle_relay_version(AsyncWebServerRequest *request) {
  if (relayVersionRequest) {
    return;
  }
  relayVersionRequest = request;
}

// Endpoint: GET http://{ipaddr}/relay/update
void handle_relay_update(AsyncWebServerRequest *request) {
  if (relayUpdateRequest) {
    return;
  }
  relayUpdateRequest = request;
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
  Serial.printf("\nConnected to %s as %s with RSSI %d\n", host_ssid, WiFi.localIP().toString().c_str(), WiFi.RSSI());
  delay(100);

  // Set up the local HTTP server
  Serial.println("Set up the local server");

  localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_root(request);
  });

  localServer.on("/status", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain", "C");
  });

  localServer.on("/restarts", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain", String(restarts));
  });

  localServer.on("/clear", HTTP_GET, [](AsyncWebServerRequest *request) {
    strcpy(restarts, "0");
    writeTextToFile("/restarts", restarts);
    request->send(200, "text/plain", String(restarts));
  });

  localServer.on("/reset", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_reset(request);
  });

  localServer.on("/factory-reset", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_factory_reset(request);
  });

  localServer.on("/on", HTTP_GET, [](AsyncWebServerRequest *request) {
    AsyncWebParameter* p = request->getParam("type");
    const char* type = p->value().c_str();
    p = request->getParam("id");
    const char* id = p->value().c_str();
    handle_on(request, type, id);
  });

  localServer.on("/off", HTTP_GET, [](AsyncWebServerRequest *request) {
    AsyncWebParameter* p = request->getParam("type");
    const char* type = p->value().c_str();
    p = request->getParam("id");
    const char* id = p->value().c_str();
    handle_off(request, type, id);
    delay(100);
  });

  localServer.on("/relay/version", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_relay_version(request);
  });

  localServer.on("/relay/update", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_relay_update(request);
  });

  localServer.onNotFound([](AsyncWebServerRequest *request){
    request->send(404, "text/plain", "The content you are looking for was not found.");
  });

  localServer.begin();

  strcat(requestVersionURL, "http://");
  strcat(requestVersionURL, host_server);
  strcat(requestVersionURL, "/extender/version");
  strcat(requestUpdateURL, "http://");
  strcat(requestUpdateURL, host_server);
  strcat(requestUpdateURL, "/extender/update");
  strcat(requestRelayVersionURL, "http://");
  strcat(requestRelayVersionURL, host_server);
  strcat(requestRelayVersionURL, "/relay/version");
  strcat(requestRelayUpdateURL, "http://");
  strcat(requestRelayUpdateURL, host_server);
  strcat(requestRelayUpdateURL, "/relay/update");

  // Check for updates every 10 minutes
  ticker.attach(UPDATE_CHECK_INTERVAL, requestUpdateCheck);
  delay(1000);
  requestUpdateCheck();
}

// Check for updated relay firmware
void checkRelayUpdate() {
  Serial.println("checkRelayUpdate");
  bool error = false;
  Serial.printf("Check for relay update at %s\n", requestRelayVersionURL);
  httpGET(requestRelayVersionURL, true);
  int newVersion = atoi(httpPayload);
  if (newVersion == 0) {
    Serial.println("Bad response from host, so restarting");
    restart();
  }
  Serial.printf("Current version is %d, new version is %d\n", relayVersion, newVersion);
  if (newVersion > relayVersion) {
    Serial.printf("Get relay binary from %s\n",requestRelayUpdateURL);
    // Download the binary
    WiFiClient wifi;
    HTTPClient client;
    client.begin(wifi, requestRelayUpdateURL);
    // Send HTTP GET request
    int httpResponseCode = client.GET();
    int len = client.getSize();
    Serial.printf("Writing %d bytes to LittleFS\n", len);
    File file = LittleFS.open("/relay.bin", FILE_WRITE);
    if (!file) {
      Serial.println("There was an error opening /relay.bin for writing");
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
      Serial.println("Writing complete");
      file.close();
      client.end();
      if (error) {
        Serial.println("An error occurred while downloading the relay binary");
      }
    }
  }
  relayVersion = newVersion;
}

// Check for updated extender and relay firmware
void checkForUpdates() {
  if (updateCheck) {
    updateCheck = false;
    busyGettingUpdates = true;
    Serial.printf("Check for update at %s\n", requestVersionURL);
    httpGET(requestVersionURL, true);
    int newVersion = atoi(httpPayload);
    if (newVersion == 0) {
      if (errorCount > 10) {
        Serial.println("Bad response from host, so restarting");
        delay(10000);  // Bad response so restart
        ESP.restart();
      }
    } else {
      Serial.printf("Installed version is %d, new version is %d\n", CURRENT_VERSION, newVersion);
      if (newVersion > CURRENT_VERSION) {
        Serial.printf("Installing version %d\n", newVersion);
        WiFiClient client;
        ESPhttpUpdate.update(requestUpdateURL);
      } else {
        checkRelayUpdate();
      }
    }
  }
  busyGettingUpdates = false;
  busyStartingUp = false;
  busyUpdatingClient = false;
  busyDoingGET = false;
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

  // writeTextToFile("/config", "");

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
    WiFi.softAP(softap_ssid);
    Serial.printf("Soft AP %s created with IP ", softap_ssid); Serial.println(WiFi.softAPIP());
  
    localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
      Serial.println("onAPDefault");
      request->send(200, "text/plain", String(softap_ssid) + " in unconfigured mode");
    });

    localServer.on("/status", HTTP_GET, [](AsyncWebServerRequest *request) {
      request->send(200, "text/plain", "U");
    });

    localServer.on("/setup", HTTP_GET, [](AsyncWebServerRequest *request) {
      handle_setup(request);
    });

    localServer.onNotFound([](AsyncWebServerRequest *request) {
      request->send(404, "text/plain", "The content you are looking for was not found.");
    });

    localServer.begin();
    Serial.println(String(softap_ssid) + " not configured");
  } else {
    Serial.println("Good to go");
    setupNetwork();
    Serial.println(String(softap_ssid) + " configured and running");
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
        if (strcmp(relayType[n], "shelly") == 0) {
          strcat(deviceURL, "/relay/0?turn=");
        } else {
          strcat(deviceURL, "/");
        }
        if (relayState[n]) {
          strcat(deviceURL, "on");
        } else {
          strcat(deviceURL, "off");
        }
        httpGET(deviceURL, false);
        strcpy(relayResponse[n], httpPayload);
//        Serial.printf("%s %s\n", deviceURL, httpPayload);
        relayFlag[n] = false;
      }
    }

    if (relayVersionRequest) {
      Serial.print("Received version request from ");
      Serial.println(relayVersionRequest->client()->remoteIP());
      relayVersionRequest->send(200, "text/plain", ((String)relayVersion).c_str());
      relayVersionRequest = 0;
      delay(100);
    }

    if (relayUpdateRequest) {
      Serial.print("Received update request from ");
      Serial.println(relayUpdateRequest->client()->remoteIP());
      busyUpdatingClient = true;
      relayUpdateRequest->send(LittleFS, "/relay.bin", "application/octet");
      Serial.print("Relay code sent to ");
      Serial.println(relayUpdateRequest->client()->remoteIP());
      relayUpdateRequest = 0;
      busyUpdatingClient = false;
      delay(100);
    }
  }

  checkForUpdates();
}