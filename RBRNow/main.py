import asyncio,machine
from config import Config
from pin import PIN

class RBRNow():

    def init(self):
        config=Config()
        self.led=config.getLED()
        self.config=config
        asyncio.create_task(self.startBlink())
        asyncio.create_task(self.closeAP())
        self.config.doFinalInitTasks()

    async def blink(self):
        while True:
            if self.config.resetRequested:
                asyncio.get_event_loop().stop()
                machine.reset()
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

    async def startBlink(self):
        self.uptime=0
        self.blinkCycle='init'
        await self.blink()

    async def closeAP(self):
        while True:
            print('2-min config window')
            await asyncio.sleep(120)
            print('Close the AP')
            if self.config.isMaster():
                self.blinkCycle='master'
                self.config.closeAP()
                break
            if self.config.getMyMaster()!=None:
                self.blinkCycle='slave'
                self.config.closeAP()
                break

if __name__ == '__main__':
    RBRNow().init()
    try: asyncio.get_event_loop().run_forever()
    except: pass
    print('Finished')
    machine.reset()

