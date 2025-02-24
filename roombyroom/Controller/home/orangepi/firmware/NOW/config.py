import json,asyncio,network
from files import readFile,writeFile,fileExists
from pin import PIN
from machine import reset
from binascii import hexlify,unhexlify
from server import Server

class Config():

    def __init__(self):
        if fileExists('config.json'):
            self.config=json.loads(readFile('config.json'))
        else:
            self.config={}
            self.config['name']='(none)'
            self.config['master']=False
            self.config['channel']=1
            self.config['pins']={}
            pin={}
            pin['pin']=3
            pin['invert']=False
            self.config['pins']['led']=pin
            pin={}
            pin['pin']=9
            pin['invert']=False
            self.config['pins']['relay']=pin
            writeFile('config.json',json.dumps(self.config))
        self.led=PIN(self,'led')
        if self.getPinNo('relay')!=None: self.relay=PIN(self,'relay')
        self.ipaddr=None
        self.uptime=0
        self.server=Server(self)

    async def respond(self,response,writer):
        await self.server.respond(response,writer)
    async def sendDefaultResponse(self,writer):
        await self.server.sendDefaultResponse(writer)
    async def handleClient(self,reader,writer):
        await self.server.handleClient(reader,writer)

    async def send(self,peer,espmsg): return await self.espComms.send(peer,espmsg)

    def restart(self):
        await asyncio.sleep(1)
        asyncio.get_event_loop().stop()

    def reset(self):
        print('Reset requested')
        asyncio.create_task(self.restart())

    def setAP(self,ap): self.ap=ap
    def setSTA(self,sta): self.sta=sta
    def setMAC(self,mac): self.mac=mac
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
    def getRBRNow(self): return self.rbrNow
    def getPinNo(self,name):
        return self.config['pins'][name]['pin']
    def isPinInverted(self,name):
        return self.config['pins'][name]['invert']
        return None
    def getLED(self): return self.led
    def getRelay(self): return self.relay
    def getUptime(self): return int(round(self.uptime))
