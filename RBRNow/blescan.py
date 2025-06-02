import asyncio
import aioble
from binascii import hexlify

class BLEScan():
    
    def __init__(self):
        self.values=''

    async def scan(self):
        print("Scanning for BLE devices...")
        while True:
            async with aioble.scan(duration_ms=20000) as scanner:
                async for result in scanner:
                    addr = result.device.addr_hex()
                    if addr.find('a4:c1:38:') == 0:
                        rssi = result.rssi
                        data = hexlify(result.adv_data).decode()
                        if len(data) > 28:
                            temp = int(data[20:24], 16)
                            hum = int(data[24:26], 16)
                            batt = int(data[26:28], 16)
                            print(f'{addr[9:]} {rssi} {temp} {hum} {batt}')
                            self.values = f'{addr[9:]};{rssi};{temp};{hum};{batt}'
#                    else: print(f'{addr} - no')
            await asyncio.sleep(0.1)

    def getValues(self):
        values=self.values
        self.values=''
        return values
