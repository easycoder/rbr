import asyncio
from binascii import hexlify,unhexlify
from espnow import ESPNow as E

class ESPComms():
    
    def __init__(self,config):
        self.config=config
        config.setESPComms(self)
        E().active(True)
        print('ESP-Now initialised')
    
    def checkPeer(self,mac):
        try:
            E().get_peer(mac)
        except Exception:
            E().add_peer(mac)

    async def send(self,peer,espmsg):
        mac=unhexlify(peer.encode())
        self.checkPeer(mac)
        print(f'Send {espmsg[0:20]} to {peer}')
        try:
            result=E().send(mac,espmsg)
            if result:
                counter=50
                while counter>0:
                    if E().any():
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
                mac,msg=E().irecv()
                sender=hexlify(mac).decode()
                msg=msg.decode()
#                print(f'Message from {sender}: {msg[0:20]}')
                response=self.config.getHandler().handleMessage(msg)
                self.checkPeer(mac)
                E().send(mac,response)
            await asyncio.sleep(.1)
