import asyncio,hardware,functions,os,machine,gc

watchdogCount=0

###################################################################################
def saveFile(name,content):
    if len(content)==0:
        raise(BaseException('...Empty file'))
    hardware.writeFile('temp',content)
    if content==hardware.readFile('temp'):
        if hardware.fileExists(name):
            gc.collect()
            if content==hardware.readFile(name):
                os.remove('temp')
                print('...Unchanged')
            else:
                os.remove(name)
                os.rename('temp',name)
                print('...Done')
        else:
            os.rename('temp',name)
            print('...New file')
    else:
        raise(BaseException('...Did not save'))

###################################################################################
async def getFile(file):
    url='http://'+functions.getServer()
    if functions.isPrimary():
        url+='getFile?data=firmware/XR/'+file
    else:
        url+='/getFile?'+file
    return await functions.httpGET(url)

###################################################################################
async def update(version):
    try:
        print('Updating files.txt','...',end='')
        files=await getFile('files.txt')
        saveFile('files.txt',files)
        for file in files.split():
            await asyncio.sleep(1)
            print('Updating',file,'...',end='')
            content=await getFile(file)
            saveFile(file,content)
            content=None
            gc.collect()
        print('Update the version')
        hardware.writeFile('version',version)
        print('Remove the update flag')
        if hardware.fileExists('update'):
            os.remove('update')
        print("Update complete - rebooting")
        await asyncio.sleep(1)
        machine.reset()
    except (BaseException) as error:
        print(error,'\nUpdate aborted')
        await asyncio.sleep(1)
        machine.reset()

###################################################################################
# Watchdog
async def watchdog():
    global watchdogCount
    while True:
        await asyncio.sleep(60)
        print('Watchdog count:',watchdogCount)
        if watchdogCount==0:
            print('Timeout')
            await asyncio.sleep(1)
            machine.reset()
        watchdogCount=0

###################################################################################
def run(version):
    print('Update to version',version)
    functions.getConfigData()
    if functions.connect()==False:
        return

    loop = asyncio.get_event_loop()
    loop.create_task(update(version))
    loop.create_task(watchdog())

    try:
        # Run the event loop indefinitely
        loop.run_forever()
    except Exception as e:
        print('Error occured: ', e)
    except KeyboardInterrupt:
        print('Program Interrupted by the user')
