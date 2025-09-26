import asyncio,machine,time
from espnow import ESPNow

class Channels():
    def __init__(self,espComms):
        print('Starting Channels')
        self.espComms=espComms
        self.config=espComms.config
        self.channels=[1,6,11]
        self.myMaster=self.config.getMyMaster()
        if self.config.isMaster():
            self.ssid=self.config.getSSID()
            self.password=self.config.getPassword()
            asyncio.create_task(self.checkRouterChannel())
        self.resetCounter()

    def setupSlaveTasks(self):
        asyncio.create_task(self.findMyMaster())
        asyncio.create_task(self.countMissingMessages())

    def resetCounter(self):
        self.idleCount=0

    async def findMyMaster(self):
        if await self.ping(): return
        self.hopToNextChannel()
        asyncio.get_event_loop().stop()
        machine.reset()

    async def ping(self):
        peer=bytes.fromhex(self.myMaster)
        self.espComms.espSend(peer,'ping')
        _,msg=self.espComms.e.recv(1000)
        print('Ping response from',self.myMaster,':',msg)
        if msg:
            print('Found master on channel',self.espComms.channel)
            return True
        return False

    async def countMissingMessages(self):
        print('Count missing messages')
        espComms=self.espComms
        ap=espComms.ap
        e=espComms.e
        self.idleCount=0
        while True:
            await asyncio.sleep(1)
            self.idleCount+=1
            limit=30
            if self.idleCount>limit:
                print('No messages for 30 seconds')
                # Retry the current channel
                if await self.ping():
                    self.idleCount=0
                    continue
                self.hopToNextChannel()
                channel=self.hopToNextChannel()
                asyncio.get_event_loop().stop()
                machine.reset()

    def hopToNextChannel(self):
        index=-1
        for n,value in enumerate(self.channels):
            if value==self.espComms.channel:
                self.espComms.channel=self.channels[(n+1)%len(self.channels)]
                index=n
                break
        if index==-1: self.espComms.channel=self.channels[0]
        self.config.setChannel(self.espComms.channel)

    async def checkRouterChannel(self):
        print('Check the router channel')
        while True:
            await asyncio.sleep(300)
            sta=self.espComms.sta
            sta.disconnect()
            time.sleep(1)
            print('Reconnecting...',end='')
            sta.connect(self.ssid,self.password)
            while not sta.isconnected():
                time.sleep(1)
                print('.',end='')
            channel=sta.config('channel')
            if channel!=self.espComms.channel:
                print(' router changed channel from',self.espComms.channel,'to',channel)
                asyncio.get_event_loop().stop()
                machine.reset()
            print(' no channel change')
            self.espComms.restartESPNow()