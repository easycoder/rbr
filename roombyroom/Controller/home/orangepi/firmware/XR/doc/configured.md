# Configured mode
This mode is handled by configured.py. Here’s the code:
```
import urlencode,network,asyncio,socket,gc
import ubinascii,time,json,os,machine,urlencode
import hardware,functions

myName=None
incomingMap=None
outgoingMap=None
resetRequest=False
pollCount=0
pollTotal=0

###########################################################################
# Handle a poll request
def handlePoll(data):
    global incomingMap,outgoingMap
    if data.startswith('data='):#
        data=data[5:].replace('%20',' ').replace('%22','"')
        data=json.loads(data)
        for key in data.keys():
            incomingMap[key]=data[key]
#    print('Incoming:',incomingMap)
    return json.dumps(outgoingMap)

###########################################################################
# Asynchronous function to handle client requests
async def handleClient(reader, writer):
    global resetRequest,pollCount,pollTotal,currentVersion

    request_line = await reader.readline()

    # Skip HTTP request headers
    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line, 'utf-8').split()[1]
#    print('Request:', request)

    req=request.split('?')
    cmd=req[0].split('/')
    cmd=cmd[len(cmd)-1]
    if len(req)>1:
        data=req[1].split()
        data=data[0].replace('%27','\'')
    else:
        data=None
#    print('Command/Data:',cmd,data)

    # Generate HTML response
    resetRequest=False
    if cmd=='reboot':
        response='reboot'
        resetRequest=True
    elif cmd=='reset':
        response='Factory reset'
        os.remove('config.json');
        resetRequest=True
    elif cmd=='poll':
        response=handlePoll(data)
    elif cmd=='getFile':
        print('getFile:',data)
        if len(data)==0:
            response=None
        else:
            response=hardware.readFile(data)
            if len(response)==0:
                response=None
    else:
        response=f'{functions.getMyName()} v{currentVersion} {functions.getMySSID()} from {functions.getHostSSID()} {functions.getRelay()} {pollTotal}/{pollCount}'
#        print(response)

    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)
    await writer.drain()
    await writer.wait_closed()
    if resetRequest:
        await asyncio.sleep(1)
        machine.reset()
    gc.collect()

###########################################################################
# Main loop
async def main():
    global incomingMap,outgoingMap,resetRequest,pollCount,pollTotal,currentVersion
    currentVersion=hardware.readFile('version')
    if currentVersion==None:
        currentVersion=0
    myname=functions.getMyName()
    incomingMap={}
    outgoingMap={}
    incomingMap[myname]=json.loads('{"ts":"0"}')
    outgoingMap['ts']='0'
    pollCount=0

    await functions.setupAP()
    server = asyncio.start_server(handleClient, "0.0.0.0", 80)
    asyncio.create_task(server)
    print('Server running')

    while (True):
        await asyncio.sleep(10)

        data=urlencode.encode(json.dumps(incomingMap))
        url='http://'+functions.getServer()+'/poll?data='+data
        try:
            response=await functions.httpGET(url)
            outgoingMap=json.loads(response)
            print('Outgoing:',outgoingMap)
            if myname in outgoingMap:
                state=outgoingMap[myname]['relay']
            else:
                state='off'
            hardware.setRelay(state)
            incomingMap[myname]=json.loads('{"ts":"'+outgoingMap['ts']+'"}')
            if 'v' in outgoingMap:
                version=outgoingMap['v']
            else:
                version='9999999999'
            pollCount+=1
            pollTotal+=1
            if int(version)>int(currentVersion):
                print('Update required')
                hardware.writeFile('update',version)
                await asyncio.sleep(1)
                machine.reset()
        except Exception as e:
            print('Error:',e)

###########################################################################
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

########################################################################### def run():
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
    except KeyboardInterrupt:
        print('Program interrupted')
```
As with unconfigured mode, the code runs concurrent tasks using the asyncio library. One of these tasks is the main program; the other is a watchdog that monitors activity to ensure polling runs as expected. If for any reason it stops (such as the device’s host going offline), the watchdog forces a reset after a decent interval. This avoids un-needed resets when momentary failures occur.

Most of the functions required by the code - other than standard libraries - are kept in two local modules; `functions.py` and `hardware.py`. These will be described later.

The main progam starts by doing some initialization. Two special dictionary objects - `outgoingMap` and `incomingMap` - hold the data passing around the network. Both of these, once created,  last for as long as the program is running. An access point (hotspot) is set up for other devices to use as part of the message chain.

In the main loop, the code polls its parent device every ten seconds, sending it the `incomingMap`. The reply - the `outgoingMap` - is parsed to find if the local relay should be on or off. The version number in `outgoingMap` is compared with that currently saved, and if there’s been an advance the device creates an update file and forces a reset.

When a client device polls this one, the incoming request is parsed to find the command and its data (if any). The format of the request is one of

 - http://(my ip address)/command
 - http://(my ip address)/command?data

The commands recognised are as follows:

**reboot** forces a restart of the code.
**reset** erases the configuration file then forces a reboot, causing the device to restart in unconfigured mode.
**getFile?{filename}** is a request for the contents of the named file to be returned. This is used by the updater.
**poll?data={incomingMap}** Poll the parent of this device, supplying the incoming map (the part of it known to this device). The outgoing map is returned to the caller.

Any other command will return a line of general information about the device and its status.

[Unconfigured mode](unconfigured.md)

[Update mode](update.md)

[Functions](functions.md)

[Back to start](README.md)

