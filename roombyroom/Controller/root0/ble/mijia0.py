#!/usr/bin/env python3

from bluepy import btle
from bluepy.btle import Scanner

SCAN_DURATION = 10
MY_ADDRESS = 'a4:c1:38:91:cc:14'

def scan(duration):
    try:
        scanner = Scanner()
        devices = scanner.scan(duration)
        for dev in devices:
            if dev.addr == MY_ADDRESS:
                adtype, desc, value = dev.getScanData()[0]
                # print(value)
                temp = (int(value[16:18], 16) * 256 + int(value[18:20], 16)) / 10
                hum = int(value[20:22], 16)
                batt = int(value[22:24], 16)
                print(f'Temperature: {temp}, Humidity: {hum}, Battery: {batt}')
    except Exception as e:
        print("scan: Error, ", e)

if __name__ == '__main__':
    while True:
        scan(SCAN_DURATION)
