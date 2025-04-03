import asyncio,dht
<<<<<<< HEAD
from machine import Pin,reset
=======
from machine import Pin
>>>>>>> refs/remotes/origin/main

class DHT22():

    def __init__(self,sensorpin,verbose=False):
        if verbose:
            print('Initialise sensor on pin',sensorpin)
<<<<<<< HEAD
        if sensorpin is not '':
            self.sensor=dht.DHT22(Pin(int(sensorpin)))
        self.verbose=verbose
        self.temp=0
        self.errors=0
=======
        self.sensor=dht.DHT22(Pin(int(sensorpin)))
        self.verbose=verbose
>>>>>>> refs/remotes/origin/main

    async def measure(self):
        msg=None
        print('Run the temperature sensor')
        while True:
            try:
                self.sensor.measure()
<<<<<<< HEAD
                self.temp=round(self.sensor.temperature(),1)
                if self.verbose:
                    print('Temperature: %3.1f C' %self.temp)
                self.errors=0
=======
                self.temp=self.sensor.temperature()
                if self.verbose:
                    print('Temperature: %3.1f C' %self.temp)
>>>>>>> refs/remotes/origin/main
            except OSError as e:
                if self.verbose:
                    msg=f'Failed to read sensor: {str(e)}'
                    print(msg)
<<<<<<< HEAD
                self.errors+=1
                if self.errors>50: reset()
            await asyncio.sleep(5)

=======
            await asyncio.sleep(5)
    
>>>>>>> refs/remotes/origin/main
    def getTemperature(self):
        return self.temp
