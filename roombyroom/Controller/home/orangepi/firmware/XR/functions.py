import network,socket,ubinascii,asyncio,time,os,json,machine
import uaiohttpclient as aiohttp
from machine import Pin

led = Pin(2, Pin.OUT)
myname=None
myssid=None
myip=None

def setupPins():
    global relay,led
    relay=Pin(0,mode=Pin.OUT)
    led=Pin(2,mode=Pin.OUT)

def setLED(onoff):
    global led
    led.off() if onoff else led.on()

def setRelay(onoff):
    global relay
    relay.off() if onoff=='on' else relay.on()

def getRelay():
    global relay
    return 'ON' if relay.value() else 'OFF'

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
# Get the configuration data
def getConfigData():
    global myname,hostssid,hostpass,mypass,myip
    if fileExists('config.json'):
        config=json.loads(readFile('config.json'))
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
async def setupAP(id):
    global myssid,ipaddr,mypass,myip
    if hostssid==None:
        myip='192.168.66.1'
        mypass='00000000'
    ap = network.WLAN(network.AP_IF)
    myssid = 'RBR-'+id+'-' + ubinascii.hexlify(ap.config('mac')).decode()[6:]
    print('Set up AP for',myssid)
    ap.active(True)
    ap.config(essid=myssid, authmode=3, password=mypass)
    ap.ifconfig((myip, '255.255.255.0', myip, '8.8.8.8'))

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
            return False
    station=sta_if.ifconfig()
    print('\nConnected as',station[0])
    return True

###################################################################################
# Do an HTTP GET
async def httpGET(url):
    global led
#    print('Get',url)
    setLED(True)
    resp = await aiohttp.request("GET", url)
    response=(await resp.read()).decode()
    setLED(False)
    return response


