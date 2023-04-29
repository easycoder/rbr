/**
* Test ESP8266 wifi and programming. Will print wifi networks to serial and blink led on pin 13.
 */

#include "Arduino.h"
#include "ESP8266WiFi.h"

#ifndef LED_BUILTIN
#define LED_BUILTIN 13
#endif

void setup()
{
  // initialize LED digital pin as an output.
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(115200);
  
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);
  Serial.println("Setup done");
}


void do_blinking()
{
  // turn the LED on (HIGH is the voltage level)
  bool state = 0;
  
  static const int LOCAL_DELAYS[] = { 200,400,200, 1000 };
  for ( int dloop = 0; dloop < sizeof(LOCAL_DELAYS)/sizeof(int); dloop ++ )
  {
     state = !state;
     digitalWrite(LED_BUILTIN, state);
     // wait for a second
     delay( LOCAL_DELAYS[dloop] );
  }
}


void scan_networks() 
{
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
    Serial.print(n);
    Serial.println(" networks found");
    for (int i = 0; i < n; ++i)
    {
      // Print SSID and RSSI for each network found
      Serial.print(i + 1);
      Serial.print(": ");
      Serial.print(WiFi.SSID(i));
      Serial.print(" (");
      Serial.print(WiFi.RSSI(i));
      Serial.print(")");
      Serial.println((WiFi.encryptionType(i) == ENC_TYPE_NONE)?" ":"*");
      delay(10);
    }
  }
  Serial.println("");
} 
void loop()
{
  
  do_blinking();
  scan_networks();
    
}