import network,asyncio,time,urequests

def connect(hostssid,hostpass):
    station = network.WLAN(network.STA_IF)
    station.active(True)
    print('Connect to',hostssid,hostpass)
    station.connect(hostssid,hostpass)
    while station.isconnected()==False:
        time.sleep(1)
        print('.',end='')
    print('\nConnected:',station.ifconfig())

async def run():
    url='http://192.168.66.1/test'
    print('Poll',url)
    response = urequests.get(url)
    print(response.text)
    response.close()

connect('myserver','00000000')
event_loop = asyncio.get_event_loop()
event_loop.create_task(run())
event_loop.run_forever()