import network,asyncio,socket,time
from files import readFile

class STA():
    
    def __init__(self,config):
        sta=network.WLAN(network.WLAN.IF_STA)
        sta.active(True)
        self.sta=sta
        self.config=config
        config.setSTA(sta)
    
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
        channel=self.sta.config('channel')
        print(f'{self.sta.ifconfig()[0]} ch {channel}')
        asyncio.create_task(asyncio.start_server(self.handleClient, "0.0.0.0", 80))

    async def handleClient(self,reader, writer):
        request = await reader.read(1024)
        request = request.decode().split(' ')
        if len(request) > 1:
            peer = None
            msg=None
            request=request[1].split('?')
            items=request[1].split('&')
            for n in range(0, len(items)):
                item = items[n].split('=')
                if item[0] =='mac': peer = item[1]
                elif item[0] == 'msg': espmsg = item[1]
            handler=self.config.getHandler()
            if peer==None:
                response=handler.handleMessage(request)
            else:
                if peer==self.config.getMAC():
                    response=handler.handleMessage(espmsg)
                else:
                    if peer!=None and espmsg!=None:
                        response=self.config.send(peer,espmsg)
                    else:
                        print('Can\'t send message')
                        response='Can\'t send message'
            await self.config.respond(response,writer)
