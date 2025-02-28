import asyncio,network
from files import readFile
from config import Config
from pin import PIN
from handler import Handler
from ap import AP
from sta import STA
from machine import reset
from binascii import hexlify,unhexlify
from espnow import ESPNow
from espcomms import ESPComms

class RBRNow():

    def __init__(self):
        self.config=Config()
        self.led=self.config.getLED()

    def init(self):
        config=self.config
        self.handler=Handler(config)
        ap=AP(config)
        ap.startup()
        sta=STA(config)
        if config.isMaster(): sta.connect()
        espComms=ESPComms(config)
        asyncio.create_task(self.startBlink())
        asyncio.create_task(self.stopAP())
        if not config.isMaster():
            asyncio.create_task(espComms.receive())

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
        self.config.getAP().stop()
        self.blinking=False

if __name__ == '__main__':
    RBRNow().init()
    try: asyncio.get_event_loop().run_forever()
    except: pass
    reset()
 
