import urlencode,network,asyncio,socket,gc
import ubinascii,time,json,os,machine,urlencode
import hardware,functions,handleClient,maps

myName=None
resetRequest=False
pollCount=0
pollTotal=0

async def main():
    global pollCount,pollTotal,currentVersion
    currentVersion=hardware.readFile('version')
    if currentVersion==None:
        currentVersion=0
    myname=functions.getMyName()
    
    maps.setIncomingMapElement(myname,json.loads('{"ts":"0"}'))
    pollCount=0

    await functions.setupAP()
    server = asyncio.start_server(handleClient.handleClient, "0.0.0.0", 80)
    asyncio.create_task(server)
    print('Server running')

    while (True):
        await asyncio.sleep(2)

        incomingMap=maps.getIncomingMap()
        data=urlencode.encode(json.dumps(incomingMap))
        url='http://'+functions.getServer()+'/poll?data='+data
        response=await functions.httpGET(url)
        outgoingMap=json.loads(response)
        maps.setOutgoingMap(outgoingMap)
        print('Outgoing:',outgoingMap)
        if myname in outgoingMap:
            state=outgoingMap[myname]['relay']
        else:
            state='off'
        hardware.setRelay(state)
        incomingMap[myname]=json.loads('{"ts":"'+outgoingMap['ts']+'"}')
        info=f'{functions.getMySSID()},{pollTotal}'
        incomingMap[myname]['i']=info
        maps.setIncomingMap(incomingMap)
        if 'v' in outgoingMap:
            version=outgoingMap['v']
        else:
            version='1'
        pollCount+=1
        pollTotal+=1
        if int(version)>int(currentVersion):
            print('Update required')
            hardware.writeFile('update',version)
            await asyncio.sleep(1)
            machine.reset()

# Watchdog
async def watchdog():
    global pollCount
    while True:
        await asyncio.sleep(60)
        print('Poll count:',pollCount)
        if pollCount==0:
            print('Timeout')
            await asyncio.sleep(1)
            machine.reset()
        pollCount=0

def run():
    hardware.setupPins()
    functions.getConfigData()
    functions.connect()

    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.create_task(watchdog())
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
