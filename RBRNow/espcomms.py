import asyncio
from binascii import hexlify,unhexlify
from espnow import ESPNow as E

class ESPComms():
    
    def __init__(self,config):
        self.config=config
        config.setESPComms(self)
        E().active(True)
        self.peers=[]
        print('ESP-Now initialised')
    
    def checkPeer(self,peer):
        if not peer in self.peers:
            self.peers.append(peer)
            E().add_peer(peer)

    async def send(self,mac,espmsg):
        peer=unhexlify(mac.encode())
        # Flush any incoming messages
        while E().any(): _,_ = E().irecv()
        self.checkPeer(peer)
        try:
#            print(f'Send {espmsg[0:20]}... to {mac}')
            result=E().send(peer,espmsg)
#            print(f'Result: {result}')
            if result:
                counter=50
                while counter>0:
                    if E().any():
                        mac,response = E().irecv()
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
        print('Starting ESPNow receiver on channel',self.config.getChannel())
        self.waiting=False
        while True:
            if E().any():
                mac,msg=E().recv()
                sender=hexlify(mac).decode()
                msg=msg.decode()
#                print(f'Message from {sender}: {msg[0:30]}...')
                if msg[0]=='!':
                    # It's a message to be relayed
                    comma=msg.index(',')
                    slave=msg[1:comma]
                    msg=msg[comma+1:]
#                    print(f'Slave: {slave}, msg: {msg}')
                    response=await self.send(slave,msg)
                else:
                    # It's a message for me
                    response=self.config.getHandler().handleMessage(msg)
                    response=f'{response} {self.getRSS(sender)}'
                print(f'Response to {sender}: {response}')
                self.checkPeer(mac)
                E().send(mac,response)
            await asyncio.sleep(.1)
            self.config.kickWatchdog()

    def getRSS(self,mac):
        peer=unhexlify(mac.encode())
        try: return E().peers_table[peer][0]
        except: return 0
