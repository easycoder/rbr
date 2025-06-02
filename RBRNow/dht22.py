import asyncio,dht
from machine import Pin,reset

class DHT22():

    def __init__(self,sensorpin,verbose=False):
        if verbose:
            print('Initialise sensor on pin',sensorpin)
        if sensorpin is '': self.sensor=None
        else: self.sensor=dht.DHT22(Pin(int(sensorpin)))
        self.verbose=verbose
        self.temp=0
        self.errors=0
        self.paused=False

    async def measure(self):
        if self.sensor==None: return
        msg=None
        print('Run the temperature sensor')
        while True:
            if not self.paused:
                try:
                    self.sensor.measure()
                    temperature=self.sensor.temperature()
                    if temperature>50: temperature=0
                    self.temp=round(temperature*10)
                    if self.verbose:
                        print('Temperature:',temperature)
                    self.errors=0
                except OSError as e:
                    if self.verbose:
                        msg=f'Failed to read sensor: {str(e)}'
                        print(msg)
                    self.errors+=1
                    if self.errors>50: reset()
            await asyncio.sleep(5)
    
    def pause(self):
        self.paused=True
    
    def resume(self):
        self.paused=False

    def getTemperature(self):
        return self.temp
