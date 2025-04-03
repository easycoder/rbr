<<<<<<< HEAD
import os,network,asyncio,socket,ubinascii,time,machine,hardware,config
=======
import os,network,asyncio,socket,ubinascii,time,machine,hardware
>>>>>>> refs/remotes/origin/main
from machine import Pin

async def handle_client(reader, writer):
    request_line = await reader.readline()

    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line, 'utf-8').split()[1]

    req=request.split('?')
    cmd=req[0].split('/')
    cmd=cmd[len(cmd)-1]
    if len(req)>1:
        args=req[1].split()
        args=args[0].replace('%27','\'')
    else:
        args=None
    print(cmd,args)
    
<<<<<<< HEAD
    import hardware
=======
>>>>>>> refs/remotes/origin/main
    resetRequest=False
    response = 'OK'
    if cmd is 'config':
        parts=args.split('=')
        name=parts[0]
        value=parts[1]
        hardware.writeFile(f'config/{name}', value)
        response=f'{cmd}: OK'
    elif cmd is 'get':
        response=hardware.readFile(f'config/{args}')
    else:
        try:
            rssi=ap.status('rssi')
        except:
            rssi=''
        response=f'SSID: {myssid} {rssi}'

<<<<<<< HEAD
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write('<!DOCTYPE HTML><html lang="en"><head></head><body>'+response+'</body></html>')
=======
    print('Response:', response)
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n')
    writer.write(response)
>>>>>>> refs/remotes/origin/main
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

    server = asyncio.start_server(handle_client, "0.0.0.0", 80)
    asyncio.create_task(server)
    print('Server running')
    asyncio.create_task(blink())

    while True:
        await asyncio.sleep(10)

def run():
    print('Unconfigured')
    hardware.createDirectory('config')
    asyncio.create_task(main())
    try:
        asyncio.get_event_loop().run_forever()
    except:
        pass
