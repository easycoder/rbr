import asyncio,dht
from machine import Pin

class DHT22():

    def __init__(self,sensorpin,verbose=False):
        if verbose:
            print('Initialise sensor on pin',sensorpin)
        self.sensor=dht.DHT22(Pin(int(sensorpin)))
        self.verbose=verbose

    async def measure(self):
        msg=None
        print('Run the temperature sensor')
        while True:
            try:
                self.sensor.measure()
                self.temp=self.sensor.temperature()
                if self.verbose:
                    print('Temperature: %3.1f C' %self.temp)
            except OSError as e:
                if self.verbose:
                    msg=f'Failed to read sensor: {str(e)}'
                    print(msg)
            await asyncio.sleep(5)
    
    def getTemperature(self):
        return self.temp
