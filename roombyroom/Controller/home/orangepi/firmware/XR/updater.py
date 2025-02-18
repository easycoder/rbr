import asyncio,hardware,functions,maps,httpGet,os,machine,gc
from time import sleep

def abort(error=''):
    print(f'\nError: {error}')
    sleep(2)
    machine.reset()

def saveFile(name,content):
    if len(content)==0:
        abort('Empty')
    hardware.writeFile('temp',content)
    sleep(1)
    temp=hardware.readFile('temp')
    if temp==content:
        if hardware.fileExists(name):
            gc.collect()
            existing=hardware.readFile(name)
            if content==existing:
                os.remove('temp')
                print('Unchanged')
            else:
                os.remove(name)
                os.rename('temp',name)
                print('Updated')
        else:
            os.rename('temp',name)
            print('New file')
    else:
        abort('Mismatch')

async def getFile(file):
    try:
        file=file.split(' ')
        url='http://'+maps.getServer()
        if maps.isPrimary():
            url+='getFile?data=firmware/XR/'+file[0]
        else:
            url+='/getFile?'+file[0]
        content=await httpGet.httpGET(url)
        if len(file)==2 and len(content)!=int(file[1]):
            abort('Length')
        return content
    except Exception as e:
        abort(e)

async def update(version):
    try:
        print('Updating files.txt ... ',end='')
        files=await getFile('files.txt')
        if files==None:
            abort()
        saveFile('files.txt',files)
        for file in files.split('\n'):
            if file=='':
                break;
            await asyncio.sleep(1)
            print(f'Updating {file} ... ',end='')
            content=await getFile(file)
            if content==None:
                abort('Empty')
            saveFile(file.split(' ')[0],content)
            content=None
            gc.collect()
        hardware.writeFile('version',version)
        if hardware.fileExists('update'):
            os.remove('update')
        print("Rebooting")
        await asyncio.sleep(3)
        machine.reset()
    except (BaseException) as error:
        abort(error)

def run(version):
    print('Updater: update to version',version)
    hardware.setupPins()
    functions.getConfigData()
    if functions.connect()==False:
        abort()

    loop = asyncio.get_event_loop()
    loop.create_task(update(version))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('Program Interrupted by the user')

