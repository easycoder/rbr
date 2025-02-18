import network,asyncio,socket,time
from files import readFile

class STA():
    
    def __init__(self,config):
<<<<<<< HEAD
        sta=network.WLAN(network.WLAN.IF_STA)
        sta.active(True)
        self.sta=sta
        self.config=config
        config.setSTA(sta)
=======
        self.config=config
        config.setSTA(self)
        sta=network.WLAN(network.WLAN.IF_STA)
        sta.active(True)
        self.sta=sta
        config.setSTA(sta)
        if config.isESP8266(): sta.disconnect()
>>>>>>> 627b084 (sync)
    
    def disconnect(self):
        self.sta.disconnect()

    def connect(self):
        ssid=self.config.getSSID()
        password=self.config.getPassword()
        print(ssid,password)
        print('Connecting...',end='')
        self.sta.connect(ssid,password)
        while not self.sta.isconnected():
            time.sleep(1)
            print('.',end='')
<<<<<<< HEAD
        channel=self.sta.config('channel')
        print(f'{self.sta.ifconfig()[0]} ch {channel}')
        asyncio.create_task(asyncio.start_server(self.handleClient, "0.0.0.0", 80))

    async def handleClient(self,reader, writer):
=======
        ipaddr=self.sta.ifconfig()[0]
        self.channel=self.sta.config('channel')
        self.config.setIPAddr(ipaddr)
        print(f'{ipaddr} ch {self.channel}')
        asyncio.create_task(asyncio.start_server(self.handleClient, "0.0.0.0", 80))
    
    def getChannel(self): return self.channel

    async def sendDefaultResponse(self,writer):
        ms='M' if self.config.isMaster() else 'S'
        response=f'{self.config.getMAC()} {ms} {self.config.getName()}'
        await self.config.respond(response,writer)
        return None

    async def handleClient(self,reader, writer):
        handler=self.config.getHandler()
>>>>>>> 627b084 (sync)
        request = await reader.read(1024)
        request = request.decode().split(' ')
        if len(request) > 1:
            peer = None
            msg=None
<<<<<<< HEAD
            request=request[1].split('?')
            items=request[1].split('&')
            for n in range(0, len(items)):
                item = items[n].split('=')
                if item[0] =='mac': peer = item[1]
                elif item[0] == 'msg': espmsg = item[1]
            handler=self.config.getHandler()
=======
            ack=False
            request=request[1].split('?')
            if len(request)<2:
                return await self.sendDefaultResponse(writer)
            items=request[1].split('&')
            for n in range(0, len(items)):
                item = items[n].split('=')
                if len(item)<2:
                    response=handler.handleMessage(item[0])
                    return await self.config.respond(response,writer)
                if item[0]=='mac': peer=item[1]
                elif item[0]=='msg': espmsg=item[1]
>>>>>>> 627b084 (sync)
            if peer==None:
                response=handler.handleMessage(request)
            else:
                if peer==self.config.getMAC():
                    response=handler.handleMessage(espmsg)
                else:
<<<<<<< HEAD
                    if peer!=None and espmsg!=None:
                        response=self.config.send(peer,espmsg)
=======
                    if espmsg!=None:
                        response=await self.config.send(peer,espmsg)
#                        print('sta response:',response)
>>>>>>> 627b084 (sync)
                    else:
                        print('Can\'t send message')
                        response='Can\'t send message'
            await self.config.respond(response,writer)
