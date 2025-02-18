import os,asyncio
from machine import Pin

def fileExists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

def readFile(name):
    try:
        f=open(name,'r')
        value=f.read()
        f.close()
    except:
        value=None
    return value

def writeFile(name,text):
    f=open(name,'w')
    f.write(text)
    f.close()

def createDirectory(path):
    try:
        os.mkdir(path)
    except Exception:
        pass

def clearFile(name):
    open(name,'w').close()

def setupLED():
    global led
    if fileExists('led'):
        led=Pin(int(readFile('led')),mode=Pin.OUT)
    else:
        led=Pin(2,mode=Pin.OUT)

def setupRelay():
    global relay
    if fileExists('relay'):
        r=readFile('relay')
        if r=='-':
            relay=None
            return
        r=int(r)
    else:
        r=0
    relay=Pin(r,mode=Pin.OUT)

def setupPins():
    setupLED()
    setupRelay()

def setLED(onoff):
    global led
    if fileExists('ledinv'):
        led.on() if onoff else led.off()
    else:
        led.off() if onoff else led.on()

def setRelay(onoff):
    global relay
    if relay!=None:
        if fileExists('reverse'):
            relay.off() if onoff=='on' else relay.on()
        else:
            relay.on() if onoff=='on' else relay.off()

def hasRelay():
    global relay
    return relay!=None

def getRelay():
    global relay
    if hasRelay():
        if fileExists('reverse'):
            return 'ON' if relay.value() else 'OFF'
        else:
            return 'OFF' if relay.value() else 'ON'

async def blink():
    setLED(True)
    await asyncio.sleep(0.5)
    setLED(False)
    await asyncio.sleep(0.5)
