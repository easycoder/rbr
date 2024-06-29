# functions.py

import network,socket,ubinascii,asyncio,time
import uaiohttpclient as aiohttp
import machine
from machine import Pin

relay=Pin(0,mode=Pin.OUT)
led=Pin(2,mode=Pin.OUT)
led.off()

def setRelay(onoff):
    global relay
    relay.off() if onoff else relay.on()

def setLed(onoff):
    global led
    led.off() if onoff else led.on()

def getRelay():
    global relay
    return str(relay.value())

###################################################################################
def getMyName():
    global myname
    return myname

###################################################################################
def getMySSID():
    global myssid
    return myssid

###################################################################################
def setMyPassword(p):
    global mypass
    mypass=p

###################################################################################
def getServer():
    global station
    path=station[2]
    if path=='172.24.1.1':
        path=path+'/resources/php/rest.php'
    return path

###################################################################################
# Write data to a file
def writeFile(name,value):
    print(f'Writing {value} to {name}')
    f = open(name, 'w')
    f.write(value)
    f.close()

###################################################################################
#Read data from a file
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
    try:
        myname=readFile('name.txt')
    except:
        myname = None
    try:
        hostssid=readFile('hostssid.txt')
    except:
        hostssid = None
    try:
        hostpass=readFile('hostpass.txt')
    except:
        hostpass = None
    try:
        mypass=readFile('mypass.txt')
    except:
        mypass = None
    try:
        myip=readFile('myip.txt')
    except:
        myip = None

    print ('Config:',myname,hostssid,hostpass,mypass,myip)
    return (myname,hostssid,hostpass,mypass,myip)

###################################################################################
# The Access Point
async def setupAP(id,ipaddr,mypass):
    global myssid
    ap = network.WLAN(network.AP_IF)
    myssid = 'RBR-'+id+'-' + ubinascii.hexlify(ap.config('mac')).decode()[6:]
    print('Set up AP for',myssid)
    ap.active(True)
    ap.config(essid=myssid, authmode=3, password=mypass)
    ap.ifconfig((ipaddr, '255.255.255.0', ipaddr, '8.8.8.8'))

    while not ap.active():
        await asyncio.sleep(1)

    print('AP:',ap.ifconfig())

###################################################################################
# Connect to our host
def connect():
    global station
    hostssid=readFile('hostssid.txt')
    hostpass=readFile('hostpass.txt')
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect(hostssid,hostpass)
    print('Connecting to',hostssid)
    timeout=30
    while sta_if.isconnected()==False:
        time.sleep(1)
        print('.',end='')
        timeout-=1
        if timeout==0:
            print('\nCan\'t connect to',hostssid)
            return False
    station=sta_if.ifconfig()
    print('\nConnected to',station)
    return True

###################################################################################
# Do an HTTP GET
async def httpGET(url):
    setLed(True)
    resp = await aiohttp.request("GET", url)
    setLed(False)
    response=await resp.read()
    return response.decode()

###################################################################################
# Return a dictionary from a stringified object
def createData(str):
    values={}
    items=str.split(',')
    for item in items:
        key,value=item.split(':',1)
        values[key]=value
    return values

###################################################################################
# Update the firmware
async def update(prefix,list):
    for name in list:
        print('Update',prefix+'/'+name)
        url='http://'+getServer()+'/firmware?path='+prefix+'/'+name
        try:
            print('GET',url)
            content=await httpGET(url)
            f=open(name,'w')
            f.write(content)
            f.close()
        except Exception as e:
            print('Error:',e,'\n','Error in update')



