import urlencode,network,asyncio,socket,gc
import ubinascii,time,json,os,machine,urlencode
import hardware,functions,handleClient,maps

myName=None

async def handleClient(reader, writer):
    global resetRequest,pollTotal,currentVersion

    request_line = await reader.readline()

    # Skip HTTP request headers
    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line, 'utf-8').split()[1]

    req=request.split('?')
    cmd=req[0].split('/')
    cmd=cmd[len(cmd)-1]
    if len(req)>1:
        data=req[1].split()
        data=data[0].replace('%27','\'')
    else:
        data=None

    # Generate HTML response
    resetRequest=False
    if cmd is 'config':
        response=hardware.readFile('config.html')
    elif cmd=='reboot':
        response='reboot'
        resetRequest=True
    elif cmd=='reset':
        response='Factory reset'
        os.remove('config.json');
        resetRequest=True
    elif cmd=='run':
        response='Exit debugger'
        os.remove('debug');
        resetRequest=True
    elif cmd=='on':
        response='Relay on'
        hardware.setRelay('on')
    elif cmd=='off':
        response='Relay off'
        hardware.setRelay('off')
    else:
        response=f'Debug: {functions.getMyName()} v{maps.getCurrentVersion()} {functions.getMySSID()} {hardware.getRelay()}'

    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)
    await writer.drain()
    await writer.wait_closed()
    if resetRequest:
        await asyncio.sleep(1)
        machine.reset()
    gc.collect()

async def main():
    pollError=0
    currentVersion=hardware.readFile('version')
    if currentVersion==None:
        currentVersion=0
    maps.setCurrentVersion(currentVersion)
    myname=functions.getMyName()
    
    maps.setIncomingMapElement(myname,json.loads('{"ts":"0"}'))
    maps.clearPollCount()

    await functions.setupAP()
    server = asyncio.start_server(handleClient, "0.0.0.0", 80)
    asyncio.create_task(server)
    print('Server running')

def run():
    print('XR Debugger')
    hardware.setupPins()
    functions.getConfigData()
#    functions.connect()

    loop = asyncio.get_event_loop()
    loop.create_task(main())

    try:
        # Run the event loop indefinitely
        loop.run_forever()
    except Exception as e:
        print('Error occured: ', e)
        hardware.writeFile('update', currentVersion)
        raise(e)
    except KeyboardInterrupt:
        print('Program interrupted')

run()
