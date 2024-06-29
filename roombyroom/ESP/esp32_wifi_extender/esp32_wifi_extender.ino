// Wifi extender

#include <WiFi.h>
#include <WiFiClient.h>
#include <ESPAsyncWebServer.h>
#include <ESP32httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 45
#define DEBUG 0    // set to 1 to debug

#if DEBUG
#define serial_begin(...)   Serial.begin(__VA_ARGS__);
#define serial_available()  Serial.available()
#define serial_readString() Serial.readString()
#define debug(...)          Serial.print(__VA_ARGS__)
#define debugf(...)         Serial.printf(__VA_ARGS__)
#define debugln(...)        Serial.println(__VA_ARGS__)
#else
#define serial_begin(...)
#define serial_available()  false
#define serial_readString() ""
#define debug(...)
#define debugf(...)
#define debugln(...)
#endif

#define BAUDRATE 115200
#define POLL_INTERVAL 10
#define ReBOOT_INTERVAL 
#define RESET_INTERVAL 3600
#define RELAY_COUNT 10
#define RELAY_DELAY 50
#define RELAY_ERROR_LIMIT 100
#define HOST_ERROR_LIMIT 10
#define POLL_BUSY_LIMIT 10
#define ERROR_MAX 100
#define FORMAT_LITTLEFS_IF_FAILED true
#define LED_PIN 2
#define RELAY_REQ_IDLE 0
#define RELAY_REQ_REQ 1
#define RELAY_REQ_ACTIVE 2

struct rdata {
    char type[8];
    bool onoff;
    uint errors;
    uint state;
    bool ok;
    char response[256];
};

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
struct rdata relayData[RELAY_COUNT];
uint totalErrors;
uint errorCount = 0;
uint relayVersion = 0;
uint logLevel = 0;
uint rid = 0;
bool busyStartingUp = true;
bool busyGettingUpdates = false;
bool busyDoingGET = false;
bool busyPolling = false;
bool busyDoingRelay = false;
bool running = false;
bool relayFlag = false;
char info[80];
char deviceURL[40];
char restarts[10];
int pollCount = 0;
int pollBusyCount = 0;
int httpResponseCode;
char results[1000];
String commandString;
String httpPayload;

Ticker pollTicker;
Ticker resetTicker;

AsyncWebServer localServer(80);

 #ifdef __cplusplus
  extern "C" {
 #endif

  uint8_t temprature_sens_read();

#ifdef __cplusplus
}
#endif

///////////////////////////////////////////////////////////////////////////////////////////////////
// Perform a GET
char* httpGET(char* requestURL, bool restartOnError = false) {
  if (logLevel == 3) {
    debugf("GET %s\n", requestURL);
  }
  busyDoingGET = true;
  WiFiClient client;
  HTTPClient http;
  char* response;

  http.begin(client, requestURL);

  // Send HTTP GET request
  httpResponseCode = http.GET();
  if (logLevel >= 3) {
    debugf("Response code %d, %d errors\n", httpResponseCode, errorCount);
  }
  if (httpResponseCode >= 200 && httpResponseCode < 400) {  // Happy flow
    httpPayload = http.getString();
    if (logLevel == 3) {
      debugf("Payload length: %d\n", httpPayload.length());
    }
    response = (char*)malloc(httpPayload.length() + 1);
    strcpy(response, httpPayload.c_str());
    // errorCount = 0;
  }
  else {  // Here if an error occurred
    if (restartOnError) {
      debugf("%s\nNetwork error %d\n", requestURL, httpResponseCode);
      reset();
    } else {
      if (logLevel > 1) {
        debugf("%s\nNetwork error %d (%d)\n", requestURL, httpResponseCode, errorCount);
      }
      if (++errorCount > ERROR_MAX) {
        reset();
      }
    }
    response = (char*)malloc(1);  // Provide something to 'free'
    response[0] = '\0';
  }
  if (logLevel == 3) {
    debugf("Response: %s\n", response);
  }
  // Free resources
  http.end();
  client.stop();
  busyDoingGET = false;
  return response;
}

///////////////////////////////////////////////////////////////////////////////////////////////////
int httpPost(char* requestURL, char* requestData) {
  if(WiFi.status()== WL_CONNECTED){
    WiFiClient client;
    HTTPClient http;
  
    // Your Domain name with URL path or IP address with path
    http.begin(client, requestURL);
    
    // Specify content-type header
    http.addHeader("Content-Type", "application/json");        
    // Send HTTP POST request
    int httpResponseCode = http.POST(requestData);
    
       // Free resources
    http.end();
  }
  else {
    debugln("WiFi Disconnected");
  }
  return httpResponseCode;
}

///////////////////////////////////////////////////////////////////////////////////////////////////
void reportError(const char* message) {
  char request[80];
  sprintf(request, "http://%s/resources/php/rest.php/error/%s", host_server, message);
  int httpResponseCode = httpPost(request, results);
}

///////////////////////////////////////////////////////////////////////////////////////////////////
void ledOn() {
  digitalWrite(LED_PIN, HIGH);
}

///////////////////////////////////////////////////////////////////////////////////////////////////
void ledOff() {
  digitalWrite(LED_PIN, LOW);
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Write text to a LittleFS file
void writeTextToFile(const char* filename, const char* text) {
  auto file = LittleFS.open(filename, "w");
  file.print(text);
  delay(10);
  file.close();
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Read a LittleFS file into text
const char* readFileToText(const char* filename) {
  auto file = LittleFS.open(filename, "r");
  if (!file) {
    if (logLevel >= 2) {
      debugln("file open failed");
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

///////////////////////////////////////////////////////////////////////////////////////////////////
// Do a regular poll to get relay data
void poll() {
  if (busyPolling) {
    ++pollBusyCount;
    if (pollBusyCount == POLL_BUSY_LIMIT) {
      reportError("Poll busy limit reached");
      reset();
    }
    return;
  }
  pollBusyCount = 0;
  busyPolling = true;
  // Count the number of relay errors. If more than the limit, reset.
  totalErrors = errorCount;
  for (int n = 0; n < RELAY_COUNT; n++) {
    totalErrors += relayData[n].errors;
  }
  if (totalErrors > RELAY_ERROR_LIMIT) {
    debugln("Too many relay errors");
    reportError("Too many relay errors");
    reset();
  }
  int mem = esp_get_free_heap_size();
  if (mem < 10000) {
    reportError("Heap space too low");
    reset();
  }
  debugf("\nPoll %d: Mem %d, errors %d\n", ++pollCount, mem, totalErrors);

  // Poll the system controller. Reset if no reply
  char request[80];
  sprintf(request, "http://%s/resources/php/rest.php/relaydata/%d/%d", host_server, mem, errorCount);
  char* response = httpGET(request, false);
  // debugf("%s\n", response);
  const int capacity = JSON_OBJECT_SIZE(RELAY_COUNT) + RELAY_COUNT*JSON_OBJECT_SIZE(6);
  StaticJsonDocument<capacity> relaySpec;
  DeserializationError error = deserializeJson(relaySpec, response);
  if (error) {
    // debugf("Invalid relay data: %s\n", response);
    busyPolling = false;
    return;
  }
  free(response);

  // debugln("Iterate the relays");
  JsonArray array = relaySpec.as<JsonArray>();
  for (JsonVariant v : array) {
    JsonObject obj = v.as<JsonObject>();
    const char* extender = obj["extender"];
    if (strcmp(extender, &host_ipaddr[9]) == 0) {
      const char* ip = obj["ip"];
      int id = atoi(ip) - 100;
      if (id < RELAY_COUNT) {
        const char* type = obj["type"];
        strcpy(relayData[id].type, type);
        const char* onoff = obj["onoff"];
        relayData[id].onoff = strcmp(onoff, "on") == 0;
        if (logLevel >= 3) {
            debugf("%s %d %s ", (const char*)obj["type"], id, onoff);
        }
        relayData[id].state = RELAY_REQ_REQ;
      }
    }
  }
  relaySpec.clear();
  busyPolling = false;
}

///////////////////////////////////////////////////////////////////////////////////////////////////
char* getUnconfiguredStatus() {
  int temperature = (int)round((temprature_sens_read() - 32) / 1.8);
  strcpy(info, (String(softap_ssid) + " unconfigured; temp=" + temperature).c_str());
  return info;
}

///////////////////////////////////////////////////////////////////////////////////////////////////
char* getConfiguredStatus() {
  int temperature = (int)round((temprature_sens_read() - 32) / 1.8);
  sprintf(info, "RBR WiFi extender v%d %s/%s Temp:%d Restarts:%s", CURRENT_VERSION, host_ssid, host_ipaddr, temperature, restarts);
  return info;
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Endpoint: GET http://{ipaddr}/reset
void handle_reset(AsyncWebServerRequest *request) {
  debugln("Endpoint: reset");
  reset();
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Reset the system
void reset() {
  debugln("Forcing a reset...");
  WiFi.softAPdisconnect(true);
  delay(10);
  // writeTextToFile("/restart", "Y"); // What's this for (3/12/23)?
  ESP.restart();
  // while (1) {} // force watchdog timer reboot
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Reset the system periodically
void regularReset() {
  reportError("Regular reset (this is not an error)");
  reset();
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Endpoint: GET http://{ipaddr}/factory-reset
void handle_factory_reset(AsyncWebServerRequest *request) {
  debugln("Endpoint: factory-reset");
  writeTextToFile("/config", "");
  request->send(200, "text/plain", "Factory reset");
  reset();
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Print the current status
void printStatus(char* info) {
  int temperature = (int)round((temprature_sens_read() - 32) / 1.8);
  sprintf(info, "RBR WiFi extender v%d %s/%s Temp:%d Restarts:%s", CURRENT_VERSION, host_ssid, host_ipaddr, temperature, restarts);
  debugln(info);
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Endpoint: GET http://{ipaddr}/
void handle_default(AsyncWebServerRequest *request) {
  char info[200];
  printStatus(info);
  request->send(200, "text/plain", info);
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Endpoint: GET http://{ipaddr}/setup?(params)
void handle_setup(AsyncWebServerRequest *request) {
  debugln("handle_setup");
  request->send(200, "text/plain", "OK");

  if(request->hasParam("config")) {
    AsyncWebParameter* p = request->getParam("config");
    String config = p->value();
    debug(config);
    writeTextToFile("/config", config.c_str());
    ESP.restart();
  }
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Set the log level
void setLogLevel(AsyncWebServerRequest *request, int level) {
  setTheLogLevel(level);
  request->send(200, "text/plain", String(logLevel));
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Set the log level
void setTheLogLevel(int level) {
  debugf("Set the log level to %d\n", level);
  logLevel = level;
  char buf[10];
  sprintf(buf, "%d", logLevel);
  writeTextToFile("/logLevel", buf);
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Show the on-off state of a relay
void showState(AsyncWebServerRequest *request, uint id) {
  const char* onoff = relayData[id].onoff ? "OK" : "FAIL";
  if (logLevel >= 3) {
    debugf("Relay %d status: %s\n", id, onoff);
  }
  request->send(200, "text/plain", onoff);
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Set up the network and the local server
void setupNetwork() {
  debugf("Network SSID: %s\nNetwork password: %s\nSoft AP SSID: %s\nSoft AP password: %s\nHost ipaddr: %s\nHost gateway: %s\nHost server: %s\n",
    host_ssid, host_password, softap_ssid, softap_password, host_ipaddr, host_gateway, host_server);

  ipaddr.fromString(host_ipaddr);
  if (!ipaddr) {
    debugln("UnParsable IP '" + String(host_ipaddr) + "'");
    reset();
  }
  gateway.fromString(host_gateway);
  if (!gateway) {
    debugln("UnParsable IP '" + String(host_gateway) + "'");
    reset();
  }
  server.fromString(host_server);
  if (!server) {
    debugln("UnParsable IP '" + String(host_server) + "'");
    reset();
  }

  setupHotspot();
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Set up the local hotspot and connect to the host
void setupHotspot() {
  // Set up the soft AP with up to 10 connections
  WiFi.softAP(softap_ssid, softap_password, 1, 0, 10);
  debugf("Soft AP %s/%s created with IP %s\n", softap_ssid, softap_password, WiFi.softAPIP().toString().c_str());

  //connect to the controller's wi-fi network
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    debugln("STA failed to configure");
  }
  WiFi.begin(host_ssid, host_password);
  debugf("Connecting to %s", host_ssid);
  int counter = 0;
  while (WiFi.status() != WL_CONNECTED) {
    if (++counter > 60) {
      reset();
    }
    debug(".");
    delay(1000);
  }
  debugf("\nConnected as %s with RSSI %d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  delay(100);

  // Set up the local HTTP server
  debugln("Set up the local server");

  localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    handle_default(request);
  });

  localServer.on("/clear", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain", String(restarts));
    strcpy(restarts, "0");
    writeTextToFile("/restarts", restarts);
    handle_default(request);
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

  localServer.on("/status", HTTP_GET, [](AsyncWebServerRequest *request) {
     AsyncWebParameter* p = request->getParam("id");
      const char* id_s = p->value().c_str();
      uint id = atoi(id_s) - 100;
      showState(request, id);
  });

  localServer.on("/relay/version", HTTP_GET, [](AsyncWebServerRequest *request) {
    debugf("Version request from %s\n", request->client()->remoteIP().toString().c_str());
    request->send(200, "text/plain", ((String)relayVersion).c_str());
    debugf("Version %d sent\n", relayVersion);
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

  // Poll the controller regularly
  pollTicker.attach(POLL_INTERVAL, poll);

  // Reset regularly
  resetTicker.attach(RESET_INTERVAL, regularReset);
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Check for updated extender and relay firmware
void checkForUpdates() {
  busyGettingUpdates = true;

  if (logLevel >= 1) {
    debugln("Check for update");
  }
  WiFiClient client;
  char request[80];
  sprintf(request, "http://%s/extender/version", host_server);
  delay(10);
  char* httpPayload = httpGET(request, true);
  int newVersion = atoi(httpPayload);
  free(httpPayload);
  if (newVersion == 0) {
    if (errorCount > HOST_ERROR_LIMIT) {
      debugln("Too many host comms errors, so resetting");
      reportError("Too many host comms errors");
      reset();
    }
  } else {
    if (newVersion > CURRENT_VERSION) {
      debugf("Updating from %d to %d\n\n\n", CURRENT_VERSION, newVersion);
      writeTextToFile("/restarts", "0");
      WiFiClient client;
      sprintf(request, "http://%s/extender/esp32_wifi_extender.ino.bin", host_server);
      ESPhttpUpdate.update(request);
      // This is never reached
    } else {
      debugf("Firmware version %d\n", CURRENT_VERSION);
    }
  }
  // Get the relay version number
  char url[40];
  sprintf(url, "http://%s/relay/version", host_server);
  httpPayload = httpGET(url, true);
  relayVersion = atoi(httpPayload);
  free(httpPayload);
  debugf("Relay version %d\n", relayVersion);
  if (relayVersion == 0) {
    reportError("Unable to get relay version");
    reset();
  }
  busyGettingUpdates = false;
}

///////////////////////////////////////////////////////////////////////////////////////////////////
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

///////////////////////////////////////////////////////////////////////////////////////////////////
// Process a message from the serial port (development only)
void processMessage(const char* msg) {
  char* message = (char*)malloc(strlen(msg) + 1);
  strcpy(message, msg);
  if (strcmp(message, "ping") == 0) {
    debugln("ping OK");
  }
  else if (strcmp(message, "clear") == 0) {
    debugln("clear");
    strcpy(restarts, "0");
    writeTextToFile("/restarts", restarts);
    char info[200];
    printStatus(info);
  }
  else if (strcmp(message, "blink") == 0) {
    debugln("blink");
    blink();
  }
  else if (strcmp(message, "reset") == 0) {
    reset();
  }
  else if (strcmp(message, "factory-reset") == 0) {
    writeTextToFile("/config", "");
    reset();
  }
  else {
    char* ptr = strchr(message, '=');
    if (ptr == NULL) {
      if (busyStartingUp) {
        debugf("%s\n", getUnconfiguredStatus());
      } else {
        debugf("%s\n", getConfiguredStatus());
      }
    }
    else {
      *ptr = '\0';
      ptr++;
      // debugf("%s %s\n", message, ptr);
      if (strcmp(message, "log") == 0) {
        setTheLogLevel(atoi(ptr));
      }
    }
  }
  free(message);

/*  
  localServer.on("/onoff", HTTP_GET, [](AsyncWebServerRequest *request) {
    doOnOff(request);
  });

  localServer.on("/relay/version", HTTP_GET, [](AsyncWebServerRequest *request) {
    debugf("Version request from %s\n", request->client()->remoteIP().toString().c_str());
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

///////////////////////////////////////////////////////////////////////////////////////////////////
// Start here
void setup(void) {
  busyStartingUp = true;

  debugln("setup");
  serial_begin(BAUDRATE);
  delay(500);
  pinMode(LED_PIN, OUTPUT);
  ledOff();

  if (!LittleFS.begin(FORMAT_LITTLEFS_IF_FAILED)){
    debugln("LITTLEFS begin Failed");
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
    debugln("Reboot requested");
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

  // Init the relay flags
  debugln("Init relays");
  for (uint n = 0; n < RELAY_COUNT; n++) {
    relayData[n].state = RELAY_REQ_IDLE;
    relayData[n].errors = 0;
  }

//  Uncomment the next line to force a return to unconfigured mode
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
  debugf("\n\n\nMAC: %s, SSID: %s\n", mac.c_str(), String(softap_ssid));
  debugf("Version %d: Restarts: %d\n", CURRENT_VERSION, nRestarts);

  // Set up the soft AP
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  delay(100);
  debugln("Read config from LittleFS/config");
  const char* config_s = readFileToText("/config");
  if (config_s[0] != '\0') {
    StaticJsonDocument<400> config;
    DeserializationError error = deserializeJson(config, config_s);
    if (error) {
      debugf("Config = %s\n", config_s);
      debugln("Not valid JSON");
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
    debugln("Missing config data");
    softap_ssid[4] = 'e';
    softap_ssid[5] = 'x';
    WiFi.softAP(softap_ssid);
    debugf("Soft AP %s created with IP ", softap_ssid); debugln(WiFi.softAPIP());

    localServer.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
      debugln("onAPDefault");
      request->send(200, "text/plain", getUnconfiguredStatus());
    });

    localServer.on("/setup", HTTP_GET, [](AsyncWebServerRequest *request) {
      handle_setup(request);
    });

    localServer.onNotFound([](AsyncWebServerRequest *request) {
      request->send(404, "text/plain", "The content you are looking for was not found.");
    });

    localServer.begin();
    debugln(getUnconfiguredStatus());

    resetTicker.attach(2, blink);
  } else {
    // Here if we are already configured
    setupNetwork();
    busyStartingUp = false;
  }

  checkForUpdates();
}

///////////////////////////////////////////////////////////////////////////////////////////////////
// Main loop
void loop(void) {

  if (busyStartingUp || busyGettingUpdates || busyDoingGET || busyPolling || busyDoingRelay) {
    return;
  }

  busyDoingRelay = true;
  // Examine the info for the next relay and send a command if its request flag is set
  if (relayData[rid].state == RELAY_REQ_REQ) {
    if (logLevel >= 2) {
      debugf("Process relay %d\n", rid);
    }
    relayData[rid].state = RELAY_REQ_ACTIVE;
    uint id = rid + 100;
    strcpy(deviceURL, deviceRoot);
    char command[30];
    char onoff[4];
    strcpy(onoff, relayData[rid].onoff ? "on" : "off");
    if (strcmp(relayData[rid].type, "r1") == 0) {
      sprintf(command, "/%s", onoff);
    } else if (strcmp(relayData[rid].type, "tasmota") == 0) {
      sprintf(command, "/cm?cmnd=power%%20%s", onoff);
    } else if (strcmp(relayData[rid].type, "shelly") == 0) {
      sprintf(command, "/relay/0?turn=%s", onoff);
    }
    sprintf(deviceURL, "%s%d%s", deviceRoot, id, command);
    if (logLevel >= 3) {
      debugln(deviceURL);
    }
    char* httpResponse = httpGET(deviceURL, false);
    char response[256];
    strncpy(response, httpResponse, 255);
    response[255] = '\0';
    free(httpResponse);

    // If no response, bump the error count
    if (strlen(response) == 0) {
      relayData[rid].ok = false;
      relayData[rid].errors++;
      if (logLevel >= 1) {
        debugf("No response from relay %d (%d)\n", rid, relayData[rid].errors);
      }
    } else {
      relayData[rid].errors = 0;
      // Check the return value for each relay type
      // debugf("Response: %s\n", response);
      if (strcmp(relayData[rid].type, "r1") == 0) {
        char buf[3];
        strncpy(buf, response, 2);
        buf[2] = '\0';
        relayData[rid].ok =  (relayData[rid].onoff && strcmp(buf, "ON") == 0)
          || (!relayData[rid].onoff && strcmp(buf, "OF") == 0);
      }
      else if (strcmp(relayData[rid].type, "tasmota") == 0) {
        char buf[3];
        buf[0] = tolower(response[10]);
        buf[1] = tolower(response[11]);
        buf[2] = '\0';
        // debugf("RID=%d state=%s buf='%s'\n", rid, relayData[rid].state ? "on" : "off", buf);
        relayData[rid].ok = (relayData[rid].onoff && strcmp(buf, "on") == 0)
          || (!relayData[rid].onoff && strcmp(buf, "of") == 0);
      }
      else if (strcmp(relayData[rid].type, "shelly") == 0) {
        char buf[5];
        buf[0] = response[8];
        buf[1] = response[9];
        buf[2] = response[10];
        buf[3] = response[11];
        buf[4] = '\0';
        relayData[rid].ok = (relayData[rid].onoff && strcmp(buf, "true") == 0)
          || (!relayData[rid].onoff && strcmp(buf, "fals") == 0);
        // strcpy(response, buf);
      }
      else {
        relayData[rid].ok = false;
        relayData[rid].errors++;
        sprintf(response, "Unknown relay type '%s'", relayData[rid].type);
      }
      debugf("Relay %d: %s %s\n", rid, response, relayData[rid].ok ? "OK" : "FAIL");
    }
    for (int n = 0; n < strlen(response); n++) {
      if (response[n] == '"') {
        response[n] = '\'';
      }
    }
    strcpy(relayData[rid].response, response);
    if (strlen(relayData[rid].response) == 0) {
      strcpy(relayData[rid].response, "<none>");
    }
    delay(10);
    if (logLevel >= 3) {
      debugf("Relay %d: %s - Status: %s\n", rid, deviceURL, deviceURL, response);
    }
    relayData[rid].state = RELAY_REQ_IDLE;
    relayFlag = true; // A relay has been processed
  }
  // After all relays, if any have been processed send a response back
  if (++rid == RELAY_COUNT) {
    if (relayFlag) {
      // char* response = httpGET(deviceURL, false);
      // debugf("%s\n", response);
      const int capacity = JSON_OBJECT_SIZE(RELAY_COUNT) + JSON_OBJECT_SIZE(4) * RELAY_COUNT + 1024;
      StaticJsonDocument<capacity> jsonDoc;
      for (int n = 0; n < RELAY_COUNT; n++) {
        // jsonDoc[n]["type"] = relayData[n].type;
        // jsonDoc[n]["onoff"] = relayData[n].onoff;
        jsonDoc[n]["ip"] = n + 100;
        jsonDoc[n]["errors"] = relayData[n].errors;
        jsonDoc[n]["ok"] = relayData[n].ok;
        jsonDoc[n]["response"] = relayData[n].response;
      }
      char results[1000];
      serializeJson(jsonDoc, results);
      // debugln(results);
      char request[80];
      sprintf(request, "http://%s/resources/php/rest.php/response/%s", host_server, host_ipaddr);
      int httpResponseCode = httpPost(request, results);
      if (logLevel >= 3) {
        debugf("POST response: %d\n", httpResponseCode);
      }
      relayFlag = false;
    }
    rid = 0;
  }
  busyDoingRelay = false;

  // Handle command input
  if (serial_available()) {     //wait for data available
    commandString = serial_readString();  //read until timeout
    commandString.trim();                        // remove any \r \n whitespace at the end of the String
    processMessage(commandString.c_str());
  }

  // Tell the server I've restarted. Do this just once.
  if (!running) {
    running = true;
    char request[80];
    sprintf(request, "http://%s/resources/php/rest.php/ex-restarts/%s", host_server, restarts);
    char* httpPayload = httpGET(request, false);
    free(httpPayload);
    debugf("%s configured and running\n", softap_ssid);
  }
}
