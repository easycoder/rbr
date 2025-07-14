import asyncio,machine
from binascii import unhexlify
from files import readFile,writeFile,renameFile,deleteFile,createDirectory

class Handler():
    
    def __init__(self,config):
        self.config=config
        config.setHandler(self)
        self.relay=config.getRelay()

    def checkFile(self, buf, file):
        try:
            with open(file, 'r') as f:
                i = 0  # index in lst
                pos = 0  # position in current list item
                while True:
                    c = f.read(1)
                    if not c:
                        # End of file: check if we've also finished the list
                        while i < len(buf) and pos == len(buf[i]):
                            i += 1
                            pos = 0
                        return i == len(buf)
                    if i >= len(buf) or pos >= len(buf[i]) or c != buf[i][pos]:
                        return False
                    pos += 1
                    if pos == len(buf[i]):
                        i += 1
                        pos = 0
        except OSError:
            return False

    def handleMessage(self,msg):
#        print('Message:',msg)
        response=f'OK {self.config.getUptime()} :{self.config.getBLEScan().getValues()}'
        if msg == 'uptime':
            pass
        elif msg == 'on':
            response=f'{response} ON' if self.relay.on() else 'No relay'
        elif msg == 'off':
            response=f'{response} OFF' if self.relay.off() else 'No relay'
        elif msg == 'relay':
            try:
                response=f'OK {self.relay.getState()}'
            except:
                response='No relay'
        elif msg=='reset':
            self.config.reset()
            response='OK'
        elif msg == 'ipaddr':
            response=f'OK {self.config.getIPAddr()}'
        elif msg=='channel':
            response=f'OK {self.config.getChannel()}'
        elif msg[0:8]=='channel=':
            channel=msg[8:]
            self.config.setChannel(channel)
            response=f'OK {channel}'
        elif msg=='temp':
            response=f'OK {self.config.getTemperature()}'
        elif msg=='pause':
            self.config.pause()
            response=f'OK paused'
        elif msg=='resume':
            self.config.resume()
            response=f'OK resumed'
        elif msg[0:6]=='delete':
            file=msg[7:]
            response='OK' if deleteFile(file) else 'Fail'
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
            if len(self.buffer[0])>0:
                file=msg[5:]
                print(f'Save {file}')
                size=0
                f = open(file,'w')
                for n in range(0, len(self.buffer)):
                    f.write(self.buffer[n])
                    size+= len(self.buffer[n])
                f.close()
                # Check the file against the buffer
                if self.checkFile(self.buffer, file): response=str(size) 
                else: response='Bad save'
            else: response='No update'
            text=None
        elif msg[0:5]=='mkdir':
            path=msg[6:]
            print(f'mkdir {path}')
            response='OK' if createDirectory(path) else 'Fail'
        else: response=f'Unknown message: {msg}'
#        print('Handler:',response)
        return response


