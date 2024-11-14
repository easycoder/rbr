import gc,os,json,hardware,maps,functions

# Asynchronous function to handle client requests
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
    elif cmd=='poll':
        if data.startswith('data='):
            data=data[5:].replace('%20',' ').replace('%22','"')
            data=json.loads(data)
            for key in data.keys():
                maps.setIncomingMapElement(key,data[key])
        response=json.dumps(maps.getOutgoingMap())
        print(response)
    elif cmd=='getFile':
        print('getFile:',data)
        if len(data)==0:
            response=None
        else:
            response=hardware.readFile(data)
            if len(response)==0:
                response=None
    else:
        pollTotal=maps.getPollTotal()
        d=int(pollTotal/360/24)
        t=pollTotal*10%(3600*24)
        h=int(t/3600)
        t=t%3600
        m=int(t/60)
        s=t%60
        response=f'{functions.getMyName()} v{maps.getCurrentVersion()} {functions.getMAC()} from {functions.getHostSSID()},{functions.getRSSI()} {hardware.getRelay()} {d}:{h}:{m}:{s}'

    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)
    await writer.drain()
    await writer.wait_closed()
    if resetRequest:
        await asyncio.sleep(1)
        machine.reset()
    gc.collect()

