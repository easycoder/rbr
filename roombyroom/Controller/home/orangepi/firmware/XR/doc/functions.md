# Functions
A set of helper functions is kept in `functions.py` and `hardware.py`. These are provided as two files to help avoid running out of memory during updates.

A single third-party library, `uaiohttpclient`, which handles asynchronous HTTP requests, is placed in the lib directory.

Here’s the code for `functions.py`:
```
import network,socket,ubinascii,asyncio,time,os,json,machine
import uaiohttpclient as aiohttp
import hardware

myname=None
myssid=None
mypass=None

###################################################################################
def getMyName():
    global myname
    return myname

###################################################################################
def getHostSSID():
    global hostssid
    return hostssid

###################################################################################
def getMySSID():
    global myssid
    return myssid

###################################################################################
def setMyPassword(p):
    global mypass
    mypass=p

###################################################################################
def isPrimary():
    global station
    path=station[2]
    return path=='172.24.1.1'

###################################################################################
def getServer():
    global station
    path=station[2]
    if isPrimary():
        return path+'/resources/php/rest.php/'
    return path

###################################################################################
# Get the configuration data
def getConfigData():
    global myname,hostssid,hostpass,mypass
    if hardware.fileExists('config.json'):
        config=json.loads(hardware.readFile('config.json'))
        myname=config['myname']
        hostssid=config['hostssid']
        hostpass=config['hostpass']
        mypass=config['mypass']
        return (json.dumps(config))
    else:
        print('\nCan\'t load the config file')
        os.remove('config.json')
        time.sleep(1)
        machine.reset()

###################################################################################
# The Access Point
async def setupAP():
    global station,myssid,mypass
    ap = network.WLAN(network.AP_IF)
    myssid = 'RBR-XR-' + ubinascii.hexlify(ap.config('mac')).decode()[6:]
    print('Set up AP for',myssid)
    ap.config(essid=myssid, authmode=3, password=mypass)
    mynet=station[2]
    ip=mynet.split('.')
    if ip[2]=='100':
        ip[2]='101'
    else:
        ip[2]='100'
    myip=ip[0]+'.'+ip[1]+'.'+ip[2]+'.1'
    ap.ifconfig((myip, '255.255.255.0', myip, '8.8.8.8'))
    ap.active(True)

    timeout=60
    while not ap.active():
        await asyncio.sleep(1)
        timeout-=1
        if timeout==0:
            print('\nCan\'t set up AP')
            await asyncio.sleep(1)
            machine.reset()

    print('AP:',ap.ifconfig())

###################################################################################
# Connect to our host
def connect():
    global station,hostssid,hostpass
    print('connect',hostssid)
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(hostssid,hostpass)
    print('Connecting to',hostssid)
    timeout=60
    while sta_if.isconnected()==False:
        time.sleep(1)
        print('.',end='')
        timeout-=1
        if timeout==0:
            print('\nCan\'t connect to',hostssid)
            machine.reset()
    station=sta_if.ifconfig()
    print('\nConnected as',station[0])
    return True

###################################################################################
# Do an HTTP GET
async def httpGET(url):
#    print('Get',url)
    hardware.setLED(True)
    resp = await aiohttp.request("GET", url)
    response=(await resp.read()).decode()
    hardware.setLED(False)
    return response
```
The second functions module, `hardware.py`, deals with physical devices such as LEDs and files:
```
import os
from machine import Pin

led = Pin(2, Pin.OUT)

###########################################################################
def setupPins():
    global relay,led
    relay=Pin(0,mode=Pin.OUT)
    led=Pin(2,mode=Pin.OUT)

###########################################################################
def setLED(onoff):
    global led
    led.off() if onoff else led.on()

###########################################################################
def setRelay(onoff):
    global relay
    relay.off() if onoff=='on' else relay.on()

###########################################################################
def getRelay():
    global relay
    return 'OFF' if relay.value() else 'ON'

###########################################################################
def fileExists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

###########################################################################
# Write data to a file
def writeFile(name,value):
#    print(f'Writing {value} to {name}')
    f = open(name, 'w')
    f.write(value)
    f.close()

###########################################################################
# Read data from a file
def readFile(name):
    try:
        f = open(name,'r')
        value=f.read()
        f.close()
    except:
        value=None
    return value
```
[Configured mode](configured.md)

[Unconfigured mode](unconfigured.md)

[Update mode](update.md)

[Back to start](README.md)

