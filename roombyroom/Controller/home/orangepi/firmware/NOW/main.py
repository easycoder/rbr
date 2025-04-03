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

<<<<<<< HEAD
    def init(self):
        self.config=Config()
        self.led=self.config.getLED()
=======
    def __init__(self):
        self.config=Config()
        self.led=self.config.getLED()

    def init(self):
>>>>>>> refs/remotes/origin/main
        config=self.config
        self.handler=Handler(config)
        ap=AP(config)
        sta=STA(config)
<<<<<<< HEAD
        if config.isMaster():
            print('Starting as master')
            sta.connect()
        else: print('Starting as slave')
=======
        if config.isMaster(): sta.connect()
>>>>>>> refs/remotes/origin/main
        config.startServer()
        espComms=ESPComms(config)
        asyncio.create_task(self.startBlink())
        asyncio.create_task(self.stopAP())
        if not config.isMaster():
            asyncio.create_task(espComms.receive())

    async def blink(self):
        while True:
            self.led.on()
<<<<<<< HEAD
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
=======
            self.config.addUptime(self.blinkOn)
            await asyncio.sleep(self.blinkOn)
            self.led.off()
            self.config.addUptime(self.blinkOff)
            await asyncio.sleep(self.blinkOff)
    
    def setBlinkCycle(self,on,off):
        self.blinkOn=on
        self.blinkOff=off
>>>>>>> refs/remotes/origin/main
        
    def startBlink(self):
        self.blinking=True
        self.uptime=0
<<<<<<< HEAD
        self.blinkCycle='init'
        await self.blink()
        
    def stopAP(self):
        await asyncio.sleep(120)
        if self.config.isMaster(): self.blinkCycle='master'
        else: self.blinkCycle='slave'
=======
        self.setBlinkCycle(0.5,0.5)
        await self.blink()
        
    def stopAP(self):
        await asyncio.sleep(600)
        self.setBlinkCycle(0.2,4.8)
>>>>>>> refs/remotes/origin/main
        self.config.getAP().stop()
        self.blinking=False

if __name__ == '__main__':
    RBRNow().init()
    try: asyncio.get_event_loop().run_forever()
    except: pass
    reset()
 
<<<<<<< HEAD

=======
>>>>>>> refs/remotes/origin/main
