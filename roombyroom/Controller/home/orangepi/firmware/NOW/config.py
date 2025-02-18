import json,asyncio,network
from files import readFile
from pin import PIN
<<<<<<< HEAD
from handler import Handler
from ap import AP
from sta import STA
from machine import reset
from binascii import hexlify,unhexlify
from espnow import ESPNow

class Main():
    peers=[]

    def init(self):
        self.config=json.loads(readFile('config.json'))
        self.led=PIN(self,'led')
        if self.getPinNo('relay')!=None: self.relay=PIN(self,'relay')
        self.handler=Handler(self)
        self.ap=AP(self)
        self.ap.startup()
        sta=STA(self)
        if self.config['device']=='ESP8266': sta.disconnect()
        if self.isMaster(): sta.connect()
        self.esp=ESPNow()
        self.esp.active(True)
        asyncio.create_task(self.startBlink())
        asyncio.create_task(self.stopAP())
        asyncio.create_task(self.receive())

    async def respond(self,response,writer):
        responseBytes = str(response).encode()
        await writer.awrite(b"HTTP/1.0 200 OK\r\n")
        await writer.awrite(b"Content-Type: text/plain\r\n")
        await writer.awrite(f"Content-Length: {len(responseBytes)}\r\n".encode())
        await writer.awrite(b"\r\n")
        await writer.awrite(str(response).encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    def send(self,peer,espmsg):
        global peers
        mac=unhexlify(peer.encode())
        if not peer in self.peers:
            self.peers.append(peer)
            ESPNow().add_peer(mac)
        channel=self.config['ap'].config('channel')
#        print(f'Sending \'{espmsg}\' to {peer} ({mac}) on channel {channel}')
        try:
            result=self.esp.send(mac,espmsg)
        except:
            result=False
        if not result: print('Fail')
        return result

    async def receive(self):
        while True:
            if ESPNow().any():
                host,msg = ESPNow().recv()
                if msg:
                    host=hexlify(host).decode()
                    msg=msg.decode()
                    response=self.handler.handleMessage(msg)
            await asyncio.sleep(.1)

    async def blink(self):
        while True:
            self.led.on()
            self.uptime+=self.blinkOn
            await asyncio.sleep(self.blinkOn)
            self.led.off()
            self.uptime+=self.blinkOff
            await asyncio.sleep(self.blinkOff)
    
    def setBlinkCycle(self,on,off):
        self.blinkOn=on
        self.blinkOff=off
        
    def startBlink(self):
        self.blinking=True
        self.uptime=0
        self.setBlinkCycle(0.5,0.5)
        await self.blink()
        
    def stopAP(self):
        await asyncio.sleep(120)
        self.setBlinkCycle(0.2,4.8)
        self.ap.stop()
        self.blinking=False
=======
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

    async def respond(self,response,writer): self.responder.respond(response,writer)

    async def send(self,peer,espmsg): return await self.espComms.send(peer,espmsg)
>>>>>>> 627b084 (sync)

    def reset(self):
        asyncio.get_event_loop().stop()

<<<<<<< HEAD
    def setAP(self,ap): self.config['ap']=ap
    def setSTA(self,sta): self.config['sta']=sta
    def setMAC(self,mac): self.config['mac']=mac
    def isMaster(self): return self.config['master']
    def getName(self): return self.config['name']
    def getSSID(self): return self.config['ssid']
    def getMAC(self): return self.config['mac']
    def getPassword(self): return self.config['password']
    def getChannel(self): return self.config['channel']
    def getHandler(self): return self.handler
=======
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
>>>>>>> 627b084 (sync)
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
<<<<<<< HEAD

Main().init()
try: asyncio.get_event_loop().run_forever()
except: pass
reset()
 


=======
>>>>>>> 627b084 (sync)
