import asyncio,machine
from binascii import unhexlify
<<<<<<< HEAD
from files import readFile,writeFile
=======
from files import readFile,writeFile,renameFile
>>>>>>> 627b084 (sync)

class Handler():
    
    def __init__(self,config):
        self.config=config
<<<<<<< HEAD
        self.relay=config.getRelay()

    def handleMessage(self,msg):
        print('Message:',msg)
        response='OK'
        if msg == 'on':
            self.relay.on()
            response='OK'
        elif msg == 'off':
=======
        config.setHandler(self)
        self.relay=config.getRelay()

    def handleMessage(self,msg):
#        print('Message:',msg)
        response='OK'
        if msg == 'on':
            print('relay ON')
            self.relay.on()
            response='OK'
        elif msg == 'off':
            print('relay OFF')
>>>>>>> 627b084 (sync)
            self.relay.off()
            response='OK'
        elif msg == 'uptime':
            response=self.config.getUptime()
        elif msg == 'reset':
            self.config.reset()
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
<<<<<<< HEAD
                response=len(text)
=======
                response=str(len(text))
>>>>>>> 627b084 (sync)
        elif msg[0:4]=='save':
            text=''.join(self.buffer)
            if len(text)>0:
                file=msg[5:]
<<<<<<< HEAD
                writeFile(file,text)
                test=readFile(file)
                if test==text:
#                    print(f'Written {file}')
                    response=len(text)
                else: response='Bad save'
            else: response='No update'
        elif msg == 'reset':
=======
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
>>>>>>> 627b084 (sync)
            asyncio.get_event_loop().stop()
        else:
            response='Unknown message'
        return response
