import json,asyncio,network
from files import readFile
from pin import PIN
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

    def reset(self):
        asyncio.get_event_loop().stop()

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

Main().init()
try: asyncio.get_event_loop().run_forever()
except: pass
reset()
 


