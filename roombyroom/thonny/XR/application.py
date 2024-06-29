# application.py

import machine, os, functions, asyncio

myName=None
incomingMap=None
outgoingMap=None
resetRequest=False

# Handle a request on the hotspot
def handlePoll(args):
    global incomingMap,outgoingMap
    args=args.split('&')
    for arg in args:
        item=arg.split('=')
        incomingMap[item[0]]=item[1]
    print('Incoming:',incomingMap)
    return str(outgoingMap)

# Handle a request on the hotspot
async def handleRequest(cmd,args):
    # Write a config element
    def writeConfigElement(item):
        key,value=item.split('=',1)
        if key=='Relay+Name':
            functions.writeFile('name.txt', value)
            return True
        elif key=='Host+SSID':
            functions.writeFile('hostssid.txt', value)
            return True
        elif key=='Host+Password':
            functions.writeFile('hostpass.txt', value)
            return True
        elif key=='My+Password':
            functions.writeFile('mypass.txt', value)
            return True
        return False

    global myssid, incomingMap, resetRequest
    response=f'SSID: {functions.getMySSID()}'

    if cmd is 'config':
        response=functions.readFile('config.html')
    if cmd is 'setup':
        items=args.split('&')
        for item in items:
            writeConfigElement(item)
            await asyncio.sleep(1)
        await asyncio.sleep(1)
        response=functions.readFile('ack.html')
        resetRequest=True
    elif cmd is 'reboot':
        response='reboot'
        resetRequest=True
    elif cmd is 'reset':
        response='Factory reset'
        os.remove('password.txt');
        resetRequest=True
    elif cmd is 'poll':
        response=handlePoll(args)
    elif cmd is 'relay':
        response=functions.getRelay()
    return response,resetRequest

# Run the application
async def run():
    global incomingMap,outgoingMap,VERSION
    myname=functions.getMyName()
    incomingMap={}
    outgoingMap={}
    incomingMap[myname]='0'
    outgoingMap['ts']='0'
    while True:
        await asyncio.sleep(10)
        if resetRequest:
            print("Reset request")
            await asyncio.sleep(1)
            machine.reset()
            return
        url='http://'+functions.getServer()+'/poll?data='+str(incomingMap).replace(' ','')
        print('Poll',url)
        try:
            map=await functions.httpGET(url)
            map=map.replace('{','').replace('}','').replace('"','').replace(' ','')
            outgoingMap=functions.createData(map.strip())
            print('Outgoing:',outgoingMap)
            if myname in map:
                state=outgoingMap[myname]
            else:
                state='off'
            functions.relay(state)
            incomingMap[myname]=outgoingMap['ts']
            version=outgoingMap['version']
            current=functions.readFile('version')
            if current==None:
                current=0
            if int(version)>int(current):
                await functions.update('XR',['boot.py','main.py','functions.py','application.py','config.html','ack.html'])
                functions.writeFile('version',version)
        except Exception as e:
            print('Error:',e,'\n','Error in main loop')
