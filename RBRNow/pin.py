from machine import Pin

class PIN():

    def __init__(self,config,pin,invert=False):
        if pin=='': self.pin=None
        else: self.pin=Pin(int(pin),mode=Pin.OUT)
        self.invert=invert
        self.off()
        
    def on(self):
        if self.pin==None: return None
        self.state = 'ON'
        if self.invert: self.pin.off()
        else: self.pin.on()
        return self.state            
    
    def off(self):
        if self.pin==None: return None
        self.state = 'OFF'
        if self.invert: self.pin.on()
        else: self.pin.off()
        return self.state            

    def getState(self):
        if self.pin==None: return None
        return self.state            
