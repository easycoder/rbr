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
            print(f'{ipaddr} ch {self.channel}')
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
        print('ESP-Now initialised')
        
        if not config.isMaster() and config.getMyMaster()!=None: self.channels=Channels(self)
        self.requestToSend=False
        self.sending=False

    def closeAP(self):
        password=str(random.randrange(100000,999999))
        print('Password:',password)
        self.ap.config(essid='-',password=password)
    
    def addPeer(self,peer):
        h=peer.hex()
        if not hasattr(self,'peers'): self.peers=[]
        if not h in self.peers:
            self.peers.append(h)
            self.e.add_peer(peer,channel=self.channel)
            print('Added',h,'to peers')

    def send(self,mac,msg):
#        print(f'Send {msg[0:20]}... to {mac} on channel {self.channel}')
        self.requestToSend=True
        while not self.sending: await asyncio.sleep(.1)
        self.requestToSend=False
        peer=bytes.fromhex(mac)
        self.addPeer(peer)
        try:
            result=self.e.send(peer,msg)
            if result:
                counter=100
                while counter>0:
                    if self.e.any():
                        _,reply = self.e.irecv()
                        if reply:
#                           print(f"Received reply: {reply.decode()}")
                            result=reply.decode()
                            break
                    await asyncio.sleep(.1)
                    counter-=1
                if counter==0: result='Fail (no reply)'
                else:
                    print(f'{msg[0:20]} to {mac}: {result}')
                    self.resetCounters()
            else: result='Fail (no result)'
        except Exception as e:
            print(e)
            result=f'Fail ({e})'
        self.sending=False
        return result

    async def receive(self):
        print('Starting ESPNow receiver')
        tick=0
        if self.config.isMaster():
            while True:
                if self.e.active():
                    while self.e.any():
                        mac,msg=self.e.recv()
                        msg=msg.decode()
#                        print('Message:',msg)
                        if msg=='ping':
                            try:
                                self.addPeer(mac)
                                self.e.send(mac,'pong')
                            except Exception as ex: print('ping:',ex)
                    if self.requestToSend:
                        self.sending=True
                        while self.sending: await asyncio.sleep(.1)
                else: print('Not active')
                await asyncio.sleep(.1)
                tick+=1
                if tick>600:
                    print('tick')
                    tick=0

        else:
            self.resetCounters()
            while True:
                if self.e.active():
                    while self.e.any():
                        mac,msg=self.e.recv()
                        msg=msg.decode()
                        if msg=='ping':
                            try:
                                checkPeer(mac)
                                self.e.send(mac,'pong')
                            except Exception as ex: print('ping:',ex)
                        else:
                            if msg[0]=='!':
                                # It's a message to be relayed
                                comma=msg.index(',')
                                slave=msg[1:comma]
                                msg=msg[comma+1:]
    #                            print(f'Slave: {slave}, msg: {msg}')
                                response=await self.send(slave,msg)
                            else:
                                # It's a message for me
                                response=self.config.getHandler().handleMessage(msg)
                                response=f'{response} {self.getRSS()}'
                            print(f'{msg[0:30]}... {response}')
                            self.addPeer(mac)
                            try:
                                self.e.send(mac,response)
                                self.resetCounters()
                            except Exception as ex: print('Can\'t respond',ex)
                await asyncio.sleep(.1)
                self.config.kickWatchdog()

    def getRSS(self):
        try: return self.e.peers_table[self.sender][0]
        except: return 0

    def resetCounters(self):
        if hasattr(self,'channels'): self.channels.resetCounters()

    def resetCounters(self):
        if hasattr(self,'channels'): self.channels.resetCounters()
