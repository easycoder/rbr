import network,binascii,asyncio,random

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
        ap.ifconfig(('192.168.9.1','255.255.255.0','192.168.9.1','8.8.8.8'))
        print(mac,config.getName()) 

    def stop(self):
        password=str(random.randrange(100000,999999))
        print(password)
        self.ap.config(essid='-',password=password)

    def getChannel(self): return self.ap.config('channel')
