# ESP32 code to handle Mijia thermometer

from binascii import hexlify
from bluetooth import BLE
from micropython import const
from time import localtime, sleep
from struct import unpack

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_MAC = 'a4:c1:38:91:cc:14'


def log(*args):
    y, mo, d, h, mi, s, wkd, yd = localtime()
    print("[{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]".format(y, mo, d, h, mi, s), *args)


def handle_scan(ev, data):
    if ev == _IRQ_SCAN_RESULT:
        addr = hexlify(data[1], ":").decode()
        if addr != _MAC:
            return
        #print("Data:", data)
        rssi = data[3]
        params = data[4]
        #log("Device {0} (RSSI {1}, {2}):".format(addr, rssi, list(params)))
        temp = params[10] * 256 + params[11]
        hum = params[12]
        batt = params[13]
        log("Temperature: {0}, Humidity: {1}, Battery: {2}".format(temp/10, hum, batt))
    elif ev == _IRQ_SCAN_DONE:
        log("Scan done.")
    else:
        log("Unexpected event: {0}".format(ev))

BLE().active(True)
BLE().irq(handle_scan)
log("Starting passive scan. Detection can take seconds or even minutes.")
BLE().gap_scan(0, 55_000, 25_250)  # scan often & indefinitely

# You could add your own code here, the scanning runs in the background.
# We explicitly do nothing, simply to prevent the script from ending.
while True:
    sleep(5)

