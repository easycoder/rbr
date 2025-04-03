from machine import Pin

class PIN():

<<<<<<< HEAD
    def __init__(self,config,pin,invert=False):
        if pin=='': self.pin=None
        else: self.pin=Pin(int(pin),mode=Pin.OUT)
        self.invert=invert
=======
    def __init__(self,config,name):
        self.pinNo=config.getPinNo(name)
        self.invert=config.isPinInverted(name)
        if self.pinNo!='':
            self.pin=Pin(int(self.pinNo),mode=Pin.OUT)
        else: self.pin=None
        
#    def getPinNo(self): return self.pinNo
#    def isReversed(self): return self.reverse
>>>>>>> refs/remotes/origin/main
        
    def on(self):
        if self.pin!=None:
            if self.invert: self.pin.off()
            else: self.pin.on()
    
    def off(self):
        if self.pin!=None:
            if self.invert: self.pin.on()
            else: self.pin.off()
<<<<<<< HEAD

    def getState(self):
        if self.pin!=None:
            value=self.pin.value()
            if self.invert:
                value=1 if value==0 else 0
            return value
        else:
            return None
=======
>>>>>>> refs/remotes/origin/main
