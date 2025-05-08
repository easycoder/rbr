import asyncio,dht
from machine import Pin,reset

class DHT22():

    def __init__(self,sensorpin,verbose=False):
        if verbose:
            print('Initialise sensor on pin',sensorpin)
        if sensorpin is not '':
            self.sensor=dht.DHT22(Pin(int(sensorpin)))
        self.verbose=verbose
        self.temp=0
        self.errors=0

    async def measure(self):
        msg=None
        print('Run the temperature sensor')
        while True:
            try:
                self.sensor.measure()
                self.temp=round(self.sensor.temperature(),1)
                if self.verbose:
                    print('Temperature:',self.temp)
                self.errors=0
            except OSError as e:
                if self.verbose:
                    msg=f'Failed to read sensor: {str(e)}'
                    print(msg)
                self.errors+=1
                if self.errors>50: reset()
            await asyncio.sleep(5)

    def getTemperature(self):
        return self.temp
