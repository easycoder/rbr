/*********
Russell Williams
Complete project details at https://RandomNerdTutorials.com  
 File: ESP8266_DS18B20_Webserver_v1.1
*********/

// Import required libraries

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <Hash.h>
#include <ESPAsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

// Variables to store temperature values
String temperatureC = "";

// Setup destination/target server
String RBRserverName = "http://172.24.1.244:8080";

// Replace with your network credentials
const char* ssid = "RBR-803f5da35e86";
const char* password = "r00m8Yr00m";

// Create AsyncWebServer object on port 80
AsyncWebServer server(80);

// the following variables are unsigned longs because the time, measured in
// milliseconds, will quickly become a bigger number than can be stored in an int.
unsigned long lastTime = 0;
// Timer set to 10 minutes (600000)
//unsigned long timerDelay = 600000;
// Set timer to 5 seconds (5000)
unsigned long timerDelay = 5000;

void setup() {
 Serial.begin(115200); 

 WiFi.begin(ssid, password);
 Serial.println("Connecting");
 while(WiFi.status() != WL_CONNECTED) {
  delay(500);
  Serial.print(".");
 }
 Serial.println("");
 Serial.print("Connected to WiFi network with IP Address: ");
 Serial.println(WiFi.localIP());
 
 Serial.println("Timer set to 5 seconds (timerDelay variable), it will take 5 seconds before publishing the first reading.");
}

String readDSTemperatureC() {

 float tempC = 18.9;

 if(tempC == -127.00) {
  Serial.println("Failed to read from DS18B20 sensor");
  return "--";
 } else {
  Serial.print("Temperature Celsius: ");
  Serial.println(tempC); 
 }
 return String(tempC);
}

void loop() {
 // Send an HTTP POST request depending on timerDelay
 if ((millis() - lastTime) > timerDelay) {
  //Check WiFi connection status
  if(WiFi.status()== WL_CONNECTED){
   WiFiClient client;
   HTTPClient http;

   temperatureC = readDSTemperatureC();
   String serverPath = RBRserverName +"/notify?temp=" + temperatureC + "&hum=0";
    
   // Your Domain name with URL path or IP address with path
   http.begin(client, serverPath);

   // Send HTTP GET request
   int httpResponseCode = http.GET();

   Serial.printf("Server Path is: %s\n", serverPath.c_str());
  }
  lastTime = millis();
 }
}