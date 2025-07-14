import json,asyncio,time
from files import readFile,writeFile,fileExists
from pin import PIN
from server import Server
from dht22 import DHT22
from blescan import BLEScan

class Config():

    def __init__(self):
        if fileExists('config.json'):
            self.config=json.loads(readFile('config.json'))
        else:
            self.config={}
            self.config['name']='(none)'
            self.config['master']=False
            self.config['channel']=1
            self.config['path']=''
            self.config['pins']={}
            pin={}
            pin['pin']=''
            pin['invert']=False
            self.config['pins']['led']=pin
            pin={}
            pin['pin']=''
            pin['invert']=False
            self.config['pins']['relay']=pin
            pin={}
            pin['pin']=''
            self.config['pins']['dht22']=pin
            writeFile('config.json',json.dumps(self.config))
        pin,invert=self.getPinInfo('led')
        self.led=PIN(self,pin,invert)
        pin,invert=self.getPinInfo('relay')
        self.relay=PIN(self,pin,invert)
        pin,_=self.getPinInfo('dht22')
        if pin=='': self.dht22=None
        else:
            self.dht22=DHT22(pin)
            asyncio.create_task(self.dht22.measure())
        print('path:',self.config['path'])
        self.ipaddr=None
        self.uptime=0
        self.resetRequested=False
        self.server=Server(self)
        asyncio.create_task(self.runWatchdog())
        self.bleScan=BLEScan()

    async def respond(self,response,writer):
        await self.server.respond(response,writer)
    async def sendDefaultResponse(self,writer):
        await self.server.sendDefaultResponse(writer)
    async def handleClient(self,reader,writer):
        await self.server.handleClient(reader,writer)

    async def send(self,peer,espmsg): return await self.espComms.send(peer,espmsg)

    def reset(self):
        print('Reset requested')
        self.resetRequested=True
    
    def pause(self):
        if self.dht22!=None: self.dht22.pause()
    
    def resume(self):
        if self.dht22!=None: self.dht22.resume()

    def setAP(self,ap): self.ap=ap
    def setSTA(self,sta): self.sta=sta
    def setMAC(self,mac): self.mac=mac
    def setChannel(self,channel):
        self.config['channel']=channel
        writeFile('config.json',json.dumps(self.config))
    def setIPAddr(self,ipaddr): self.ipaddr=ipaddr
    def setHandler(self,handler): self.handler=handler
    def setESPComms(self,espComms): self.espComms=espComms
    def addUptime(self,t): self.uptime+=t
    
    def isMaster(self): return self.config['master']
    def isESP8266(self): return False
    def getDevice(self): return self.config['device']
    def getName(self): return self.config['name']
    def getSSID(self): return self.config['hostssid']
    def getPassword(self): return self.config['hostpass']
    def getMAC(self): return self.mac
    def getAP(self): return self.ap
    def getSTA(self): return self.sta
    def stopAP(self): self.ap.stop()
    def startServer(self): self.server.startup()
    def getIPAddr(self): return self.ipaddr
    def getChannel(self): return self.ap.getChannel()
    def getHandler(self): return self.handler
    def getESPComms(self): return self.espComms
    def getBLEScan(self): return self.bleScan
    def getRBRNow(self): return self.rbrNow
    def getPinInfo(self,name):
        pin=self.config['pins'][name]
        print(name,pin)
        if 'invert' in pin: invert=pin['invert']
        else: invert=False
        return pin['pin'],invert
    def getLED(self): return self.led
    def getRelay(self): return self.relay
    def getUptime(self): return int(round(self.uptime))
    def getTemperature(self): return self.dht22.getTemperature()

    async def runWatchdog(self):
        while True:
            self.active=False
            await asyncio.sleep(180)
            if not self.active:
                print('No activity - reset')
                asyncio.get_event_loop().stop()
        pass

    def kickWatchdog(self):
        self.active=True
