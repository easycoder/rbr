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

void badIP(String ipaddr) {
  Serial.println("Bad IP '" + ipaddr + "'");
  restart();
}

// Connect to the controller network and launch the updater
void connectToHost() {
  Serial.printf("%s %s %s\n", host_ssid, host_password, host_ipaddr);

  sprintf(requestUpdateURL, "http://%s/relay/current", host_server);

  // Check IP addresses are well-formed

  IPAddress ipaddr;
  IPAddress gateway;
  IPAddress server;

  if (!ipaddr.fromString(host_ipaddr)) {
    badIP(host_ipaddr);
  }

  if (!gateway.fromString(host_gateway)) {
    badIP(host_gateway);
  }

  if (!server.fromString(host_server)) {
    badIP(host_server);
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
      getConfigValue(config, "ssid", host_ssid);
      getConfigValue(config, "password", host_password);
      getConfigValue(config, "ipaddr", host_ipaddr);
      getConfigValue(config, "gateway", host_gateway);
      getConfigValue(config, "server", host_server);
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

void getConfigValue(StaticJsonDocument<400> config, String name, char* value) {
  if (config.containsKey(name)) {
    strcpy(value, config[name]);
  } else {
    value[0] = '\0';
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
          Serial.println(ESPhttpUpdate.getLastErrorString().c_str());
          restart();
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
