import urlencode,network,asyncio,socket,gc
import ubinascii,time,json,os
import hardware,functions,poll,handleClient,maps,dht22,state

resetRequest=False
loop=None

async def pollTask():
    result=await poll.poll()
    state.restart('Polling stopped')

async def watchdog():
    while True:
        await asyncio.sleep(300)
        pollCount=maps.getPollCount()
        print(f'Polls:{pollCount}, free:{gc.mem_free()}')
        if pollCount==0:
            state.restart('Watchdog restart')
        maps.clearPollCount()

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





