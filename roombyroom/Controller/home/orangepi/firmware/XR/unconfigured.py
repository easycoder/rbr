# Import necessary modules
import os,network,asyncio,socket,ubinascii,time,machine,hardware,config
from machine import Pin

def info():
    print('This handles unconfigured mode')

# Asynchronous function to handle client's requests
async def handle_client(reader, writer):
    request_line = await reader.readline()
#    print('Request:', request_line)

    # Skip HTTP request headers
    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line, 'utf-8').split()[1]
#    print('Request:', request)

    req=request.split('?')
    cmd=req[0].split('/')
    cmd=cmd[len(cmd)-1]
    if len(req)>1:
        args=req[1].split()
        args=args[0].replace('%27','\'')
    else:
        args=None
    print(cmd,args)
    
    # Generate HTML response
    import hardware
    resetRequest=False
    response = 'OK'
    if cmd is 'config':
        response=hardware.readFile('config.html')
    elif cmd is 'setup':
        await config.writeConfig(args,reader,writer)
        await asyncio.sleep(1)
        response=hardware.readFile('ack.html')
        resetRequest=True
    else:
        try:
            rssi=ap.status('rssi')
        except:
            rssi=''
        response=f'SSID: {myssid} {rssi}'

    # Send the HTTP response and close the connection
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write('<!DOCTYPE HTML><html lang="en"><head></head><body>'+response+'</body></html>')
    await writer.drain()
    await writer.wait_closed()
    if resetRequest:
        await asyncio.sleep(1)
        machine.reset()

async def blink():
    hardware.setupLED()
    while True:
        hardware.setLED(True)
        await asyncio.sleep(0.5)
        hardware.setLED(False)
        await asyncio.sleep(0.5)

async def main():
    global ap,myssid
    ap=network.WLAN(network.AP_IF)
    myssid='RBR-xr-' + ubinascii.hexlify(ap.config('mac')).decode()[6:]
    print('Set up AP for',myssid)
    ap.active(True)
    ap.config(essid=myssid, authmode=3, password='00000000')
    ap.ifconfig(('192.168.9.1', '255.255.255.0', '192.168.9.1', '8.8.8.8'))

    timeout=60
    while not ap.active():
        await asyncio.sleep(1)
        timeout-=1
        if timeout==0:
            print('\nCan\'t set up AP')
            await asyncio.sleep(1)
            machine.reset()

    # Start the server and run the event loop
    server = asyncio.start_server(handle_client, "0.0.0.0", 80)
    asyncio.create_task(server)
    print('Server running')
    asyncio.create_task(blink())

    while True:
        await asyncio.sleep(10)

def run():
    print('Unconfigured')
    asyncio.create_task(main())
    try:
        asyncio.get_event_loop().run_forever()
    except:
        pass

run()
