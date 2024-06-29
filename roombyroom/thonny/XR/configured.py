# Import necessary modules
import functions,network,asyncio,socket,ubinascii,time
from machine import Pin

myName=None
incomingMap=None
outgoingMap=None
resetRequest=False

# Create several LEDs
led_blink = Pin(2, Pin.OUT)

# Handle a poll request
def handlePoll(args):
    global incomingMap,outgoingMap
    args=args.split('&')
    for arg in args:
        key,value=arg.split('=',1)
        incomingMap[key]=value
    print('Incoming:',incomingMap)
    return str(outgoingMap)

# Asynchronous function to handle client's requests
async def handle_client(reader, writer):
    global resetRequest

    print("Client connected")
    request_line = await reader.readline()
    print('Request:', request_line)

    # Skip HTTP request headers
    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line, 'utf-8').split()[1]
    print('Request:', request)

    req=request.split('?')
    cmd=req[0].split('/')
    cmd=cmd[len(cmd)-1]
    if len(req)>1:
        args=req[1].split()
        args=args[0].replace('%27','\'')
    else:
        args=None
    print(cmd,args)
    
    # Generate HTML response
    resetRequest=False
    if cmd is 'reboot':
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
    else:
        response=f'SSID: {functions.getMySSID()}'

    # Send the HTTP response and close the connection
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write('<!DOCTYPE HTML><html lang="en"><head></head><body>'+response+'</body></html>')
    await writer.drain()
    await writer.wait_closed()
    print('Client Disconnected')

async def main():
    global incomingMap,outgoingMap
    myname=functions.readFile('myname.txt')
    myip=functions.readFile('myip.txt')
    mypass=functions.readFile('mypass.txt')
    incomingMap={}
    outgoingMap={}
    incomingMap[myname]='0'
    outgoingMap['ts']='0'
    
    await functions.setupAP('XR',myip,mypass)
    # Start the server and run the event loop
    server = asyncio.start_server(handle_client, "0.0.0.0", 80)
    asyncio.create_task(server)
    print('Server running')

    while True:
        await asyncio.sleep(10)
        if resetRequest:
            print("Reset request")
            await asyncio.sleep(1)
            machine.reset()
            return

        url='http://'+functions.getServer()+'/poll?data='+str(incomingMap).replace(' ','')
        try:
            map=await functions.httpGET(url)
            map=map.replace('{','').replace('}','').replace('"','').replace(' ','')
            outgoingMap=functions.createData(map.strip())
            print('Outgoing:',outgoingMap)
            if myname in outgoingMap:
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
                await functions.update('XR',['boot.py','main.py','unconfigured.py','configured.py','functions.py','config.html','ack.html'])
                functions.writeFile('version',version)
        except Exception as e:
            print('Error:',e)

def run():
    if functions.connect()==False:
        return

    loop = asyncio.get_event_loop()
    # Create a task to run the main function
    loop.create_task(main())

    try:
        # Run the event loop indefinitely
        loop.run_forever()
    except Exception as e:
        print('Error occured: ', e)
    except KeyboardInterrupt:
        print('Program Interrupted by the user')


