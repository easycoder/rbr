import json,asyncio,network
from files import readFile
from pin import PIN
from machine import reset
from binascii import hexlify,unhexlify
from responder import Responder

class Config():

    def __init__(self):
        self.config=json.loads(readFile('config.json'))
        self.led=PIN(self,'led')
        if self.getPinNo('relay')!=None: self.relay=PIN(self,'relay')
        self.ipaddr=None
        self.responder=Responder(self)

    async def respond(self,response,writer):
        await self.responder.respond(response,writer)
    async def sendDefaultResponse(self,writer):
        await self.responder.sendDefaultResponse(writer)

    async def send(self,peer,espmsg): return await self.espComms.send(peer,espmsg)

    def reset(self):
        asyncio.get_event_loop().stop()

    def setAP(self,ap): self.ap=ap
    def setSTA(self,sta): self.sta=sta
    def setMAC(self,mac): self.mac=mac
    def setIPAddr(self,ipaddr): self.ipaddr=ipaddr
    def setHandler(self,handler): self.handler=handler
    def setESPComms(self,espComms): self.espComms=espComms
    
    def isMaster(self): return self.config['master']
    def isESP8266(self): return self.config['device']=='ESP8266'
    def getDevice(self): return self.config['device']
    def getName(self): return self.config['name']
    def getSSID(self): return self.config['ssid']
    def getMAC(self): return self.mac
    def getAP(self): return self.ap
    def getSTA(self): return self.sta
    def getIPAddr(self): return self.ipaddr
    def getPassword(self): return self.config['password']
    def getChannel(self): return self.ap.getChannel()
    def getHandler(self): return self.handler
    def getESPComms(self): return self.espComms
    def getRBRNow(self): return self.rbrNow
    def getPinNo(self,name):
        for pin in self.config['pins']:
            if pin['name']==name:
                return pin['pin']
        return None
    def isPinReversed(self,name):
        for pin in self.config['pins']:
            if pin['name']==name:
                return pin['reverse']
        return None
    def getLED(self): return self.led
    def getRelay(self): return self.relay
    def getUptime(self): return int(round(self.uptime))
