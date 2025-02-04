import network
import espnow
from machine import Pin

sta = network.WLAN(network.STA_IF)
sta.active(True)
mac = sta.config('mac')
print('\n\nMAC Address:', mac)

esp = espnow.ESPNow()
esp.active(True)

led = Pin(3, Pin.OUT)

while True:
    _, msg = esp.recv()
    if msg:
        if msg == b'ON':
            led.on()
        elif msg == b'OFF':
            led.off()
        else:
            print('Unknown message')
