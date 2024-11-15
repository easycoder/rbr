import network,socket,ubinascii,asyncio,time,os,json,machine
import uaiohttpclient as aiohttp
import hardware

mac=None
myname=None
myssid=None
mypass=None
rssi=None

def reset():
    time.sleep(1)
    machine.reset()

def getMAC():
    global mac
    return mac

def getMyName():
    global myname
    return myname

def getHostSSID():
    global hostssid
    return hostssid

def getMySSID():
    global myssid
    return myssid

def setMyPassword(p):
    global mypass
    mypass=p

def isPrimary():
    global station
    path=station[2]
    return path=='172.24.1.1'

def getServer():
    global station
    path=station[2]
    if isPrimary():
        return path+'/resources/php/rest.php/'
    return path

def getRSSI():
    global rssi
    return rssi

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
        reset()

async def setupAP():
    global station,mac,myssid,mypass
    ap = network.WLAN(network.AP_IF)
    mac = ubinascii.hexlify(ap.config('mac')).decode()[6:]
    myssid = 'RBR-XR-' + mac
    print('Set up AP for',myssid,'with',mypass)
    ap.active(True)
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
            reset()

    print('AP:',ap.ifconfig())

def connect():
    global station,hostssid,hostpass,rssi
    print('connect',hostssid)
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    for (ssid, bssid, channel, RSSI, authmode, hidden) in sta_if.scan():
        if ssid.decode("utf-8")==hostssid:
          rssi="{}".format(RSSI)
    print('RSSI:',rssi)
    if rssi==None:
        reset()
    sta_if.connect(hostssid,hostpass)
    print('Connecting...')
    timeout=60
    while sta_if.isconnected()==False:
        time.sleep(1)
        print('.',end='')
        timeout-=1
        if timeout==0:
            print('\nCan\'t connect to',hostssid)
            reset()
    station=sta_if.ifconfig()
    print('\nConnected as',station[0])
    return True

async def httpGET(url):
#    print('Get',url)
    hardware.setLED(True)
    resp = await aiohttp.request("GET", url)
    response=(await resp.read()).decode()
    hardware.setLED(False)
    return response



