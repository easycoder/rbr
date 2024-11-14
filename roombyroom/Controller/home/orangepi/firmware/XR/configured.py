import urlencode,network,asyncio,socket,gc
import ubinascii,time,json,os,machine
import hardware,functions,poll,handleClient,maps,dht22

myName=None
resetRequest=False

def reset():
    time.sleep(1)
    machine.reset()

async def clientHandler(reader,writer):
    await handleClient.handleClient(reader,writer)

async def main():
    myname=functions.getMyName()
    
    maps.setIncomingMapElement(myname,json.loads('{"ts":"0"}'))
    maps.clearPollCount()

    await functions.setupAP()
    server = asyncio.start_server(clientHandler, "0.0.0.0", 80)
    asyncio.create_task(server)
    print('Server running')
    
    await poll.poll(myname)
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
    await dht22.measure()

def run():
    hardware.setupPins()
    functions.getConfigData()
    functions.connect()

    loop = asyncio.get_event_loop()
    if hardware.fileExists('therm'):
        dht22.init()
        loop.create_task(temperature())
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
