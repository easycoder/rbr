#!/usr/bin/env python3

import time, os
from bluepy.btle import Scanner

SCAN_DURATION = 10
MY_PREFIX = 'a4:c1:38'

def scan(duration):
    try:
        scanner = Scanner()
        # print('Scanning...')
        devices = scanner.scan(duration)
        # print('Processing...')
        for dev in devices:
            if dev.addr[0:8] == MY_PREFIX:
                adtype, desc, value = dev.getScanData()[0]
                temp = (int(value[16:18], 16) * 256 + int(value[18:20], 16)) / 10
                hum = int(value[20:22], 16)
                batt = int(value[22:24], 16)
                # print(f'{dev.addr}: Temperature: {temp}, Humidity: {hum}, Battery: {batt}, RSSI: {dev.rssi}, RSSI: {dev.rssi}')
                ts = round(time.time())
                dir = '/mnt/data/sensors'
                if not os.path.exists(f'{dir}'):
                    os.makedirs(f'{dir}')
                path = f'{dir}/{dev.addr}.txt'
                file = open(path, 'w')
                message = '{"temperature": "' + str(temp) + '", "timestamp": "' + str(ts) + '", "battery": "' + str(batt)  + '", "RSSI": "' + str(dev.rssi) + '"}'
                # print(message)
                file.write(message)
                file.close()
                os.chmod(path, 0o666)

    except Exception as e:
        pass
        #print("scan: Error, ", e)

if __name__ == '__main__':
    while True:
        scan(SCAN_DURATION)
