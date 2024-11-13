import urlencode,network,asyncio,socket,gc
import ubinascii,time,json,os,machine,urlencode
import hardware,functions,handleClient,maps,dht22

myName=None
resetRequest=False

def reset():
    time.sleep(1)
    machine.reset()

async def clientHandler(reader,writer):
    await handleClient.handleClient(reader,writer)

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
    server = asyncio.start_server(clientHandler, "0.0.0.0", 80)
    asyncio.create_task(server)
    print('Server running')

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
            info=f'{functions.getMySSID()},{maps.getPollTotal()},{functions.getRSSI()}'
            incomingMap[myname]['i']=info
            if hardware.fileExists('temp'):
                incomingMap[myname]['t']=dht22.getTemperature()
            maps.setIncomingMap(incomingMap)
            if 'v' in outgoingMap:
                version=outgoingMap['v']
            else:
                version='1'
            maps.bumpPoll()
            if int(version)>int(currentVersion):
                print('Update required')
                hardware.writeFile('update',version)
                reset()
        except Exception as e:
            print('Poll error',pollError,e)
            pollError+=1
            if pollError>20:
                reset()

async def watchdog():
    while True:
        await asyncio.sleep(60)
        pollCount=maps.getPollCount()
        print('Poll count:',pollCount)
        if pollCount==0:
            print('Timeout')
            reset()
        maps.clearPollCount()

async def temperature():
    print('Run the temperature sensor')
    await dht22.measure()

def run():
    hardware.setupPins()
    functions.getConfigData()
    functions.connect()

    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.create_task(watchdog())
    if hardware.fileExists('temp'):
        dht22.init()
        loop.create_task(temperature())
    print('Configured as',functions.getMyName())

    try:
        # Run the event loop indefinitely
        loop.run_forever()
    except Exception as e:
        print('Error occured: ', e)
        hardware.writeFile('update', currentVersion)
        raise(e)
    except KeyboardInterrupt:
        print('Program interrupted')
