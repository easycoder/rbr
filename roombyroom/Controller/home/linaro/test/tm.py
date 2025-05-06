import network
import espnow
import time
from machine import Pin
        
###################################################################
# Main program
# Set up the network
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.config(channel=11)
mac = sta.config('mac')
print('\n\nMAC Address:', mac)
    
# Start ESP-NOW
esp = espnow.ESPNow()
esp.active(True)

# Add an ESP-NOW peer (another ESP32)
# Use its MAC address.
# Each device prints this on startup.
peer = b'\x9c\x9en\x0b\xa9T'
esp.add_peer(peer)

while True:
    print('ON')
    print(esp.send(peer, 'ON'))
    time.sleep(1)
    print('OFF')
    print(esp.send(peer, 'OFF'))
    time.sleep(1)
