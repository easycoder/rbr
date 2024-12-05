import asyncio,hardware,functions,maps,httpGet,os,machine,gc
from time import sleep

def saveFile(name,content):
    if len(content)==0:
        raise(BaseException('...Empty file'))
    hardware.writeFile('temp',content)
    sleep(1)
    temp=hardware.readFile('temp')
    if temp==content:
        if hardware.fileExists(name):
            gc.collect()
            existing=hardware.readFile(name)
            if content==existing:
                os.remove('temp')
                print('...Unchanged')
            else:
                os.remove(name)
                os.rename('temp',name)
                print('...Updated')
        else:
            os.rename('temp',name)
            print('...New file')
    else:
        raise(BaseException('...Did not save'))

async def getFile(file):
    url='http://'+maps.getServer()
    if maps.isPrimary():
        url+='getFile?data=firmware/XR/'+file
    else:
        url+='/getFile?'+file
    return await httpGet.httpGET(url)

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
        await asyncio.sleep(5)
        machine.reset()
    except (BaseException) as error:
        print(error,'\nUpdate aborted')
        await asyncio.sleep(1)
        machine.reset()

def run(version):
    print('Updater: update to version',version)
    hardware.setupPins()
    functions.getConfigData()
    if functions.connect()==False:
        raise Exception('\nUpdate aborted')

    loop = asyncio.get_event_loop()
    loop.create_task(update(version))

    try:
        loop.run_forever()
    except Exception as e:
        print('Error occured: ', e)
        raise(e)
    except KeyboardInterrupt:
        print('Program Interrupted by the user')
