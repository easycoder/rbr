import network
import espnow
import time
from ubinascii import hexlify, unhexlify
from machine import Pin,reset

sta = network.WLAN(network.STA_IF)
sta.active(True)
mac = sta.config('mac')
print("MAC Address:", hexlify(mac).decode('utf-8'))

esp = espnow.ESPNow()
esp.active(True)

led = Pin(3, Pin.OUT)

while True:
    _, msg = esp.recv()
    if msg:
        print(msg)
        msg = msg.split(' ')
        mac = msg[0]
        msg = msg[1]
        if msg == 'ON':
            print('ON')
            led.on()
        elif msg == 'OFF':
            print('OFF')
            led.off()
        else:
            print(msg)
