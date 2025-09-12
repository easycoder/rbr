import asyncio,machine,time
from espnow import ESPNow

class Channels():
    def __init__(self,espComms):
        print('Starting Channels')
        self.espComms=espComms
        self.config=self.espComms.config
        self.channels=[1,6,11]
        if self.config.isMaster():
            self.ssid=self.config.getSSID()
            self.password=self.config.getPassword()
            asyncio.create_task(self.checkRouterChannel())
        self.resetCounters()
        asyncio.create_task(self.findMyMaster())
        asyncio.create_task(self.countMissingMessages())

    def resetCounters(self):
        self.messageCount=0
        self.idleCount=0

    async def findMyMaster(self):
        self.foundMaster=False
        self.myMaster=self.config.getMyMaster()
        print('Looking for',self.myMaster)
        if self.myMaster==None:
            # Wait 10 seconds for a message
            for count in range(100):
                self.myMaster=self.config.getMyMaster()
                if self.myMaster!=None:
                    print('Found master',self.myMaster,'on channel',self.espComms.channel)
                    self.foundMaster=True
                    return
                await asyncio.sleep(.1)
        else:
            if await self.ping(): return
            self.hopToNextChannel()
            asyncio.get_event_loop().stop()
            machine.reset()
    
    async def ping(self):
        peer=bytes.fromhex(self.myMaster)
        self.espComms.addPeer(peer)
        self.espComms.e.send(peer,'ping')
        _,msg=self.espComms.e.recv(1000)
        print('Ping response from',self.myMaster,':',msg)
        if msg!=None:# and msg.decode()=='pong':
            print('Found master on channel',self.espComms.channel)
            self.foundMaster=True
            return True
        return False

    async def countMissingMessages(self):
        print('Count missing messages')
        espComms=self.espComms
        ap=espComms.ap
        e=espComms.e
        while True:
            await asyncio.sleep(1)
            if not self.foundMaster: continue

            self.messageCount+=1
            self.idleCount+=1
            
            limit=30
            if self.messageCount>limit and not espComms.config.isMaster():
                print('No messages for 30 seconds')
                # Retry the current channel
                if await self.ping():
                    self.resetCounters()
                    continue
                self.hopToNextChannel()
                channel=self.hopToNextChannel()
                asyncio.get_event_loop().stop()
                machine.reset()

            if self.idleCount>300:
                print('No messages after 3 minutes')
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

