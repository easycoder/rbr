from machine import Pin

class PIN():

    def __init__(self,config,pin,invert=False):
        if pin=='': self.pin=None
        else: self.pin=Pin(int(pin),mode=Pin.OUT)
        self.invert=invert
        
    def on(self):
        if self.pin!=None:
            if self.invert: self.pin.off()
            else: self.pin.on()
    
    def off(self):
        if self.pin!=None:
            if self.invert: self.pin.on()
            else: self.pin.off()

    def getState(self):
        if self.pin==None: return None
        return self.pin.value()            
