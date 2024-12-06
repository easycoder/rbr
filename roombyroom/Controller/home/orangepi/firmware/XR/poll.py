import gc,os,time,asyncio,maps,hardware,functions,urlencode,dht22,state
from incoming import Devices
from httpGet import httpGET

async def poll():
    version=0
    rstate=None
    info=None
    ts=0
    rs=0
    pollError=0
    currentVersion=hardware.readFile('version')
    if currentVersion==None:
        currentVersion=0
    print(f'v:{currentVersion}')
    maps.setCurrentVersion(currentVersion)
    maps.setIncomingMap(Devices())
    myname=maps.getMyName()
    count=0
    while (True):
        gc.collect()
        await asyncio.sleep(2)
        try:
            maps.bumpPollCount()
            incomingMap=maps.getIncomingMap()
            url=f'http://{maps.getServer()}/poll?data={incomingMap.toString()}'
            outgoingMap=await httpGET(url)
            maps.setOutgoingMap(outgoingMap)
            count+=1
            rstate='off'
            lines=outgoingMap.split()
            nlines=len(lines)
            if nlines>1:
                version=lines[0]
                ts=lines[1]
                n=2
                while n<nlines:
                    items=lines[n].split(':')
                    if myname==items[0]:
                        rstate=items[1]
                        break
                    n+=1
            hardware.setRelay(rstate)
            
            info=''
            if hardware.fileExists('therm'):
                info=f't={dht22.getTemperature()}'
            elif hardware.hasRelay():
                info=f'r={rstate}'

            if rs==0:
                rs=ts;
            
            ssid=functions.getHostSSID()
            mac=functions.getMAC()
            rssi=maps.getRSSI()

            data=f'{myname}:{ts},{rs},{ssid},{mac},{count},{rssi},{info}'
            item=incomingMap.getDevice(myname)
            incomingMap.replace(myname,data)
            maps.setIncomingMap(incomingMap)

            if int(version)>int(currentVersion):
                hardware.writeFile('update',version)
                state.restart(f'Update to v{version}')
            pollError=0
        except Exception as e:
            pollError+=1
            print(f'Error {pollError}: {str(e)}')
            if pollError>20:
                state.restart(f'Too many errors')
        gc.collect()
    return
