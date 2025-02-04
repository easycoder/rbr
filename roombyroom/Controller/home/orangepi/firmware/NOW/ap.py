import network,binascii,asyncio

class AP():
    
    def __init__(self,config):
        self.config=config
        ap=network.WLAN(network.AP_IF)
        ap.active(True)
        self.ap=ap
        config.setAP(ap)
        mac=binascii.hexlify(self.ap.config('mac')).decode()
        self.config.setMAC(mac)
        self.ssid=f'RBR-Now-{mac}'
        ap.config(essid=self.ssid,password='00000000')
        ap.config(channel=config.getChannel())
        ap.ifconfig(('192.168.9.1', '255.255.255.0', '192.168.9.1', '8.8.8.8'))
        print(mac,ap.config('channel'),config.getName()) 

    def startup(self):
        self.apServer=asyncio.create_task(asyncio.start_server(self.handleClient,self.ap.ifconfig()[0],80))

    def stop(self):
        self.apServer.cancel()
#        self.ap.config(essid='-???-',password='00000000',channel=1,hidden=True)
#        self.ap.ifconfig(('0.0.0.0', '255.255.255.0', '0.0.0.0', '8.8.8.8'))
#        self.startup()

    async def handleClient(self,reader,writer):
        request_line=await reader.readline()
        request=request_line.decode().strip()
#        print('Request:',request)
        ms='M' if self.config.isMaster() else 'S'
        response=f'{self.ssid} {self.config.getName()} {ms}\r\n'
        await self.config.respond(response,writer)
