import asyncio,network
from files import readFile
from config import Config
from pin import PIN
from handler import Handler
from ap import AP
from sta import STA
from machine import reset
from binascii import hexlify,unhexlify
from espcomms import ESPComms

class RBRNow():

    def init(self):
        self.config=Config()
        self.led=self.config.getLED()
        config=self.config
        self.handler=Handler(config)
        ap=AP(config)
        sta=STA(config)
        if config.isMaster():
            print('Starting as master')
            sta.connect()
        else: print('Starting as slave')
        config.startServer()
        espComms=ESPComms(config)
        config.setESPComms(espComms)
        asyncio.create_task(self.startBlink())
        asyncio.create_task(self.stopAP())
        if not config.isMaster():
            asyncio.create_task(espComms.receive())
        asyncio.create_task(self.config.bleScan.scan())

    async def blink(self):
        while True:
            if self.config.resetRequested:
                asyncio.get_event_loop().stop()
            self.led.on()
            if self.blinkCycle=='init':
                await asyncio.sleep(0.5)
                self.led.off()
                await asyncio.sleep(0.5)
                self.config.addUptime(1)
            elif self.blinkCycle=='master':
                await asyncio.sleep(0.2)
                self.led.off()
                await asyncio.sleep(0.2)
                self.led.on()
                await asyncio.sleep(0.2)
                self.led.off()
                await asyncio.sleep(4.6)
                self.config.addUptime(5)
            elif self.blinkCycle=='slave':
                await asyncio.sleep(0.2)
                self.led.off()
                await asyncio.sleep(4.8)
                self.config.addUptime(5)
        
    def startBlink(self):
        self.blinking=True
        self.uptime=0
        self.blinkCycle='init'
        await self.blink()
        
    def stopAP(self):
        await asyncio.sleep(120)
        if self.config.isMaster(): self.blinkCycle='master'
        else: self.blinkCycle='slave'
        self.config.getAP().stop()
        self.blinking=False

if __name__ == '__main__':
    RBRNow().init()
    try: asyncio.get_event_loop().run_forever()
    except: pass
    reset()
 


