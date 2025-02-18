import gc,os,asyncio,hardware,maps,functions,state

async def handleClient(reader, writer):
    global resetRequest,pollTotal,currentVersion
    
#    print(f'Client {gc.mem_free()}')

    data = await reader.readline()

    while await reader.readline() != b"\r\n":
        pass

    request = str(data, 'utf-8').split()[1]
    data=None

    req=request.split('?')
    cmd=req[0].split('/')
    cmd=cmd[len(cmd)-1]
    if len(req)>1:
        data=req[1]
        req=None
    else:
        data=None

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
            incomingMap=maps.getIncomingMap()
            data=data[5:].split('|')
            for line in data:
                part=line.split(':')
                if len(part)==2:
                    incomingMap.replace(part[0],line)
                maps.setIncomingMap(incomingMap)
        response=maps.getOutgoingMap()
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
        response=f'{functions.getMyName()} v{maps.getCurrentVersion()} {functions.getMAC()} from {functions.getHostSSID()},{maps.getRSSI()} {hardware.getRelay()} {d}:{h}:{m}:{s}'
    
    data=None
    try:
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        writer.write(response)
        await asyncio.wait_for(writer.drain(),10)
        await asyncio.wait_for(writer.wait_closed(),10)
    except asyncio.TimeoutError as e:
        print(f'Timeout: {str(e)}')
    except Exception as e:
        print(f'Exception: {str(e)}')
    response=None
    gc.collect()
    if resetRequest:
        state.restart()

