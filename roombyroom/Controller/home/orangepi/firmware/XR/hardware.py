import os
from machine import Pin

led = Pin(2, Pin.OUT)

###################################################################################
def fileExists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

###################################################################################
# Write data to a file
def writeFile(name,value):
#    print(f'Writing {value} to {name}')
    f = open(name, 'w')
    f.write(value)
    f.close()

###################################################################################
# Read data from a file
def readFile(name):
    try:
        f = open(name,'r')
        value=f.read()
        f.close()
    except:
        value=None
    return value

###################################################################################
def setupPins():
    global relay,led
    relay=Pin(0,mode=Pin.OUT)
    led=Pin(2,mode=Pin.OUT)

###################################################################################
def setLED(onoff):
    global led
    led.off() if onoff else led.on()

###################################################################################
def setRelay(onoff):
    global relay
    if fileExists('reverse'):
        relay.off() if onoff=='on' else relay.on()
    else:
        relay.on() if onoff=='on' else relay.off()

###################################################################################
def getRelay():
    global relay
    return 'OFF' if relay.value() else 'ON'
