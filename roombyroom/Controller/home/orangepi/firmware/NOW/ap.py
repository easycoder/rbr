import network,binascii,asyncio

class AP():
    
    def __init__(self,config):
        self.config=config
        config.setAP(self)
        ap=network.WLAN(network.AP_IF)
        ap.active(True)
        self.ap=ap
        mac=binascii.hexlify(self.ap.config('mac')).decode()
        self.config.setMAC(mac)
        self.ssid=f'RBR-Now-{mac}'
        ap.config(essid=self.ssid,password='00000000')
        ap.config(channel=config.getChannel())
        ap.ifconfig(('192.168.9.1', '255.255.255.0', '192.168.9.1', '8.8.8.8'))
        print(mac,config.getName()) 

    def startup(self):
        self.apServer=asyncio.create_task(asyncio.start_server(self.handleClient,self.ap.ifconfig()[0],80))

    def stop(self):
        self.apServer.cancel()
        self.ap.active(False)

    def getChannel(self): return self.ap.config('channel')

    async def handleClient(self,reader,writer):
        request_line=await reader.readline()
        request=request_line.decode().strip()
        request=request.split(' ')[1]
        if request=='/ipaddr':
            response=self.config.getIPAddr()
            await self.config.respond(response,writer)
        else:
            await self.config.sendDefaultResponse(writer)

