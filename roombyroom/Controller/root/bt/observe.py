import datetime
from time import sleep
from bleson import get_provider, Observer

def c2f(val):
    return round(32 + 9*val/5, 2)

last = {}

def temp_hum(values, battery, address):
    global last
    # print(values.hex())
    values = int.from_bytes(values, 'big')
    if address not in last or last[address] != values:
        last[address] = values
        temp = float(values / 10000)
        hum = float((values % 1000) / 10)
        print("{0} {1} Temp: {2} F  Humidity: {3} %  Battery: {4} %".format(datetime.datetime.now().isoformat(), address, c2f(temp), hum, battery))

def on_advertisement(advertisement):
    print(dir(advertisement))
    # ['__bytes__', '__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__len__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_name', 'address', 'address_type', 'adv_itvl', 'appearance', 'flags', 'mfg_data', 'name', 'name_is_complete', 'public_tgt_addr', 'raw_data', 'rssi', 'service_data', 'svc_data_uuid128', 'svc_data_uuid16', 'svc_data_uuid32', 'tx_pwr_lvl', 'type', 'uri', 'uuid128s', 'uuid16s', 'uuid32s']

    mfg_data = advertisement.mfg_data
    if mfg_data is not None:
        # print(advertisement)
        if advertisement.name == 'GVH5177_9835':
            address = advertisement.address
            temp_hum(mfg_data[4:7], mfg_data[7], address)
        # elif mfg_data[0] == 0x88:
        elif advertisement.name == 'GVH5075_3A2E':
            address = advertisement.address
            temp_hum(mfg_data[3:6], mfg_data[6], address)
            # print(mfg_data.hex())

# device info
# Advertisement(flags=0x05, name='GVH5075_391D', txpower=None, uuid16s=[UUID16(0xec88)], uuid128s=[], rssi=-29, mfg_data=b'\x88\xec\x00\x03QOd\x00')
# Advertisement(flags=0x05, name='GVH5177_9835', txpower=None, uuid16s=[UUID16(0xec88)], uuid128s=[], rssi=-49, mfg_data=b'\x01\x00\x01\x01\x03l\xbfd')

adapter = get_provider().get_adapter()

observer = Observer(adapter)
observer.on_advertising_data = on_advertisement

observer.start()
while True:
    sleep(60)
observer.stop()
