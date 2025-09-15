import asyncio,network,time,random,machine
from espnow import ESPNow

class ESPComms():
    e=ESPNow()
    
    def __init__(self,config):
        self.config=config
        
        if config.isMaster():
            print('Starting as master')
            self.sta=network.WLAN(network.WLAN.IF_STA)
            self.sta.active(True)
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
            self.channel=config.getChannel()
            print('Starting as slave on channel',self.channel)
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
        print(config.getName(),mac)
        if not config.isMaster():
            self.sta=network.WLAN(network.WLAN.IF_STA)
            self.sta.active(True)
            self.sta.config(channel=self.channel)
        
        self.e.active(True)
        print('ESP-Now initialised')
        
        self.requestToSend=False
        self.sending=False

    def closeAP(self):
        password=str(random.randrange(100000,999999))
        print('Password:',password)
        self.ap.config(essid='-',password=password)
            
    def addPeer(self,peer):
        h=peer.hex()
        if not hasattr(self,'peers'):
            self.peers=[]
        if h in self.peers:
            return True
        try:
            self.e.add_peer(peer,channel=self.channel)
        except OSError as ex:
            print(f'Failed to add peer {h} to ESP-NOW: {ex}')
            return False
        self.peers.append(h)
        print('Added',h,'to peers on channel',self.channel)
        return True

    def espSend(self,peer,msg):
        if self.addPeer(peer):
            try: self.e.send(peer,msg)
            except Exception as ex: print('espSend:',ex)
    
    def send(self,mac,msg):
#        print(f'Send {msg[0:20]}... to {mac} on channel {self.channel}')
        self.requestToSend=True
        while not self.sending: await asyncio.sleep(.1)
        self.requestToSend=False
        peer=bytes.fromhex(mac)
        if self.addPeer(peer):
            try:
                result=self.e.send(peer,msg)
                if result:
                    result=None
                    counter=100
                    while counter>0:
                        while self.e.any():
                            _,reply=self.e.irecv()
                            if reply:
                                reply=reply.decode()
                                if reply=='ping': continue
#                                print(f"Received reply: {reply}")
                                result=reply
                                break
                        if result: break
                        await asyncio.sleep(.1)
                        counter-=1
                    if counter==0: result='Fail (no reply)'
                    else:
                        print(f'{msg[0:20]} to {mac}: {result}')
                        self.config.resetCounters()
                else: result='Fail (no result)'
            except Exception as ex:
                result=f'Fail ({ex})'
                print(result)
        else: result='Fail (adding peer)'
        self.sending=False
        return result

    async def receive(self):
        print('Starting ESPNow receiver')
        while True:
            while True:
                if self.e.active():
                    while self.e.any():
                        mac,msg=self.e.recv()
                        msg=msg.decode()
                        print('Received',msg)
                        if msg=='ping':
                            try:
                                self.addPeer(mac)
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
                                response=f'{response} {self.getRSS(mac)}'
                            self.addPeer(mac)
                            try:
                                self.addPeer(mac)
                                self.e.send(mac,response)
                                print(response)
                                self.config.resetCounters()
                                if not self.config.getMyMaster() and not self.config.isMaster():
                                    self.config.setMyMaster(mac.hex())
                            except Exception as ex: print('Can\'t respond',ex)
                    if self.requestToSend:
                        self.sending=True
                        while self.sending: await asyncio.sleep(.1)
                else: print('Not active')
                await asyncio.sleep(.1)
                self.config.kickWatchdog()

    def getRSS(self,mac):
        try: return self.e.peers_table[mac][0]
        except: return 0
