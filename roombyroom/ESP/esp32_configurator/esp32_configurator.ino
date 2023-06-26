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
const IPAddress localIP(192,168,32,1);
const IPAddress subnet(255,255,255,0);
const char* deviceRoot("http://192.168.32.");

char softap_password[40];
bool busyStartingUp = true;
bool busyDoingGET = false;
bool errorCount = false;
char restarts[10];

AsyncWebServer localServer(80);

// Perform a GET
char* httpGET(char* requestURL, bool restartOnError = false) {
//  Serial.printf("GET %s\n", requestURL);
  busyDoingGET = true;
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
    busyDoingGET = false;
    return response;
  } else {
    if (httpResponseCode >= 200 && httpResponseCode < 400) {
      String httpPayload = http.getString();
//      Serial.printf("Payload length: %d\n", httpPayload.length());
      response = (char*)malloc(httpPayload.length() + 1);
      strcpy(response, httpPayload.c_str());
      errorCount = 0;
    }
    else {
      if (restartOnError) {
        Serial.printf("Network error %d; restarting...\n", httpResponseCode);
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
  client.stop();
//  Serial.printf("Response: %s\n", response);
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
    request->send(200, "text/plain", "OK");
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
int connectState;
int requestState;
int postState;
char* scanResult;
char* connectResult;
char* requestResult;
char* postData;
char* postURL;
char connect_ssid[20];
char connect_password[20];
char requestURL[80];
char* response = NULL;
bool connected;

void doApplicationSetup() {
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  WiFi.softAP("RBR-Config");
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

  localServer.on("/request", HTTP_GET, [](AsyncWebServerRequest *req) {
    handle_request(req);
  });

  localServer.on("/post", HTTP_POST, [](AsyncWebServerRequest *req) {
    handle_post(req);
  });

  requestURL[0] = NULL;
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

// Handle a scan
void handle_scan(AsyncWebServerRequest *req) {
  Serial.println("Endpoint: scan");

  switch (scanState) {
    case STATE_NONE:
      scanState = STATE_REQUEST;
    case STATE_REQUEST:
    case STATE_RUNNING:
      req->send(200, "text/plain", "");
      break;
    case STATE_DONE:
      scanState = STATE_NONE;
      req->send(200, "text/plain", scanResult);
      free(scanResult);
      break;
  }
}

// Handle a connection
void handle_connect(AsyncWebServerRequest *req) {
  Serial.println("Endpoint: connect");

  AsyncWebParameter* p = req->getParam("ssid");
  strcpy(connect_ssid, p->value().c_str());
  p = req->getParam("password");
  strcpy(connect_password, p->value().c_str());
  switch (connectState) {
    case STATE_NONE:
      connectState = STATE_REQUEST;
    case STATE_REQUEST:
    case STATE_RUNNING:
      req->send(200, "text/plain", "");
      break;
    case STATE_DONE:
      connectState = STATE_NONE;
      req->send(200, "text/plain", connectResult);
      free(connectResult);
      break;
  }
}

// Handle a request
void handle_request(AsyncWebServerRequest *req) {
  Serial.println("Endpoint: request");

  if (connected) {
    AsyncWebParameter* p = req->getParam("req");
    strcpy(requestURL, p->value().c_str());
    if (response) {
      free(response);
      response = NULL;
    }
    switch (requestState) {
      case STATE_NONE:
        requestState = STATE_REQUEST;
      case STATE_REQUEST:
      case STATE_RUNNING:
        req->send(200, "text/plain", "");
        break;
      case STATE_DONE:
        requestState = STATE_NONE;
        req->send(200, "text/plain", requestResult);
        free(requestResult);
        break;
    }
  } else {
    req->send(400, "text/plain", "Not connected");
  }
}

// Handle a post
void handle_post(AsyncWebServerRequest *req) {
  // Serial.println("Endpoint: post");

  if (connected) {
    // int headers = req->headers();
    // for (int i = 0; i < headers; i++) {
    //   AsyncWebHeader* h = req->getHeader(i);
    //   Serial.printf("_HEADER[%s]: %s\n", h->name().c_str(), h->value().c_str());
    // }

    int params = req->params();
    for (int i = 0; i < params; i++) {
      AsyncWebParameter* p = req->getParam(i);
      int length = p->value().length();
      const char* name = p->name().c_str();
      const char* value = p->value().c_str();
      // Serial.printf("POST[%s]: %s\n", name, value);
      if (strcmp(name, "url") == 0) {
        postURL = (char*)malloc(length + 1);
        strcpy(postURL, value);
      } else if (strcmp(name, "data") == 0) {
        postData = (char*)malloc(length + 1);
        strcpy(postData, value);
      }
      delay(10);
    }
    postState = STATE_REQUEST;
    Serial.println("POST requested");
    req->send_P(200, "text/plain", "OK");
  } else {
    Serial.println("Can't POST - not connected");
    req->send(400, "text/plain", "Not connected");
  }
}

void doApplicationLoop() {
  // Handle a scan
  if (scanState == STATE_REQUEST) {
    scanState = STATE_RUNNING;
    doScan();
    scanState = STATE_DONE;
  }

  // Handle a connect
  if (connectState == STATE_REQUEST) {
    connectState = STATE_RUNNING;
    doConnect();
    connectState = STATE_DONE;
  }

  // Handle a request
  if (requestState == STATE_REQUEST) {
    requestState = STATE_RUNNING;
    doRequest();
    requestState = STATE_DONE;
  }

  // Handle a post
  if (postState == STATE_REQUEST) {
    postState = STATE_RUNNING;
    doPost();
    postState = STATE_NONE;
  }
}

// Scan the local networks
void doScan() {
  if (connected) {
    WiFi.disconnect();
    delay(10);
  }
  Serial.println("Scan running ");
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
    scanResult = (char*)malloc(result.length() + 1);
    strcpy(scanResult, result.c_str());
    Serial.print(scanResult);
  } else {
    Serial.println("No networks");
    restart();
  }
}

// Connect to a network
void doConnect() {
  if (connected) {
    WiFi.disconnect();
    connectState = STATE_NONE;
    connected = false;
  }
  WiFi.begin(connect_ssid, connect_password);
  Serial.printf("Connecting to %s %s", connect_ssid, connect_password);
  int count = 0;
  while (WiFi.status() != WL_CONNECTED) {
      Serial.print(".");
      delay(1000);
      if (++count > 30) {
        Serial.println("Can't connect");
        return;
      }
  }
  Serial.printf("\nConnected to %s as %s with RSSI %d\n", connect_ssid, WiFi.localIP().toString().c_str(), WiFi.RSSI());
  connectResult = (char*)malloc(10);
  strcpy(connectResult, "connected");
  connected = true;
}

// Perform a GET request
void doRequest() {
  Serial.printf("GET from %s\n", requestURL);
  requestResult = httpGET(requestURL);
}

// POST data to a URL
void doPost() {
  Serial.printf("Posting to %s\n", postURL);
  WiFiClient client;
  HTTPClient http;
  http.begin(client, String(postURL));
  http.addHeader("Content-Type", "text/plain");
  int httpResponseCode = http.POST(String(postData));
  if (httpResponseCode >= 0) {
    Serial.printf("POST to %s completed with success\n", requestURL);
  } else {
    Serial.printf("GET %s: POST error: %s\n", requestURL, http.errorToString(httpResponseCode).c_str());
  }
  http.end();
  client.stop();
  free(postURL);
  free(postData);
}