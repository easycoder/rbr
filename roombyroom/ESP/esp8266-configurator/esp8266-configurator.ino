// RBR Configurator

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <Ticker.h>

#define CURRENT_VERSION 1
#define BAUDRATE 115200
#define UPDATE_CHECK_INTERVAL 3600

// Constants
const IPAddress localIP(192,168,23,1);
const IPAddress subnet(255,255,255,0);

Ticker ticker;
ESP8266WebServer localServer(80);
DynamicJsonDocument config(256);

uint8_t ledPin = 2;
bool checkForUpdate = false;
char name[40];
char softap_ssid[40];
char httpResponse[10240];
char requestVersionURL[40];  // the URL of the request for the firmware version number
char requestUpdateURL[40];   // the URL of the update firmware binary

///////////////////////////////////////////////////////////////////////////////
// Standard stuff here.

// Check if an update is available
void updateCheck() {
  checkForUpdate = true;
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
    char* empty = (char*)malloc(1);
    empty[0] = '\0';
    return empty;
  }
  size_t filesize = file.size();
  char* text = new char[filesize + 1];
  String data = file.readString();
  file.close();
  strcpy(text, data.c_str());
  return text;
}

void blink()
{
  digitalWrite(ledPin, LOW);
  delay(100);
  digitalWrite(ledPin, HIGH);
  delay(100);
  digitalWrite(ledPin, LOW);
  delay(100);
  digitalWrite(ledPin, HIGH);
}

// Restart the system
void restart() {
  delay(10000);
  ESP.reset();
}

// Reset the system
void doFactoryReset() {
  Serial.print("Factory Reset");
  localServer.send(200, "text/plain", "Factory Reset");
  writeTextToFile("/config", "");
  restart();
}

// Perform a GET
void httpGET(const char* serverName) {
  WiFiClient client;
  HTTPClient http;
    
  http.begin(client, serverName);

  String payload = "";
  
  // Send HTTP GET request
  int httpResponseCode = http.GET();
  Serial.printf("URL: %s, Response: %d\n", serverName, httpResponseCode);
  if (httpResponseCode < 0) {
    Serial.printf("Error: %s\n", http.errorToString(httpResponseCode).c_str());
  } else {
    if (httpResponseCode >= 200 && httpResponseCode < 400) {
      payload = http.getString();
    }
    else {
      Serial.printf("Error code: %d\n", httpResponseCode);
      //restart();
    }
  }
  // Free resources
  http.end();

  payload.trim();
  strcpy(httpResponse, payload.c_str());
}

///////////////////////////////////////////////////////////////////////////////
// Start here
void setup() {
  Serial.begin(BAUDRATE);
  delay(500);
  Serial.printf("\nFlash size: %d\n",ESP.getFlashChipRealSize());
  Serial.printf("Version: %d\n",CURRENT_VERSION);

  if (!LittleFS.begin()){
    LittleFS.format();
    restart();
  }

//  writeTextToFile("/config", "");

  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, HIGH);

  buildSSID();

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPConfig(localIP, localIP, subnet);
  WiFi.softAP(softap_ssid);
  delay(100);

  appSpecificSetup();

  localServer.on("/reset", doFactoryReset);
  localServer.onNotFound(notFound);
  localServer.begin();

  ticker.attach(2, blink);
  completeSetup();
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop() {
  localServer.handleClient();

  if (checkForUpdate && requestVersionURL) {
    checkForUpdate = false;
    Serial.printf("Check for update at %s\n", requestVersionURL);
    httpGET(requestVersionURL);
    int newVersion = atoi(httpResponse);
    Serial.printf("Version %d is available\n", newVersion);
    if (newVersion > CURRENT_VERSION) {
      WiFiClient client;
      Serial.printf("Installing version %d from %s\n", newVersion, requestUpdateURL);
      t_httpUpdate_return ret = ESPhttpUpdate.update(client, requestUpdateURL);
      switch (ret) {
        case HTTP_UPDATE_FAILED:
           Serial.println("Update failed");
           break;
        case HTTP_UPDATE_NO_UPDATES:
           Serial.println("No update took place");
           break;
      }
    } else {
      Serial.println("Firmware is up to date");
    }
  }
}

///////////////////////////////////////////////////////////////////////////////
// This is the application-specific code.

const char* host_ssid = "VM7203527";
const char* host_password = "5sftqwRWvwwv";
const IPAddress ipaddr(192,168,0,80);
const IPAddress gateway(192,168,0,1);

// Build the SoftAp SSID
void buildSSID() {
  String mac = WiFi.macAddress();
  Serial.println("MAC: " + mac);
  String ssid = "RBR-CF-XXXXXX";
  ssid[7] = mac[9];
  ssid[8] = mac[10];
  ssid[9] = mac[12];
  ssid[10] = mac[13];
  ssid[11] = mac[15];
  ssid[12] = mac[16];
  strcpy(softap_ssid, ssid.c_str());
  Serial.printf("SoftAP SSID: %s\n", softap_ssid);
}

// Set up endpoints for this application and do any other special setup that's needed.
void appSpecificSetup() {
  if (!WiFi.config(ipaddr, gateway, subnet)) {
    Serial.println("STA failed to configure");
  }
  WiFi.begin(host_ssid, host_password);

  // Check we are connected to wifi network
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.printf("\nConnected to %s as %s\n", host_ssid, WiFi.localIP().toString().c_str());
  delay(100);

  // Set up endpoints
  localServer.on("/", onDefault);
  localServer.on("/info", onInfo);
  localServer.on("/scan", onScan);
  localServer.on("/get", onGet);
}

// Complete the setup
void completeSetup() {
//  doScan();
}

// Scan networks
void onScan() {
  Serial.println("Scan start");
  // WiFi.scanNetworks will return the number of networks found
  int n = WiFi.scanNetworks();
  Serial.println("Scan done");
  
  if (n == 0)
  {
    Serial.println("no networks found");
  }
  else
  {
    int rlen = 20;
    char* networks = (char*)malloc((n * rlen) * sizeof(char));
      int count = 0;
      for (int i = 0; i < n; ++i) {
        if (strstr(WiFi.SSID(i).c_str(), "RBR-EX-")) {
          strcpy(&networks[i * rlen], WiFi.SSID(i).c_str());
          count = count + 1;
        } else {
          networks[i * rlen] = '\0';
        }
      }
    Serial.printf("%d extender(s) found\n", count);
    delay(10);
    if (count > 0) {
      int* indices = (int*)malloc(count * sizeof(int));
      count = 0;
      for (int i = 0; i < n; i++) {
        if (networks[i * rlen] != '\0') {
          indices[count] = i;
          count = count + 1;
        }
      }
      for (int i = 0; i < count; i++) {
        printf("%s\n", &networks[indices[i] * rlen]);
      }
      free(indices);
      delay(10);
    }
    free(networks);
  }
  localServer.send(200, "text/plain", "OK");
}

// The default page
void onDefault() {
  Serial.println("onAPDefault");
  String homePage = "<html><head></head>";
  homePage += "<body>";
  homePage += "<p>Hello, world!</p>";
  homePage += "</body></html>";
//String request = String("http://192.168.0.201/config.html");
//  httpGET(request.c_str());
  Serial.println(homePage);
  localServer.send(200, "text/html", homePage);
}

// The info page
void onInfo() {
  Serial.println("onInfo");
  localServer.send(200, "text/plain", "RBR configurator " + String(softap_ssid));
}

// The get page
void onGet() {
  String url = localServer.arg("url"); 
  Serial.printf("onGet %s\n", url.c_str());
  httpGET(url.c_str());
  Serial.println(httpResponse);
  localServer.send(200, "text/plain", httpResponse);
}