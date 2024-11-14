import machine,time,json,asyncio,maps,hardware,functions,urlencode,dht22

async def poll(myname):
    pollError=0
    currentVersion=hardware.readFile('version')
    if currentVersion==None:
        currentVersion=0
    maps.setCurrentVersion(currentVersion)
    while (True):
        await asyncio.sleep(2)
        incomingMap=maps.getIncomingMap()
        data=urlencode.encode(json.dumps(incomingMap))
        url='http://'+functions.getServer()+'/poll?data='+data
        try:
            response=await functions.httpGET(url)
            outgoingMap=json.loads(response)
            maps.setOutgoingMap(outgoingMap)
            print('Outgoing:',outgoingMap)
            if myname in outgoingMap:
                state=outgoingMap[myname]['relay']
            else:
                state='off'
            hardware.setRelay(state)
            if 'ts' in outgoingMap:
                ts = outgoingMap['ts']
            else:
                ts = '0'
            incomingMap[myname]=json.loads('{"ts":"'+ts+'"}')
            if hardware.fileExists('therm'):
                state='-'
                incomingMap[myname]['t']=dht22.getTemperature()
            info=f'{functions.getHostSSID()},{functions.getMAC()},{state},{maps.getPollTotal()},{functions.getRSSI()}'
            incomingMap[myname]['i']=info
            maps.setIncomingMap(incomingMap)
            
            if 'v' in outgoingMap:
                version=outgoingMap['v']
            else:
                version='1'
            maps.bumpPoll()
            if int(version)>int(currentVersion):
                print('Update required')
                hardware.writeFile('update',version)
                return
        except Exception as e:
            print(f'Poll error {pollError}: {e}')
            pollError+=1
            if pollError>20:
                return
