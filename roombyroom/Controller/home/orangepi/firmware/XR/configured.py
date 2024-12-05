import urlencode,network,asyncio,socket,gc
import ubinascii,time,json,os
import hardware,functions,poll,handleClient,maps,dht22,state

resetRequest=False
loop=None

async def pollTask():
    global loop
    result=await poll.poll()
    time.sleep(1)
    machine.reset()

async def watchdog():
    running=True
    while running:
        await asyncio.sleep(300)
        pollCount=maps.getPollCount()
        print('Poll count:',pollCount)
        if pollCount==0:
            running=False
        else:
            maps.clearPollCount()
    state.restart('Watchdog restart')

async def temperature():
    await dht22.measure()
    state.restart('Sensor loop terminated')

def run():
    global loop
    hardware.setupPins()
    try:
        functions.getConfigData()
        functions.connect()
        functions.setupAP()
    except Exception as e:
        state.restart(f'Setup: {str(e)}')

    maps.setIncomingMapElement(functions.getMyName(),json.loads('{"ts":"0"}'))
    maps.clearPollCount()

    loop = asyncio.get_event_loop()
    if hardware.fileExists('therm'):
        dht22.init()
        loop.create_task(temperature())
    loop.create_task(asyncio.start_server(handleClient.handleClient, "0.0.0.0", 80))
    loop.create_task(pollTask())
    loop.create_task(watchdog())
    print('Configured as',maps.getMyName())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('Program interrupted')
    except Exception as e:
        print('Exception:',str(e))
    
    print('All done')
