import asyncio,network,time,random,machine
from channels import Channels
from espnow import ESPNow

class ESPComms():
    e=ESPNow()
    
    def __init__(self,config):
        self.config=config
        
        self.sta=network.WLAN(network.WLAN.IF_STA)
        self.sta.active(True)
        if config.isMaster():
            print('Starting as master')
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
            print(f'{ipaddr}')
        else:
            print('Starting as slave')
            self.channel=config.getChannel()
        ap=network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(channel=self.channel)
        mac=ap.config('mac').hex()
        config.setMAC(mac)
        self.ssid=f'RBR-Now-{mac}'
        ap.config(essid=self.ssid,password='00000000')
        ap.ifconfig(('192.168.9.1','255.255.255.0','192.168.9.1','8.8.8.8'))
        self.ap=ap
        config.setAP(ap)
        print(config.getName(),mac,'channel',self.channel)
        config.startServer()
        
        self.espnowLock=asyncio.Lock()
        self.e.active(True)
        self.peers=[]
        print('ESP-Now initialised')
        
        self.channels = Channels(self)

    def stopAP(self):
        password=str(random.randrange(100000,999999))
        print('Password:',password)
        self.ap.config(essid='-',password=password)
    
    def checkPeer(self,peer):
        if not peer in self.peers:
            self.peers.append(peer)
            self.e.add_peer(peer,channel=self.channel)

    async def send(self,mac,espmsg):
        peer=bytes.fromhex(mac)
        # Flush any incoming messages
        while self.e.any(): _,_=self.e.irecv()
        self.checkPeer(peer)
        try:
            print(f'Send {espmsg[0:20]}... to {mac} on channel {self.channel}')
            result=self.e.send(peer,espmsg)
#            print(f'Result: {result}')
            if result:
                counter=50
                while counter>0:
                    if self.e.any():
                        mac,response = self.e.irecv()
                        if response:
#                            print(f"Received response: {response.decode()}")
                            result=response.decode()
                            break
                    await asyncio.sleep(.1)
                    counter-=1
                if counter==0:
                    result='Response timeout'
            else: result='Fail (no result)'
        except Exception as e:
            print(e)
            result=f'Fail ({e})'
        return result

    async def receive(self):
        print('Starting ESPNow receiver')
        self.channels.resetCounters()
        while True:
            if self.e.active() and self.e.any():
                async with self.espnowLock:
                    mac,msg=self.e.recv()
                    sender=mac.hex()
                    msg=msg.decode()
                    if msg[0]=='!':
                        # It's a message to be relayed
                        comma=msg.index(',')
                        slave=msg[1:comma]
                        msg=msg[comma+1:]
#                        print(f'Slave: {slave}, msg: {msg}')
                        response=await self.send(slave,msg)
                    else:
                        # It's a message for me
                        response=self.config.getHandler().handleMessage(msg)
                        response=f'{response} {self.getRSS(sender)}'
                    print(f'{msg[0:30]}... {response}')
                    self.checkPeer(mac)
                    try:
                        self.e.send(mac,response)
                        self.channels.resetCounters()
                    except: print('Can\'t respond')
            await asyncio.sleep(.1)
            self.config.kickWatchdog()

    def getRSS(self,mac):
        peer=bytes.fromhex(mac)
        try: return self.e.peers_table[peer][0]
        except: return 0
