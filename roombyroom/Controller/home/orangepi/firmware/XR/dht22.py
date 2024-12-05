import asyncio,dht,state
from machine import Pin

def init():
    global sensor
    print('Initialise sensor')
    #sensor = dht.DHT11(Pin(4))
    sensor=dht.DHT22(Pin(4)) # ESP12 D2

def getTemperature():
    global sensor
    return sensor.temperature()

async def measure():
    global sensor
    errorCount=0
    running=True
    msg=None
    print('Run the temperature sensor')
    while running:
        try:
            sensor.measure()
            await asyncio.sleep(1)
            temp=sensor.temperature()
            print('Temperature: %3.1f C' %temp)
            errorCount=0
        except OSError as e:
            errorCount+=1
            msg=f'Failed to read sensor ({errorCount}): {str(e)}'
            print(msg)
            if errorCount>10:
                running=False
        await asyncio.sleep(9)
    state.error(msg)

