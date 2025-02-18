incomingMap={}
outgoingMap={}
pollCount=0
currentVersion=0
mac=None
myname=None
myssid=None
hostssid=None
hostpass=None
mypass=None
rssi=None
netIF=None
station=None

def getOutgoingMap():
    global outgoingMap
    return outgoingMap

def setOutgoingMap(map):
    global outgoingMap
    outgoingMap=map

def getIncomingMap():
    global incomingMap
    return incomingMap

def setIncomingMap(map):
    global incomingMap
    incomingMap=map

def setIncomingMapElement(key,value):
    global incomingMap
    incomingMap[key]=value

def getPollCount():
    global pollCount
    return pollCount

def clearPollCount():
    global pollCount
    pollCount=0

def bumpPollCount():
    global pollCount
    pollCount+=1

def getCurrentVersion():
    global currentVersion
    return currentVersion

def setCurrentVersion(version):
    global currentVersion
    currentVersion=version

def getMAC():
    global mac
    return mac

def setMAC(m):
    global mac
    mac=m

def getMyName():
    global myname
    return myname

def setMyName(name):
    global myname
    myname=name

def getHostSSID():
    global hostssid
    return hostssid

def setHostSSID(ssid):
    global hostssid
    hostssid=ssid

def getHostPass():
    global hostpass
    return hostpass

def setHostPass(p):
    global hostpass
    hostpass=p

def getMySSID():
    global myssid
    return myssid

def setMySSID(ssid):
    global myssid
    myssid=ssid

def getMyPass():
    global mypass
    return mypass

def setMyPass(p):
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

def setRSSI(r):
    global rssi
    rssi=r

def getNetIF():
    global netIF
    return netIF

def setNetIF(nif):
    global netIF
    netIF=nif

def getStation():
    global station
    return station

def setStation(sta):
    global station
    station=sta

