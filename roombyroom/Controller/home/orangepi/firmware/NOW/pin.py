from machine import Pin

class PIN():

    def __init__(self,config,name):
        self.pinNo=config.getPinNo(name)
        self.invert=config.isPinInverted(name)
        if self.pinNo!='':
            self.pin=Pin(int(self.pinNo),mode=Pin.OUT)
        else: self.pin=None
        
#    def getPinNo(self): return self.pinNo
#    def isReversed(self): return self.reverse
        
    def on(self):
        if self.pin!=None:
            if self.invert: self.pin.off()
            else: self.pin.on()
    
    def off(self):
        if self.pin!=None:
            if self.invert: self.pin.on()
            else: self.pin.off()
