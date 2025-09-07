import asyncio,machine,time
from espnow import ESPNow

class Channels():
    def __init__(self,espComms):
        self.espComms=espComms
        self.channels=[1,6,11]
        if self.espComms.config.isMaster():
            self.ssid=espComms.config.getSSID()
            self.password=espComms.config.getPassword()
            asyncio.create_task(self.checkRouterChannel())
        self.resetCounters()
        asyncio.create_task(self.countMissingMessages())

    def resetCounters(self):
        self.messageCount=0
        self.idleCount=0

    async def countMissingMessages(self):
        print('Count missing messages')
        espComms=self.espComms
        ap=espComms.ap
        e=espComms.e
        while True:
            await asyncio.sleep(1)

            self.messageCount+=1
            self.idleCount+=1
            
            limit=30
            if self.messageCount>limit and not espComms.config.isMaster():
                print('No messages for 30 seconds')
                async with espComms.espnowLock:
                    for index,value in enumerate(self.channels):
                        if value==espComms.channel:
                            espComms.channel=self.channels[(index+1)%len(self.channels)]
                            break
                    self.restartESPNow()
                    print('Switched to channel',espComms.channel)
                    self.messageCount=0

            if self.idleCount>300:
                print('No messages after 3 minutes')
                asyncio.get_event_loop().stop()
                machine.reset()
    
    def restartESPNow(self):
        espComms=self.espComms
        ap=espComms.ap
        e=espComms.e
        e.active(False)
        await asyncio.sleep(.2)            
        ap.active(False)
        await asyncio.sleep(.1)
        ap.active(True)
        ap.config(channel=espComms.channel)
        espComms.config.setChannel(espComms.channel)   
        e=ESPNow()
        e.active(True)
        self.peers=[]

    async def checkRouterChannel(self):
        while True:
            await asyncio.sleep(60)
            sta=self.espComms.sta
            sta.disconnect()
            time.sleep(1)
            print('Reconnecting...',end='')
            sta.connect(self.ssid,self.password)
            while not sta.isconnected():
                time.sleep(1)
                print('.',end='')
            self.restartESPNow()
            channel=sta.config('channel')
            if channel!=self.espComms.channel:
                print(' router changed channel from',self.espComms.channel,'to',channel)
                asyncio.get_event_loop().stop()
                machine.reset()
            print(' no channel change')
    
        