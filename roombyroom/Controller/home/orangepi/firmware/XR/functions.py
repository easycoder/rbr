import network,socket,ubinascii,asyncio,time,os,json
import hardware,maps
from maps import setMyName,getMyName,setHostSSID,getHostSSID,setHostPass,getHostPass
from maps import setMySSID,getMySSID,setMyPass,getMyPass
from maps import setNetIF,getNetIF,setStation,getStation,getMAC,setMAC

def getConfigData():
    if hardware.fileExists('config.json'):
        config=json.loads(hardware.readFile('config.json'))
        setMyName(config['myname'])
        setHostSSID(config['hostssid'])
        setHostPass(config['hostpass'])
        setMyPass(config['mypass'])
        return (json.dumps(config))
    else:
        os.remove('config.json')
        msg='\nCan\'t load the config file'
        raise Exception(msg)

def setupAP():
    station=getStation()
    ap = network.WLAN(network.AP_IF)
    setMAC(ubinascii.hexlify(ap.config('mac')).decode()[6:])
    setMySSID(f'RBR-XR-{getMAC()}')
    print('Set up AP for',getMySSID(),'with',getMyPass())
    ap.active(True)
    ap.config(essid=getMySSID(), authmode=3, password=getMyPass())
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
        time.sleep(1)
        timeout-=1
        if timeout==0:
            print('\nCan\'t set up AP')
            reset()

    print('AP:',ap.ifconfig())

def connect():
    if getNetIF()!=None:
        getNetIF().disconnect()
    hostSSID=getHostSSID()
    print('connect',hostSSID)
    rssi=None
    sta_if = network.WLAN(network.STA_IF)
    setNetIF(sta_if)
    sta_if.active(True)
    for (ssid, bssid, channel, RSSI, authmode, hidden) in sta_if.scan():
        if ssid.decode("utf-8")==hostSSID:
            rssi="{}".format(RSSI)
    print('RSSI:',rssi)
    if rssi==None:
        raise Exception('Host not found')
    maps.setRSSI(rssi)
    sta_if.connect(hostSSID,getHostPass())
    print('Connecting...')
    timeout=60
    while sta_if.isconnected()==False:
        time.sleep(1)
        print('.',end='')
        timeout-=1
        if timeout==0:
            raise Exception(f'\nCan\'t connect to {hostSSID}')
    setStation(sta_if.ifconfig())
    print('\nConnected as',getStation()[0])
