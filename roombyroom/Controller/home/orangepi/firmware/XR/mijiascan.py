from bluetooth import BLE
from micropython import const
from time import localtime, sleep
from binascii import hexlify
from struct import unpack

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)

def log(*args):
    y, mo, d, h, mi, s, wkd, yd = localtime()
    print("[{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}]".format(y, mo, d, h, mi, s), *args)

def handle_scan(ev, data):
    if ev == _IRQ_SCAN_RESULT:
        addr = hexlify(data[1], ":").decode()
        if addr[0:8] == 'a4:c1:38':
            rssi = data[3]
            content = hexlify(data[4],":").decode()
            temp = int(content[30]+content[31]+content[33]+content[34],16)
            hum = int(content[36]+content[37],16)
            batt = int(content[39]+content[40],16)
            log(addr,rssi,temp,hum,batt)
    elif ev == _IRQ_SCAN_DONE:
        log("Scan done.")
    else:
        log("Unexpected event: {0}".format(ev))

BLE().active(True)
BLE().irq(handle_scan)
BLE().gap_scan(0)  # default

# You could add your own code here, the scanning runs in the background.
# We explicitly do nothing, simply to prevent the script from ending.
while True:
    sleep(5)