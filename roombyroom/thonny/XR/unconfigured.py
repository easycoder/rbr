# Import necessary modules
import functions,network,asyncio,socket,ubinascii,time
from machine import Pin

def info():
    print('This handles unconfigured mode')

# Create several LEDs
led_blink = Pin(2, Pin.OUT)

# Asynchronous function to handle client's requests
async def handle_client(reader, writer):
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
        elif key=='My+IP+Address':
            functions.writeFile('myip.txt', value)
            return True
        return False
    
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
    response = 'OK'
    if cmd is 'config':
        response=functions.readFile('config.html')
    elif cmd is 'setup':
        items=args.split('&')
        for item in items:
            writeConfigElement(item)
            await asyncio.sleep(1)
        await asyncio.sleep(1)
        response=functions.readFile('ack.html')
        resetRequest=True
    else:
        response=f'SSID: {functions.getMySSID()}'

    # Send the HTTP response and close the connection
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write('<!DOCTYPE HTML><html lang="en"><head></head><body>'+response+'</body></html>')
    await writer.drain()
    await writer.wait_closed()
    print('Client Disconnected')

async def blink_led():
    while True:
        led_blink.on()  # Toggle LED state
        await asyncio.sleep(0.5)  # Blink interval
        led_blink.off()  # Toggle LED state
        await asyncio.sleep(0.5)  # Blink interval

async def main():
    await functions.setupAP('xr','192.168.66.1','00000000')
    # Start the server and run the event loop
    print('Setting up server')
    server = asyncio.start_server(handle_client, "0.0.0.0", 80)
    asyncio.create_task(server)
    print('Server running')
    asyncio.create_task(blink_led())

    while True:
        # Add other tasks that you might need to do in the loop
        await asyncio.sleep(10)
#        print('This message will be printed every 10 seconds')

def run():
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

