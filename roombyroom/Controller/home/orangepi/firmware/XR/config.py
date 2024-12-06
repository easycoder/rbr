import asyncio,json

async def writeConfig(args):
    config={}
    def setConfigElement(item):
        key,value=item.split('=',1)
        if key=='Relay+Name':
            config['myname']=value
            return True
        elif key=='Host+SSID':
            config['hostssid']=value
            return True
        elif key=='Host+Password':
            config['hostpass']=value
            return True
        elif key=='My+Password':
            config['mypass']=value
            return True
        return False

    items=args.split('&')
    for item in items:
        setConfigElement(item)
        await asyncio.sleep(1)
    f = open('config.json', 'w')
    f.write(json.dumps(config))
    f.close()
