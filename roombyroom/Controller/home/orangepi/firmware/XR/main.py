<<<<<<< HEAD
import os,time,state
=======
import network
import espnow
import time
from ubinascii import hexlify, unhexlify
from machine import Pin,reset
>>>>>>> refs/remotes/origin/main

sta = network.WLAN(network.STA_IF)
sta.active(True)
mac = sta.config('mac')
print("MAC Address:", hexlify(mac).decode('utf-8'))

<<<<<<< HEAD
def fileExists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

if fileExists('config.json'):
    if fileExists('update'):
        f = open('update','r')
        value=f.read()
        f.close()
        try:
            print('main: Update to version',value)
            time.sleep(2)
            import updater
            updater.run(value)
        except Exception as e:
            state.restart(str(e))

    else:
        try:
            import configured
            print('main: Run configured')
            time.sleep(2)
            configured.run()
        except Exception as e:
            state.restart(str(e))

else:
    print('main: Run unconfigured')
    time.sleep(2)
    import unconfigured
    unconfigured.run()
=======
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
>>>>>>> refs/remotes/origin/main
