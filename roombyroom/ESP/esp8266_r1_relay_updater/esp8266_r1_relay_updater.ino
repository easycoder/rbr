// RBR R1 relay updater

#include <ESP8266WiFi.h>
#include <ESP8266httpUpdate.h>
#include <LittleFS.h>
#include <ArduinoJson.h>

#define BAUDRATE 115200

DynamicJsonDocument config(256);

uint errorCount = 0;
bool updateFlag = false;
char host_ssid[40];
char host_password[20];
char host_ipaddr[20];
char host_gateway[20];
char host_server[20];
char requestUpdateURL[40];

// Read a LittleFS file into text
const char* readFileToText(const char* filename) {
  auto file = LittleFS.open(filename, "r");
  if (!file) {
    Serial.println("file open failed");
    return "";
  }
  size_t filesize = file.size();
  char* text = new char[filesize + 1];
  String data = file.readString();
  file.close();
  strcpy(text, data.c_str());
  return text;
}

// Restart the system
void restart() {
  Serial.println("Reset");
  delay(10000);
  ESP.reset();
}

// Connect to the controller network and launch the updater
void connectToHost() {
  Serial.printf("host_ssid: %s\n", host_ssid);
  Serial.printf("host_password: %s\n", host_password);
  Serial.printf("host_ipaddr: %s\n", host_ipaddr);
  Serial.printf("host_gateway: %s\n", host_gateway);
  Serial.printf("host_server: %s\n", host_server);

  strcat(requestUpdateURL, "http://");
  strcat(requestUpdateURL, host_server);
  strcat(requestUpdateURL, "/relay/current");

  // Check IP addresses are well-formed

  IPAddress ipaddr;
  IPAddress gateway;
  IPAddress server;

  if (!ipaddr.fromString(host_ipaddr)) {
    Serial.println("Bad IP '" + String(host_ipaddr) + "'");
    restart();
  }

  if (!gateway.fromString(host_gateway)) {
    Serial.println("Bad IP '" + String(host_gateway) + "'");
    restart();
  }

  if (!server.fromString(host_server)) {
    Serial.println("Bad IP '" + String(host_server) + "'");
    restart();
  }

  WiFi.mode(WIFI_STA);

  // Connect to the host
  WiFi.begin(host_ssid, host_password);
  Serial.print("Connecting ");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  Serial.printf("\nConnected to %s as %s\n", host_ssid, WiFi.localIP().toString().c_str());
  delay(100);

  updateFlag = true;
}

///////////////////////////////////////////////////////////////////////////////
// Start here
void setup() {
  Serial.begin(BAUDRATE);
  delay(500);

  if (!LittleFS.begin()){
    LittleFS.format();
    return;
  }

  Serial.println("\n\nRBR R1 updater");
  String config_p = readFileToText("/config");
  if (config_p != "") {
    const char* config_s = config_p.c_str();
    StaticJsonDocument<400> config;
    DeserializationError error = deserializeJson(config, config_s);
    if (error) {
      Serial.println("LittleFS/config is not valid JSON");
      restart();
    } else {
      if (config.containsKey("ssid")) {
        strcpy(host_ssid, config["ssid"]);
      } else {
        host_ssid[0] = '\0';
      }
      if (config.containsKey("password")) {
        strcpy(host_password, config["password"]);
      } else {
        host_password[0] = '\0';
      }
      if (config.containsKey("ipaddr")) {
        strcpy(host_ipaddr, config["ipaddr"]);
      } else {
        host_ipaddr[0] = '\0';
      }
      if (config.containsKey("gateway")) {
        strcpy(host_gateway, config["gateway"]);
      } else {
        host_gateway[0] = '\0';
      }
      if (config.containsKey("server")) {
        strcpy(host_server, config["server"]);
      } else {
        host_server[0] = '\0';
      }
      if (host_ssid[0] == '\0' || host_password[0] == '\0'
      || host_ipaddr[0] == '\0' || host_gateway[0] == '\0' || host_server[0] == '\0') {
        Serial.println("Bad config data");
        restart();
      } else {
        connectToHost();
      }
    }
  } else {
    Serial.println("Bad config data");
    restart();
  }
}

///////////////////////////////////////////////////////////////////////////////
// Main loop
void loop() {
  if (updateFlag) {
    updateFlag = false;
    WiFiClient client;
    Serial.printf("Downloading from %s\n", requestUpdateURL);
    t_httpUpdate_return ret = ESPhttpUpdate.update(client, requestUpdateURL);
    switch (ret) {
      case HTTP_UPDATE_FAILED:
          Serial.println("Update failed");
          break;
      case HTTP_UPDATE_NO_UPDATES:
          Serial.println("No update took place");
          break;
      default:
        // This will never be reached as the device has restarted
        break;
    }
    restart();
  }
}
