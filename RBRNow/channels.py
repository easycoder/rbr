import asyncio,machine,time
from espnow import ESPNow

class Channels():
    def __init__(self,espComms):
        self.espComms=espComms
        self.channels=[1,6,11]
        self.ssid=espComms.sta.config('ssid')
        self.resetCounters()
        if self.espComms.config.isMaster():
            asyncio.create_task(self.checkRouterChannel())
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
            if not espComms.config.isMaster() and self.messageCount>limit:
                async with espComms.espnowLock:
                    for index,value in enumerate(self.channels):
                        if value==espComms.channel:
                            espComms.channel=self.channels[(index+1)%len(self.channels)]
                            break
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
                    print('Switched to channel',espComms.channel)
                    self.messageCount=0

            if self.idleCount>300:
                print('No messages after 3 minutes')
                asyncio.get_event_loop().stop()
                machine.reset()

    async def checkRouterChannel(self):
        print('Check router channel')
        while True:
            await asyncio.sleep(60)
            currentChannel=self.getRouterChannel()
            if currentChannel!=self.espComms.channel:
                print('Router changed channel from',self.espComms.channel,'to',currentChannel)
                asyncio.get_event_loop().stop()
                machine.reset()
#            else: print('No channel change')
    
    def getRouterChannel(self):
        sta=self.espComms.sta
        sta.disconnect()
        time.sleep(1)
        networks=sta.scan()
        sta.connect(self.ssid)
        
        for networkInfo in networks:
#            print(networkInfo[0].decode(),networkInfo[2])
            if networkInfo[0].decode()==self.ssid:
                return networkInfo[2]
        return None
        