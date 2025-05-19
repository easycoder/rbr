import asyncio,machine
from binascii import unhexlify
from files import readFile,writeFile,renameFile,deleteFile

class Handler():
    
    def __init__(self,config):
        self.config=config
        config.setHandler(self)
        self.relay=config.getRelay()

    def handleMessage(self,msg):
#        print('Message:',msg)
        response=f'OK {self.config.getUptime()}'
        if msg == 'uptime':
            pass
        elif msg == 'on':
            try:
                self.relay.on()
                response=f'{response} {self.relay.getState()}'
            except:
                response='No relay'
        elif msg == 'off':
            try:
                self.relay.off()
                response=f'{response} {self.relay.getState()}'
            except:
                response='No relay'
        elif msg == 'relay':
            try:
                response=f'OK {self.relay.getState()}'
            except:
                response='No relay'
        elif msg == 'reset':
            self.config.reset()
        elif msg == 'ipaddr':
            response=f'OK {self.config.getIPAddr()}'
        elif msg == 'temp':
            response=f'OK {self.config.getTemperature()}'
        elif msg=='pause':
            self.config.pause()
            response=f'OK paused'
        elif msg=='resume':
            self.config.resume()
            response=f'OK resumed'
        elif msg[0:6]=='delete':
            file=msg[7:]
            deleteFile(file)
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
                response=f'{part} {str(len(text))}'
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
        else:
            response=f'Unknown message: {msg}'
#        print('Handler:',response)
        return response

