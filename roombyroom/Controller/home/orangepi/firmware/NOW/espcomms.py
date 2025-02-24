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
    
    def checkPeer(self,mac):
        if not mac in self.peers:
            self.peers.append(mac)
            E().add_peer(mac)

    async def send(self,peer,espmsg):
        mac=unhexlify(peer.encode())
        self.checkPeer(mac)
        try:
            print(f'Send {espmsg[0:20]}... to {peer}')
            result=E().send(mac,espmsg)
            print(f'Result: {result}')
            result=True
            if result:
                counter=50
                while counter>0:
                    if E().any():
                        print('Reply received')
                        sender,response = E().irecv()
                        if response:
                            print(f"Received response: {response.decode()}")
                            result=response.decode()
                            break
                    await asyncio.sleep(.1)
                    counter-=1
                if counter==0:
                    result='Response timeout'
            else: result='Fail'
        except Exception as e:
            print(e)
            result='Fail'
        return result

    async def receive(self):
        print('Starting ESPNow receiver on channel',self.config.getChannel())
        self.waiting=False
        while True:
            if E().any():
                mac,msg=E().recv()
                sender=hexlify(mac).decode()
                msg=msg.decode()
                print(f'Message from {sender}: {msg[0:20]}...')
                response=self.config.getHandler().handleMessage(msg)
                print('Response',response)
                self.checkPeer(mac)
                E().send(mac,response)
            await asyncio.sleep(.1)

