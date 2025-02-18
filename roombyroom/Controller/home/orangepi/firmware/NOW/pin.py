from machine import Pin

class PIN():

    def __init__(self,config,name):
        self.pinNo=config.getPinNo(name)
        self.reverse=config.isPinReversed(name)
        self.pin=Pin(int(self.pinNo),mode=Pin.OUT)
        
    def getPinNo(self): return self.pinNo
    def isReversed(self): return self.reverse
        
    def on(self):
        if self.reverse: self.pin.off()
        else: self.pin.on()
    
    def off(self):
        if self.reverse: self.pin.on()
        else: self.pin.off()
