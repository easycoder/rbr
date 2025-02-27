import asyncio,machine
from binascii import unhexlify
from files import readFile,writeFile,renameFile

class Handler():
    
    def __init__(self,config):
        self.config=config
        config.setHandler(self)
        self.relay=config.getRelay()

    def handleMessage(self,msg):
#        print('Message:',msg)
        response='OK'
        if msg == 'on':
            print('relay ON')
            self.relay.on()
        elif msg == 'off':
            print('relay OFF')
            self.relay.off()
        elif msg == 'reset':
            self.config.reset()
        elif msg == 'uptime':
            response=str(self.config.getUptime())
        elif msg == 'ipaddr':
            response=self.config.getIPAddr()
        elif msg == 'temp':
            response=str(self.config.getTemperature())
        elif msg[0:4]=='part':
        # Format is part:{n},text:{text}
            part=None
            text=None
            items=msg.split(',')
            for item in items:
                item=item.split(':')
                label=item[0]
                value=item[1]
                if label=='part': part=int(value)
                elif label=='text': text=value
            if part!=None and text!=None:
                text=text.encode('utf-8')
                text=unhexlify(text)
                text=text.decode('utf-8')
                if part==0:
                    self.buffer=[]
                    self.pp=0
                    self.saveError=False
                else:
                    if self.saveError:
                        return 'Error'
                    else:
                        if part==self.pp+1:
                            self.pp+=1
                        else:
                            self.saveError=True
                            print('Sequence error')
                            return 'Sequence error'
                self.buffer.append(text)
                response=str(len(text))
        elif msg[0:4]=='save':
            text=''.join(self.buffer)
            if len(text)>0:
                file=msg[5:]
                print(f'Save {file}')
                writeFile('temp',text)
                test=readFile('temp')
                if test==text:
                    renameFile('temp',file)
#                    print(f'Written {file}')
                    response=str(len(text))
                else: response='Bad save'
            else: response='No update'
        elif msg == 'reset':
            print('Reset request')
            asyncio.get_event_loop().stop()
        else:
            response='Unknown message'
        return response
