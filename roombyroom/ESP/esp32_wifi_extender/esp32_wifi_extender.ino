// Wifi extender

#include <WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncWebServer.h>
#include <ESP32httpUpdate.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <Ticker.h>
#include "SPIFFS.h"

static const char *TAG = "example";

const uint currentVersion = 1;

// Local IP Address
const IPAddress localIP(192,168,23,1);
const IPAddress subnet(255,255,255,0);
const char* deviceRoot("http://192.168.23.");
const uint UPDATE_CHECK_INTERVAL = 60;

Preferences preferences;
const char* softap_ssid;
const char* softap_password;
const char* host_ssid;
const char* host_password;
const char* host_ipaddr;
const char* host_gateway;
const char* host_server;
const char* relayId;
const char* relayType;
bool relayState;
uint relayVersion = 0;
bool busyGettingUpdates = false;
bool busyUpdatingClient = false;
bool updateCheck = false;
AsyncWebServerRequest *relayVersionRequest;
AsyncWebServerRequest *relayUpdateRequest;
char requestVersionURL[40];
char requestUpdateURL[40];
char requestRelayVersionURL[40];
char requestRelayUpdateURL[40];

// Serial baud rate
const int baudRate = 115200;

Ticker ticker;

AsyncWebServer localServer(80);

// Schedule an update check
void scheduleUpdateCheck() {
  updateCheck = true;
}

// Endpoint: GET http://{ipaddr}/
void handle_root(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: root");
  request->send(200, "text/plain", "RBR WiFi extender (" + String(host_ssid) + "/" + String(host_ipaddr) + ")");
}

// Endpoint: GET http://{ipaddr}/info
void handle_info(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: info");
  request->send(200, "text/plain", "Extender up and running");
}

// Restart the system
void restart() {
  Serial.println("Restart");
  delay(10000); // Forces the watchdog to trigger
  ESP.restart();
}

// Endpoint: GET http://{ipaddr}/reset
void handle_reset(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: reset");
  preferences.clear();
  request->send(200, "text/plain", "reset");
  delay(100);
  restart();
}

// Endpoint: GET http://{ipaddr}/on?id={id}
void handle_on(AsyncWebServerRequest *request, const char* type, const char* id) {
  relayId = id;
  relayType = type;
  relayState = true;
  char response[20];
  strcpy(response, "Turn on relay ");
  strcat(response, id);
//  Serial.println(response);
  request->send(200, "text/plain", response);
}

// Endpoint: GET http://{ipaddr}/off?id={id}
void handle_off(AsyncWebServerRequest *request, const char* type, const char* id) {
  relayId = id;
  relayType = type;
  relayState = false;
  char response[20];
  strcpy(response, "Turn off relay ");
  strcat(response, id);
//  Serial.println(response);
  request->send(200, "text/plain", response);
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

// Set up endpoints and start the local server
void setupLocalServer() {
  Serial.println("Set up the local server");

  localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_root(request);
  });

  localServer.on("/info", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_info(request);
  });

  localServer.on("/reset", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_reset(request);
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
  ticker.attach(UPDATE_CHECK_INTERVAL, scheduleUpdateCheck);
  delay(1000);
  scheduleUpdateCheck();
}

// Set up the network
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
  WiFi.softAP(softap_ssid, softap_password);
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

  // Check for updates every 10 minutes
  ticker.attach(600, scheduleUpdateCheck);

  // Set up the local HTTP server
  setupLocalServer();
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
    Serial.printf("Error code: %d\n", httpResponseCode);
    restart();
  }
  // Free resources
  http.end();

  payload.trim();
  strcpy(response, payload.c_str());
}

// Endpoint: GET http://{ipaddr}/setup?(params)
void handle_setup(AsyncWebServerRequest *request) {
  Serial.println("setup");
  request->send(200, "text/plain", "OK");

  if(request->hasParam("config")) {
    AsyncWebParameter* p = request->getParam("config");
    String config_s = p->value();
    Serial.print(config_s);
  }
}

// Check for updated relay firmware
void checkRelayUpdate() {
  char response[4];
  bool error = false;
  Serial.printf("Check for relay update at %s\n", requestRelayVersionURL);
  httpGET(requestRelayVersionURL, response);
  int newVersion = atoi(response);
  if (newVersion == 0) {
    Serial.println("Bad response from host, so restarting");
    delay(10000);  // Bad response so restart
    ESP.restart();
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
    Serial.printf("Writing %d bytes to SPIFFS\n", len);
    File file = SPIFFS.open("/relay.bin", FILE_WRITE);
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
            // write it to SPIFFS
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
  busyGettingUpdates = true;
  if (updateCheck) {
    updateCheck = false;
    char response[4];
    Serial.printf("Check for update at %s\n", requestVersionURL);
    httpGET(requestVersionURL, response);
    int newVersion = atoi(response);
    if (newVersion == 0) {
      Serial.println("Bad response from host, so restarting");
      delay(10000);  // Bad response so restart
      ESP.restart();
    }
    Serial.printf("Installed version is %d, new version is %d\n", currentVersion, newVersion);
    if (newVersion > currentVersion) {
      Serial.printf("Installing version %d\n", newVersion);
      WiFiClient client;
      ESPhttpUpdate.update(requestUpdateURL);
    } else {
      checkRelayUpdate();
    }
  }
  busyGettingUpdates = false;
}
 
///////////////////////////////////////////////////////////////////////////////
// Start here
void setup(void) {
  Serial.begin(baudRate);
  delay(500);
  Serial.printf("\nVersion: %d\n",currentVersion);

  if (SPIFFS.begin(true)){
    Serial.println("SPIFFS mounted");
  } else {
    Serial.println("Formatting SPIFFS");
    if (SPIFFS.format()) {
      Serial.println("Success formatting");
      if (SPIFFS.begin(true)) {
        Serial.println("SPIFFS mounted");
      } else {
        Serial.println("An Error has occurred while mounting SPIFFS");
      }
    } else {
      Serial.println("\n\nError formatting");
    }
  }

  preferences.begin("RBR-EX", false);

  String ssid = "RBR-EX-000000";
  String mac = WiFi.macAddress();
  Serial.println("MAC: " + mac);
  ssid[7] = mac[9];
  ssid[8] = mac[10];
  ssid[9] = mac[12];
  ssid[10] = mac[13];
  ssid[11] = mac[15];
  ssid[12] = mac[16];
  softap_ssid = ssid.c_str();
  Serial.printf("SSID: %s\n", String(softap_ssid));

  // Set up the soft AP
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  delay(100);
  Serial.println("Read config from preferences");
  String config_p = preferences.getString("config");
  Serial.println("Config = " + config_p);
  const char* config_s = config_p.c_str();
  StaticJsonDocument<400> config;
  deserializeJson(config, config_s);
  host_ssid = config["host_ssid"];
  host_password = config["host_password"];
  softap_password = config["softap_password"];
  host_ipaddr = config["host_ipaddr"];
  host_gateway = config["host_gateway"];
  host_server = config["host_server"];
  if (host_ssid[0] == '\0' || host_password[0] == '\0' || softap_password[0] == '\0'
    || host_ipaddr[0] == '\0' || host_gateway[0] == '\0' || host_server[0] == '\0') {
    Serial.println("Missing config data");
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
  } else {
    Serial.println("Good to go");
    setupNetwork();
    Serial.println(String(softap_ssid) + " configured and running");
  }
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop(void) {
  if (busyGettingUpdates || busyUpdatingClient) {
    return;
  }
  if (relayId > 0) {
    Serial.print("ID = "); Serial.println(relayId);
    char deviceURL[40];
    strcpy(deviceURL, deviceRoot);
    strcat(deviceURL, relayId);
    if (relayType == "shelly") {
      strcat(deviceURL, "/relay/0?turn=");
    } else {
      strcat(deviceURL, "/");
    }
    if (relayState) {
      strcat(deviceURL, "on");
    } else {
      strcat(deviceURL, "off");
    }
    relayId = 0;
    char response[4];
    Serial.printf("GET %s\n", deviceURL);
    httpGET(deviceURL, response);
    Serial.println(response);
  }

  if (relayVersionRequest) {
    Serial.print("Received version request from ");
    Serial.println(relayVersionRequest->client()->remoteIP());
    relayVersionRequest->send(200, "text/plain", ((String)relayVersion).c_str());
    relayVersionRequest = 0;
  }

  if (relayUpdateRequest) {
    Serial.print("Received update request from ");
    Serial.println(relayUpdateRequest->client()->remoteIP());
    busyUpdatingClient = true;
    relayUpdateRequest->send(SPIFFS, "/relay.bin", "application/octet");
    Serial.print("Relay code sent to ");
    Serial.println(relayUpdateRequest->client()->remoteIP());
    relayUpdateRequest = 0;
    busyUpdatingClient = false;
  }

  checkForUpdates();
}