import json,asyncio,machine
from files import readFile,writeFile,fileExists,deleteFile
from pin import PIN
from server import Server
from dht22 import DHT22
from handler import Handler
from blescan import BLEScan
from espcomms import ESPComms
from channels import Channels

class Config():

    def __init__(self):
        if fileExists('config.json'):
            self.config=json.loads(readFile('config.json'))
        else:
            self.config={}
            self.config['name']='(none)'
            self.config['master']=False
            self.config['myMaster']=''
            self.config['path']=''
            self.config['channel']=1
            self.config['pins']={}
            pin={}
            pin['pin']=''
            pin['invert']=False
            self.config['pins']['led']=pin
            pin={}
            pin['pin']=''
            pin['invert']=False
            self.config['pins']['relay']=pin
            pin={}
            pin['pin']=''
            self.config['pins']['dht22']=pin
            writeFile('config.json',json.dumps(self.config))
        try: self.channel=int(self.config['channel'])
        except: self.channel=1
        self.master=self.config['master']
        if self.master: self.myMaster=''
        elif 'myMaster' in self.config:
            self.myMaster=self.config['myMaster']
        else: self.myMaster=''
        pin,invert=self.getPinInfo('led')
        self.led=PIN(self,pin,invert)
        pin,invert=self.getPinInfo('relay')
        self.relay=PIN(self,pin,invert)
        pin,_=self.getPinInfo('dht22')
        if pin=='': self.dht22=None
        else:
            self.dht22=DHT22(pin)
            asyncio.create_task(self.dht22.measure())
        self.ipaddr=None
        self.uptime=0
        self.hop=True
        self.resetRequested=False
        self.server=Server(self)
        self.handler=Handler(self)
        print('Config: set up comms')
        self.espComms=ESPComms(self)
        asyncio.create_task(self.runWatchdog())

    async def handleClient(self,reader,writer):
        await self.server.handleClient(reader,writer)

    async def send(self,peer,espmsg): return await self.espComms.send(peer,espmsg)
    
    def reset(self):
        print('Reset requested')
        self.resetRequested=True
    
    def clearAndReset(self):
        deleteFile('config.json')
        machine.reset()
    
    def pause(self):
        if self.dht22!=None: self.dht22.pause()
    
    def resume(self):
        if self.dht22!=None: self.dht22.resume()
    
    def doFinalInitTasks(self):
        print('Final startup tasks')
        self.server.startup()
        asyncio.create_task(self.espComms.receive())
        self.bleScan=BLEScan()
        asyncio.create_task(self.bleScan.scan())
        self.channels=Channels(self.espComms)
        if self.master: self.channels.setupSlaveTasks()

    def resetCounters(self):
        if hasattr(self,'channels'): self.channels.resetCounters()

    def setAP(self,ap): self.ap=ap
    def setSTA(self,sta): self.sta=sta
    def setESPComms(self,espComms): self.espComms=espComms 
    def setMAC(self,mac): self.mac=mac
    def setIPAddr(self,ipaddr): self.ipaddr=ipaddr
    def setEnviron(self,environ):
        print('environ:',environ)
        items=environ.split('-')
        self.channel=int(items[0])
        self.config['channel']=self.channel
        self.myMaster=items[1]
        self.config['myMaster']=self.myMaster
        writeFile('config.json',json.dumps(self.config))
        print('envron:',json.dumps(self.config))
    def setChannel(self,channel):
        print('Set channel',channel)
        self.channel=channel
        self.config['channel']=channel
        writeFile('config.json',json.dumps(self.config))
    def getChannel(self):
        return self.espComms.channel if self.isMaster() else self.channel
    def setMyMaster(self,myMaster):
        print('Setting myMaster to',myMaster)
        self.myMaster=myMaster
        self.config['myMaster']=myMaster
        writeFile('config.json',json.dumps(self.config))
    def getMyMaster(self): return self.myMaster
    def setHandler(self,handler): self.handler=handler
    def addUptime(self,t): self.uptime+=t
    
    def isMaster(self): return self.master
    def apIsOpen(self): return self.espComms.apIsOpen()
    def getDevice(self): return self.config['device']
    def getName(self): return self.config['name'].replace(' ','_')
    def getSSID(self): return self.config['hostssid']
    def getPassword(self): return self.config['hostpass']
    def getMAC(self): return self.mac
    def closeAP(self): self.espComms.closeAP()
    def getIPAddr(self): return self.ipaddr
    def getHandler(self): return self.handler
    def getESPComms(self): return self.espComms
    def getBLEValues(self):
        return self.bleScan.getValues() if hasattr(self,'bleScan') else ''
    def getRBRNow(self): return self.rbrNow
    def getPinInfo(self,name):
        pin=self.config['pins'][name]
        print(name,pin)
        if 'invert' in pin: invert=pin['invert']
        else: invert=False
        return pin['pin'],invert
    def getLED(self): return self.led
    def getRelay(self): return self.relay
    def getUptime(self): return int(round(self.uptime))
    def getTemperature(self): return self.dht22.getTemperature()

    async def runWatchdog(self):
        while True:
            self.active=False
            await asyncio.sleep(180)
            if not self.active:
                print('No activity - reset')
                asyncio.get_event_loop().stop()
                machine.reset()

    def kickWatchdog(self):
        self.active=True

