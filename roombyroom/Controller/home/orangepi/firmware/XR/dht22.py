import machine, asyncio
from machine import Pin
from time import sleep
import dht

def init():
    global sensor
    sensor = dht.DHT11(Pin(0))
    #sensor = dht.DHT22(Pin(0))

def getTemperature():
    global sensor
    return sensor.temperature()

async def measure():
    global sensor
    while True:
        try:
            sensor.measure()
            temp = sensor.temperature()
            print('Temperature: %3.1f C' %temp)
        except OSError as e:
            print('Failed to read sensor:',e)
        await asyncio.sleep(10)
