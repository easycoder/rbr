// Configurator

#include <WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncWebServer.h>
#include <ESP32httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>

#define CURRENT_VERSION 1
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
bool busyStartingUp = true;
bool busyDoingGET = false;
bool errorCount = false;
char httpPayload[200];
char restarts[10];

AsyncWebServer localServer(80);

// Perform a GET
char* httpGET(char* requestURL, bool restartOnError = false) {
  Serial.printf("%s\n", requestURL);
  busyDoingGET = true;
  WiFiClient client;
  HTTPClient http;
  char* response = "";
    
  http.begin(client, requestURL);

  httpPayload[0] = '\0';
  
  // Send HTTP GET request
  int httpResponseCode = http.GET();
  Serial.printf("%d, %d\n", httpResponseCode, errorCount);
  if (httpResponseCode < 0) {
    Serial.printf("Error: %s\n", http.errorToString(httpResponseCode).c_str());
  } else {
    if (httpResponseCode >= 200 && httpResponseCode < 400) {
      String httpPayload = http.getString();
      Serial.printf("Length: %d\n", httpPayload.length());
      response = (char*)malloc(httpPayload.length() + 1);
      strcpy(response, httpPayload.c_str());
      errorCount = 0;
    }
    else {
      if (restartOnError) {
        Serial.printf("Network error %d\n", httpResponseCode);
        restart();
      } else {
        errorCount = errorCount + 1;
        Serial.printf("Error %d (%d)\n", httpResponseCode, errorCount);
        if (errorCount == ERROR_MAX) {
          restart();
        }
      }
    }
  }
  // Free resources
  http.end();
//  Serial.println(response);
  busyDoingGET = false;
  return response;
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

// Add the standard endpoints used by all applications
void addStandardEndpoints() {
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

  localServer.onNotFound([](AsyncWebServerRequest *request){
    request->send(404, "text/plain", "The content you are looking for was not found.");
  });
}
 
///////////////////////////////////////////////////////////////////////////////
// Start here
void setup(void) {
  Serial.begin(BAUDRATE);
  delay(500);
  Serial.printf("\nVersion: %d\n",CURRENT_VERSION);

  if (!LittleFS.begin(FORMAT_LITTLEFS_IF_FAILED)){
    Serial.println("LITTLEFS begin Failed");
    restart();
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

  doApplicationSetup();
  addStandardEndpoints();
  localServer.begin();
  busyStartingUp = false;
}

// Main loop
void loop(void) {
  if (busyDoingGET) {
    return;
  } else {
    busyDoingGET = false;
  }
  doApplicationLoop();
}

///////////////////////////////////////////////////////////////////////////////
// This is the application-specific code

#define STATE_NONE 0
#define STATE_REQUEST 1
#define STATE_RUNNING 2
#define STATE_DONE 3

int scanState;
String scanResult;
char connect_ssid[20];
char connect_password[20];
char request[80];
char* response = NULL;
bool connect;
bool connected;

void doApplicationSetup() {
  buildSSID();
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  WiFi.softAP(softap_ssid);
  delay(100);

  localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *req) {
    handle_default(req);
  });

  localServer.on("/scan", HTTP_GET, [](AsyncWebServerRequest *req) {
    handle_scan(req);
  });

  localServer.on("/connect", HTTP_GET, [](AsyncWebServerRequest *req) {
    handle_connect(req);
  });

  localServer.on("/connected", HTTP_GET, [](AsyncWebServerRequest *req) {
    handle_connected(req);
  });

  localServer.on("/request", HTTP_GET, [](AsyncWebServerRequest *req) {
    handle_request(req);
  });

  localServer.on("/response", HTTP_GET, [](AsyncWebServerRequest *req) {
    handle_response(req);
  });
  request[0] = NULL;
}

void doApplicationLoop() {
  if (getScanState() == STATE_REQUEST) {
    setScanState(STATE_RUNNING);
    doScan();
    setScanState(STATE_DONE);
  }
  if (connect) {
    connect = false;
    if (connected) {
      WiFi.disconnect();
    }
    //connect to the requested wi-fi network
    WiFi.begin(connect_ssid, connect_password);
    Serial.printf("Connecting to %s", connect_ssid);
    int count = 0;
    while (WiFi.status() != WL_CONNECTED) {
        Serial.print(".");
        delay(100);
        count = count + 1;
        if (count > 40) {
          return;
        }
    }
    Serial.printf("\nConnected to %s as %s with RSSI %d\n", connect_ssid, WiFi.localIP().toString().c_str(), WiFi.RSSI());
    connected = true;
  }
  if (request[0]) {
    char req[80];
    strcpy(req, request);
    request[0] = NULL;
    char* resp = httpGET(req);
    free(response);
    response = resp;
  }
}

void buildSSID() {
  String ssid = "RBR-CF-000000";
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
}

// Endpoint: GET http://{ipaddr}/reset
void handle_default(AsyncWebServerRequest *req) {
  Serial.println("Endpoint: default");
  String homePage = "<html><head></head>";
  homePage += "<body>";
  homePage += "<p>Hello, world!</p>";
  homePage += "</body></html>";
  Serial.println(homePage);
  req->send(200, "text/html", homePage);
}

// Scan networks
void handle_scan(AsyncWebServerRequest *req) {
  Serial.println("Endpoint: scan");

  switch (getScanState()) {
    case STATE_NONE:
      setScanState(STATE_REQUEST);
    case STATE_REQUEST:
    case STATE_RUNNING:
      req->send(200, "text/plain", "");
      break;
    case STATE_DONE:
      setScanState(STATE_NONE);
      req->send(200, "text/plain", scanResult);
      break;
  }
}

// Connect to a server
void handle_connect(AsyncWebServerRequest *req) {
  Serial.println("Endpoint: connect");

  AsyncWebParameter* p = req->getParam("ssid");
  strcpy(connect_ssid, p->value().c_str());
  p = req->getParam("password");
  strcpy(connect_password, p->value().c_str());
  req->send(200, "text/plain", "");
  connect = true;
}

// Return true if connected
void handle_connected(AsyncWebServerRequest *req) {
  Serial.println("Endpoint: connected");

  req->send(200, "text/plain", connected ? "connected" : "");
}

// Make a request
void handle_request(AsyncWebServerRequest *req) {
  Serial.println("Endpoint: request");

  if (connected) {
    AsyncWebParameter* p = req->getParam("req");
    strcpy(request, p->value().c_str());
    response = NULL;
    req->send(200, "text/plain", "OK");
  } else {
    req->send(400, "text/plain", "Not connected");
  }
}

// Get the response from the last request
void handle_response(AsyncWebServerRequest *req) {
  Serial.println("Endpoint: response");

  if (response != NULL) {
    req->send(200, "text/plain", response);
    free(response);
    response = NULL;
  } else {
    req->send(200, "text/plain", "");
  }
}

// Scan the local networks
void doScan() {
  if (connected) {
    WiFi.disconnect();
    delay(10);
  }
//  Serial.println("Scan running ");
  scanResult = "";
  // WiFi.scanNetworks will return the number of networks found
  int n = WiFi.scanNetworks();
  
  String result = "";
  if (n > 0)
  {
    for (int i = 0; i < n; ++i)
    {
      // Get SSID for each network found
      result = result + WiFi.SSID(i) + "\n";
    }
    scanResult = result;
  }
}

void setScanState(int state) {
  scanState = state;
}

int getScanState() {
  return scanState;
}