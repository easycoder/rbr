#!/usr/bin/env python3

from bluepy.btle import Scanner, DefaultDelegate

SCAN_DURATION = 10
MY_PREFIX = 'a4:c1:38'
MY_ADDRESS = 'a4:c1:38:91:cc:14'

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if dev.addr[0:8] == MY_PREFIX:
            try:
                adtype, desc, value = dev.getScanData()[0]
                # print(value)
                temp = (int(value[16:18], 16) * 256 + int(value[18:20], 16)) / 10
                hum = int(value[20:22], 16)
                batt = int(value[22:24], 16)
                print(f'{dev.addr}: RSSI: {dev.rssi}, Temperature: {temp}, Humidity: {hum}, Battery: {batt}')
            except:
                pass

while True:
    Scanner().withDelegate(ScanDelegate()).scan(SCAN_DURATION)
