from machine import Pin

led = Pin(2, Pin.OUT)
led.on()

import esp
esp.osdebug(None)

import gc
gc.collect()
