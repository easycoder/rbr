import network,asyncio,socket,time
from files import readFile

class STA():
    
    def __init__(self,config):
        self.config=config
        config.setSTA(self)
        sta=network.WLAN(network.WLAN.IF_STA)
        sta.active(True)
        self.sta=sta
        config.setSTA(sta)
    
#    def disconnect(self):
#        self.sta.disconnect()

    def connect(self):
        ssid=self.config.getSSID()
        password=self.config.getPassword()
        print(ssid,password)
        print('Connecting...',end='')
        self.sta.connect(ssid,password)
        while not self.sta.isconnected():
            time.sleep(1)
            print('.',end='')
        ipaddr=self.sta.ifconfig()[0]
        self.channel=self.sta.config('channel')
        self.config.setIPAddr(ipaddr)
        print(f'{ipaddr} ch {self.channel}')
    
    def getChannel(self): return self.channel
