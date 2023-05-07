/* Wifi extender
*/

#include <WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncWebServer.h>
#include <ESP32httpUpdate.h>
#include <Preferences.h>
#include <Ticker.h>
#include "SPIFFS.h"

static const char *TAG = "example";

const uint currentVersion = 1;
uint relayVersion = 0;

// Local IP Address
const IPAddress localIP(192,168,23,1);
const IPAddress subnet(255,255,255,0);
const String deviceRoot("http://192.168.23.");

Preferences preferences;
String softap_ssid;
String softap_password;
String host_ssid;
String host_password;
String host_ipaddr;
String host_gateway;
String host_server;
int relayId;
String relayType;
bool busy = false;
bool relayState;
bool updateCheck = false;
AsyncWebServerRequest *relayVersionRequest;
AsyncWebServerRequest *relayUpdateRequest;

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
    int paramsNr = request->params();
    Serial.println(paramsNr);

    for(int i=0;i<paramsNr;i++){

        AsyncWebParameter* p = request->getParam(i);
        Serial.print("Param name: ");
        Serial.println(p->name());
        Serial.print("Param value: ");
        Serial.println(p->value());
        Serial.println("------");
    }

    request->send(200, "text/plain", "Message received");
}

// Endpoint: GET http://{ipaddr}/info
void handle_info(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: info");
  request->send(200, "text/plain", "Extender up and running");
}

// Do the reset
void reset() {
  Serial.println("Reset");
  delay(10000); // Forces the watchdog to trigger
  ESP.restart();
}

// Endpoint: GET http://{ipaddr}/reset
void handle_reset(AsyncWebServerRequest *request) {
  Serial.println("Endpoint: reset");
  preferences.putString("softap_ssid", "");
  request->send(200, "text/plain", "reset");
  delay(100);
  reset();
}

// Endpoint: GET http://{ipaddr}/on?id={id}
void handle_on(AsyncWebServerRequest *request, String type, int id) {
  relayId = id;
  relayType = type;
  relayState = true;
//    Serial.println("Relay " + type + " " + id + " on");
  request->send(200, "text/plain", "Turn on relay " + id);
}

// Endpoint: GET http://{ipaddr}/off?id={id}
void handle_off(AsyncWebServerRequest *request, String type, int id) {
  relayId = id;
  relayType = type;
  relayState = false;
//    Serial.println("Relay " + type + " " + id + " off");
  request->send(200, "text/plain", "Turn off relay " + id);
}

// Endpoint: GET http://{ipaddr}/relay/version
void handle_relay_version(AsyncWebServerRequest *request) {
  if (relayVersionRequest) {
    return;
  }
  Serial.print("Received version request from ");
  Serial.println(request->client()->remoteIP());
  relayVersionRequest = request;
}

// Endpoint: GET http://{ipaddr}/relay/update
void handle_relay_update(AsyncWebServerRequest *request) {
  if (relayUpdateRequest) {
    return;
  }
  Serial.print("Received update request from ");
  Serial.println(request->client()->remoteIP());
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
      String type = p->value();
      p = request->getParam("id");
      int id = p->value().toInt();
    handle_on(request, type, id);
  });

  localServer.on("/off", HTTP_GET, [](AsyncWebServerRequest *request) {
      AsyncWebParameter* p = request->getParam("type");
      String type = p->value();
      p = request->getParam("id");
      int id = p->value().toInt();
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
  // Check for updates every 10 minutes
  ticker.attach(60, scheduleUpdateCheck);
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
    Serial.println("UnParsable IP '" + host_ipaddr + "'");
    reset();
  }
  gateway.fromString(host_gateway);
  if (!gateway) {
    Serial.println("UnParsable IP '" + host_gateway + "'");
    reset();
  }
  server.fromString(host_server);
  if (!server) {
    Serial.println("UnParsable IP '" + host_server + "'");
    reset();
  }
  WiFi.softAP(softap_ssid, softap_password);
  Serial.printf("Soft AP %s/%s created with IP ", softap_ssid, softap_password); Serial.println(WiFi.softAPIP());

  //connect to the controller's wi-fi network
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA failed to configure");
  }
  WiFi.begin(host_ssid.c_str(), host_password.c_str());
  Serial.printf("Connecting to %s", host_ssid.c_str());
  while (WiFi.status() != WL_CONNECTED) {
      Serial.print(".");
      delay(100);
  }
  Serial.printf("\nConnected to %s as %s with RSSI %d\n", host_ssid.c_str(), WiFi.localIP().toString().c_str(), WiFi.RSSI());
  delay(100);

  // Check for updates every 10 minutes
  ticker.attach(600, scheduleUpdateCheck);

  // Set up the local HTTP server
  setupLocalServer();
}

// Perform a GET
String httpGET(const char* serverName) {
  WiFiClient client;
  HTTPClient http;
    
  http.begin(client, serverName);
  
  // Send HTTP GET request
  int httpResponseCode = http.GET();
  
  String payload = "{}"; 
  
  if (httpResponseCode > 0) {
    if (httpResponseCode >= 400) {
      Serial.printf("HTTP Response code: %d\n", httpResponseCode);
    } else {
      payload = http.getString();
    }
  }
  else {
    Serial.print("Error code: ");
    Serial.println(httpResponseCode);
  }
  // Free resources
  http.end();

  return payload;
}

// Endpoint: GET http://{ipaddr}/setup?(params)
void handle_setup(AsyncWebServerRequest *request) {
  Serial.println("setup");
  request->send(200, "text/plain", "OK");

  if(request->hasParam("network_ssid")) {
    AsyncWebParameter* p = request->getParam("network_ssid");
    host_ssid = p->value();
  }
  if (request->hasParam("network_password")) {
    AsyncWebParameter* p = request->getParam("network_password");
    host_password = p->value();
  }
  if (request->hasParam("softap_password")) {
    AsyncWebParameter* p = request->getParam("softap_password");
    softap_password = p->value();
  }
  if (request->hasParam("host_ipaddr")) {
    AsyncWebParameter* p = request->getParam("host_ipaddr");
    host_ipaddr = p->value();
  }
  if (request->hasParam("host_gateway")) {
    AsyncWebParameter* p = request->getParam("host_gateway");
    host_gateway = p->value();
  }
  if (request->hasParam("host_server")) {
    AsyncWebParameter* p = request->getParam("host_server");
    host_server = p->value();
  }

  if (host_ssid != "" && host_password != "" && softap_password != ""
    && host_ipaddr != "" && host_gateway != "" && host_server != "") {
    // Save the configuration data
    preferences.putString("host_ssid", host_ssid);
    preferences.putString("host_password", host_password);
    preferences.putString("softap_password", softap_password);
    preferences.putString("host_ipaddr", host_ipaddr);
    preferences.putString("host_gateway", host_gateway);
    preferences.putString("host_server", host_server);
    Serial.println("Config data written to preferences");
  }
  reset();
}

// Check for updated relay firmware
void checkRelayUpdate() {
  bool error = false;
  String serverURL = "http://" + host_server + "/relay/version";
  Serial.println("Check for relay update at " + serverURL);
  String response = httpGET(serverURL.c_str());
  response.trim();
  int newVersion = response.toInt();
  if (newVersion == 0) {
    Serial.println("Bad response from host, so restarting");
    delay(10000);  // Bad response so restart
    ESP.restart();
  }
  Serial.printf("Current version is %d, new version is %d\n", relayVersion, newVersion);
  if (newVersion > relayVersion) {
    String serverURL = "http://" + host_server + "/relay/binary";
    Serial.println("Get relay binary from " + serverURL);
    // Download the binary
    WiFiClient wifi;
    HTTPClient client;
    client.begin(wifi, serverURL.c_str());
    // Send HTTP GET request
    int httpResponseCode = client.GET();
    int len = client.getSize();
    Serial.printf("Length: %d\n", len);
    Serial.println("Writing to SPIFFS");
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
      }
      Serial.println("Download complete");
      file.close();
      client.end();
      if (error) {
        Serial.println("An error occurred while downloading the relay binary");
      } else {
        relayVersion = newVersion;
      }
    }
  }
}

// Check for updated extender and relay firmware
void checkForUpdates() {
  busy = true;
  if (updateCheck) {
    updateCheck = false;
    String serverURL = "http://" + host_server + "/extender/version";
    Serial.println("Check for update at " + serverURL);
    String response = httpGET(serverURL.c_str());
    response.trim();
    int newVersion = response.toInt();
    if (newVersion == 0) {
      Serial.println("Bad response from host, so restarting");
      delay(10000);  // Bad response so restart
      ESP.restart();
    }
    Serial.printf("Installed version is %d, new version is %d\n", currentVersion, newVersion);
    if (newVersion > currentVersion) {
      Serial.printf("Installing version %d\n", newVersion);
      WiFiClient client;
      ESPhttpUpdate.update("http://" + host_server + "/extender/binary");
    } else {
      checkRelayUpdate();
//      listAllFiles();
    }
  }
  busy = false;
}

// List all the SPIFFS files
void listAllFiles(){
 
  File root = SPIFFS.open("/");
  File file = root.openNextFile();
  while (file) {
      Serial.printf("FILE: %s %s\n", file.name(), file.size());
      file = root.openNextFile();
  }
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
//  preferences.putString("softap_ssid", "");
//  SPIFFS.format();

//  listAllFiles();

  softap_ssid = "RBR-EX-000000";
  String mac = WiFi.macAddress();
  Serial.println(mac);
  softap_ssid[7] = mac[9];
  softap_ssid[8] = mac[10];
  softap_ssid[9] = mac[12];
  softap_ssid[10] = mac[13];
  softap_ssid[11] = mac[15];
  softap_ssid[12] = mac[16];
  Serial.printf("SSID: %s\n", softap_ssid.c_str());

  // Set up the soft AP
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  delay(100);
  Serial.println("Read preferences");
  host_ssid = preferences.getString("host_ssid");
  host_password = preferences.getString("host_password");
  softap_password = preferences.getString("softap_password");
  host_ipaddr = preferences.getString("host_ipaddr");
  host_gateway = preferences.getString("host_gateway");
  host_server = preferences.getString("host_server");
  Serial.println("host_ssid = " + host_ssid);
  Serial.println("host_password = " + host_password);
  Serial.println("softap_password = " + softap_password);
  Serial.println("host_ipaddr = " + host_ipaddr);
  Serial.println("host_gateway = " + host_gateway);
  Serial.println("host_server = " + host_server);
  if (host_ssid == "" || host_password == "" || softap_password == ""
    || host_ipaddr == "" || host_gateway == "" || host_server == "") {
    WiFi.softAP(softap_ssid);
    Serial.printf("Soft AP %s created with IP ", softap_ssid); Serial.println(WiFi.softAPIP());
  
    localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
      Serial.println("onAPDefault");
      request->send(200, "text/plain", softap_ssid + " in unconfigured mode");
    });

    localServer.on("/setup", HTTP_GET, [](AsyncWebServerRequest *request) {
      handle_setup(request);
    });

    localServer.onNotFound([](AsyncWebServerRequest *request) {
      request->send(404, "text/plain", "The content you are looking for was not found.");
    });

    localServer.begin();
    Serial.println(softap_ssid + " not configured");
  } else {
    setupNetwork();
    Serial.println(softap_ssid + " configured and running");
  }
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop(void) {
  if (busy) {
    return;
  }
  if (relayId > 0) {
    String deviceURL = deviceRoot + relayId;
    if (relayType == "shelly") {
      deviceURL += "/relay/0?turn=";
    } else {
      deviceURL += "/";
    }
    if (relayState) {
      deviceURL += "on";
    } else {
      deviceURL += "off";
    }
    relayId = 0;
    Serial.println("GET " + deviceURL);
    String response = httpGET(deviceURL.c_str());
    Serial.println(response);
  }

  if (relayVersionRequest) {
    relayVersionRequest->send(200, "text/plain", ((String)relayVersion).c_str());
    relayVersionRequest = 0;
  }

  if (relayUpdateRequest) {
    relayUpdateRequest->send(SPIFFS, "/relay.bin", "application/octet");
    Serial.print("Relay code sent to ");
    Serial.println(relayUpdateRequest->client()->remoteIP());
    relayUpdateRequest = 0;
  }

  checkForUpdates();
}