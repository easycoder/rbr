#!/usr/bin/env python3

import bottle, time, os, json, subprocess, base64, requests
from os import listdir
from os.path import isfile, join
from bottle import Bottle, run, request, static_file

app = Bottle()

esp32 = 'http://192.168.23.1'

###############################################################################
# This is the RBR local website at http://rbr.home

# Endpoint: GET <server-ip>/register
# Called to register
@app.get('/register')
def register():
    # print('Register')
    return static_file('map', root='.')

# Endpoint: GET <server-ip>/resources/php/rest.php/map
# Called to return the map
@app.get('/resources/php/rest.php/map')
def getMap():
    # print('getMap')
    if not isfile('map'):
        f = open('map', 'w')
        f.write('{"profiles":[{"name":"Unnamed","rooms":[{"name":"Unnamed","sensor":"","relays":[""],"mode":"off","target":"0.0","events":[]}],"message":"OK"}],"profile":0,"name":"New system"}')
        f.close()
    return static_file('map', root='')

# Endpoint: GET <server-ip>/resources/php/rest.php/sensors
# Called to return the sensors
@app.get('/resources/php/rest.php/sensors')
def getSensors():
    # print('getSensors')
    if not isfile('/mnt/data/sensorData'):
        f = open('/mnt/data/sensorData', 'w')
        f.write('{"actual": 0}')
        f.close()
    return static_file('sensorData', root='/mnt/data')

# Endpoint: GET <server-ip>/resources/php/rest.php/_list/<name>
# Called to return a file list
@app.get('/resources/php/rest.php/_list/<name>')
def getFileList(name):
    # print('getFileList')
    path = f'resources/{name}'
    files = []
    for name in listdir(path):
        if isfile(f'{path}/{name}'):
            f = {}
            f['name'] = name
            f['type'] = 'ecs'
            files.append(f)
    def getName(f):
        return f['name']
    files.sort(key = getName)
    return json.dumps(files)

# Endpoint: GET <server-ip>/resources/ecs/<name>
# Called to return an ecs script
@app.get('/resources/ecs/<name>')
def getScript(name):
    # print(f'getScript {name}')
    return static_file(name, root='./resources/ecs')

# Endpoint: GET <server-ip>/resources/webson/<name>
# Called to return a webson script
@app.get('/resources/webson/<name>')
def getWebson(name):
    # print(f'getWebson {name}')
    return static_file(name, root='./resources/webson')

# Endpoint: GET <server-ip>/resources/json/<name>
# Called to return a json script
@app.get('/resources/json/<name>')
def getJson(name):
    # print(f'getJson {name}')
    return static_file(name, root='./resources/json')

# Endpoint: GET <server-ip>/resources/icon/<name>
# Called to return an icon
@app.get('/resources/icon/<name>')
def getIcon(name):
    # print(f'getIcon {name}')
    return static_file(name, root='./resources/icon')

# Endpoint: GET <server-ip>/resources/img/<name>
# Called to return an image
@app.get('/resources/img/<name>')
def getImage(name):
    # print(f'getImage {name}')
    return static_file(name, root='./resources/img')

# Endpoint: GET <server-ip>/resources/help/<name>
# Called to return a help file
@app.get('/resources/help/<path:path>')
def getHelp(path):
    # print(f'getHelp {path}')
    return static_file(path, root='./resources/help')

# Endpoint: GET <server-ip>/resources/js/<name>
# Called to return a js file
@app.get('/resources/js/<name>')
def getJS(name):
    # print(f'getJS {name}')
    return static_file(name, root='./resources/js')

# Endpoint: GET <server-ip>/resources/ecs/<name>
# Called to return a config ecs script
@app.get('/config/ecs/<name>')
def getConfigScript(name):
    # print(f'getConfigScript {name}')
    return static_file(name, root='./config/ecs')

# Endpoint: GET <server-ip>/resources/webson/<name>
# Called to return a config webson script
@app.get('/config/webson/<name>')
def getConfigWebson(name):
    # print(f'getConfigWebson {name}')
    return static_file(name, root='./config/webson')

# Endpoint: GET <server-ip>/resources/config/img/<name>
# Called to return a config image
@app.get('/config/img/<name>')
def getConfigImage(name):
    # print(f'geConfigImage {name}')
    return static_file(name, root='./config/img')

# Endpoint: GET <server-ip>/resources/config/scan
# Called to return a config scan
@app.get('/config/scan')
def getConfigScan():
    # print(f'getConfigScan')
    try:
        response = requests.get(f'{esp32}/scan', timeout=10)
        if response.status_code < 400:
            print(response.text)
            return response.text
        errorCode = response.status_code
        errorReason = response.reason
        print(f'Error code {errorCode}: {errorReason}')
    except Exception as e:
        errorReason = str(e)
        print(f'Error: {errorReason}')

# Endpoint: GET <server-ip>/resources/config/connect?ssid={ssid}&password={password}
# Called to connect to a server
@app.get('/config/connect')
def getConfigConnect():
    # print(f'getConfigConnect')
    try:
        ssid = request.query.ssid
        password = request.query.password
        response = requests.get(f'{esp32}/connect?ssid={ssid}&password={password}', timeout=5)
        if response.status_code < 400:
            print(response.text)
            return response.text
        errorCode = response.status_code
        errorReason = response.reason
        print(f'Error code {errorCode}: {errorReason}')
    except Exception as e:
        errorReason = str(e)
        print(f'Error: {errorReason}')

# Endpoint: GET <server-ip>/resources/config/connected
# Called to check if connected
@app.get('/config/connected')
def getConfigConnected():
    # print(f'getConfigConnected')
    try:
        ssid = request.query.ssid
        password = request.query.password
        response = requests.get(f'{esp32}/connected', timeout=5)
        if response.status_code < 400:
            print(response.text)
            return response.text
        errorCode = response.status_code
        errorReason = response.reason
        print(f'Error code {errorCode}: {errorReason}')
    except Exception as e:
        errorReason = str(e)
        print(f'Error: {errorReason}')

# Endpoint: GET <server-ip>/resources/config/request
# Called to issue a GET request
@app.get('/config/request')
def getConfigRequest():
    # print(f'getConfigRequest')
    try:
        req = request.query.req
        response = requests.get(f'{esp32}/request?req={req}', timeout=5)
        if response.status_code < 400:
            print(response.text)
            return response.text
        errorCode = response.status_code
        errorReason = response.reason
        print(f'Error code {errorCode}: {errorReason}')
    except Exception as e:
        errorReason = str(e)
        print(f'Error: {errorReason}')

# Endpoint: GET <server-ip>/resources/config/response
# Called to get the result of a GET request
@app.get('/config/response')
def getConfigResponse():
    # print(f'getConfigResponse')
    try:
        response = requests.get(f'{esp32}/response', timeout=5)
        if response.status_code < 400:
            print(response.text)
            return response.text
        errorCode = response.status_code
        errorReason = response.reason
        print(f'Error code {errorCode}: {errorReason}')
    except Exception as e:
        errorReason = str(e)
        print(f'Error: {errorReason}')

# Endpoint: GET <server-ip>/resources/config
# Called to return the esp32 home page
@app.get('/config')
def getConfig():
    # print(f'geConfig')
    try:
        response = requests.get(esp32, timeout=5)
        if response.status_code < 400:
            print(response.text)
            return response.text
        errorCode = response.status_code
        errorReason = response.reason
        print(f'Error code {errorCode}: {errorReason}')
    except Exception as e:
        errorReason = str(e)
        print(f'Error: {errorReason}')

# Endpoint: POST <server-ip>/resources/php/rest.php/map/<mac><password>
# Called to post the map. This always comes from the local UI
@app.post('/resources/php/rest.php/map/<mac>/<password>')
def postMap(mac, password):
    map = request.body.getvalue().decode("ascii")
    f = open('map', 'w')
    f.write(map)
    f.close()
    postMap(map)

# Endpoint: POST <server-ip>/resources/php/rest.php/backup/<mac><password>
# Called to post the backup
@app.post('/resources/php/rest.php/backup/<mac>/<password>')
def postBackup(mac, password):
    # print('postBackup')
    f = open('map', 'r')
    map = f.read()
    f.close()
    f = open('backup', 'w')
    f.write(map)
    f.close()

# Endpoint: POST <server-ip>/resources/php/rest.php/restore/<mac>/<password>
# Called to restore the backup if it exists
@app.post('/resources/php/rest.php/restore/<mac>/<password>')
def restoreBackup(mac, password):
    # print('restoreBackup')
    if isfile('backup'):
        f = open('backup', 'r')
        map = f.read()
        f.close()
        f = open('map', 'w')
        f.write(map)
        f.close()
        postMap(map)
    return static_file('map', root='')

# Endpoint: POST <server-ip>/resources/php/rest.php/_save/path>
# Called to save a resource file
@app.post('/resources/php/rest.php/_save/<path>')
def save(path):
    # print('save')
    data = request.body.getvalue().decode("ascii")
    data = base64.b64decode(data).decode("ascii")
    path = path.replace('~', '/')
    f = open(f'resources/{path}', 'w')
    f.write(data)
    f.close()

# Endpoint: GET <server-ip>/
# Called to return a top-level file
@app.get('/<name>')
def getTopLevel(name):
    # print('getHTML')
    return static_file(name, root='.')

# Endpoint: GET <server-ip>/
# Called to return the index file
@app.get('/')
def getIndex():
    # print('getIndex')
    return static_file('index.html', root='.')

# Endpoint: GET <server-ip>/sim/<data>
# Called to pass simulator data
@app.get('/sim/<data>')
def sim(data):
    # dir = f'{os.getcwd()}/sensors'
    dir = '/mnt/data/sensors'
    if not os.path.exists(f'{dir}'):
        os.makedirs(f'{dir}')
    data = json.loads(f'[{data}]')
    for index, temp in enumerate(data):
        file = open(f'{dir}/sim.{index}.txt', 'w')
        file.write('{"temperature": "' + str(temp) + '", "timestamp": "' + str(round(time.time())) + '"}')
        file.close()
    if not os.path.exists('simulator'):
        file = open('simulator', 'w')
        file.close()
    file = open('simulator', 'r')
    response = file.read()
    file.close()
    return response

# Endpoint: GET <server-ip>/ms/<data>
# Called to report movement
@app.get('/ms/<message>')
def ms(message):
    print(message)
    return

# Endpoint: GET <server-ip>/extender/version
# Called to get the current extender version
@app.get('/extender/version')
def extenderversion():
    f = open('esp/esp32_wifi_extender/version', 'r');
    version = f.read()
    f.close()
    return version

# Endpoint: GET <server-ip>/extender/update
# Called to get the current extender binary
@app.get('/extender/update')
def extenderupdate():
    return static_file('esp/esp32_wifi_extender/esp32_wifi_extender.ino.bin', root='.')

# Endpoint: GET <server-ip>/relay/version
# Called to get the current relay version
@app.get('/relay/version')
def relayversion():
    f = open('esp/esp8266_r1_relay/version', 'r');
    version = f.read()
    f.close()
    return version

# Endpoint: GET <server-ip>/relay/update
# Called to get the current relay binary
@app.get('/relay/update')
def relayupdate():
    return static_file('esp/esp8266_r1_relay/esp8266_r1_relay.ino.bin', root='.')

# Endpoint: GET <server-ip>/notify/?hum=hhh&temp=ttt&id=id
# Called when temperature changes
@app.get('/notify')
def notify():
    try:
        source = request.get("REMOTE_ADDR")
        hum = request.query.hum
        temp = request.query.temp
        if hum and temp:
            ts = round(time.time())
            temp = round(float(temp), 1)
#            print(f'hum={hum}, temp={temp}, source={source}, ts={ts}')
            # dir = f'{os.getcwd()}/sensors'
            dir = '/mnt/data/sensors'
            if not os.path.exists(f'{dir}'):
                os.makedirs(f'{dir}')
            file = open(f'{dir}/{source}.txt', 'w')
            message = '{"temperature": "' + str(temp) + '", "timestamp": "' + str(ts) + '", "battery": "100"}'
            file.write(message)
            file.close()
    except:
        print('Error')

# Post the map to the RBR web server
def postMap(map):
    # Check if we have communication with the web server
    f = open('/mnt/data/password', 'r')
    password = f.read().strip()

    f.close()
    if password:
        f = open('server.txt', 'r')
        server = f.read().strip()
        f.close()
        f = open('mac', 'r')
        mac = f.read().strip()
        f.close()
        try:
            print(f'Post to {server}/resources/php/rest.php/map/{mac}/{password}')
            response = requests.post(f'{server}/resources/php/rest.php/map/{mac}/{password}', map, timeout=5)
            if response.status_code >= 400:
                print(f'Error posting map: {response.reason} (code {response.status_code})')
        except Exception as e:
            print(f'Error posting map: {str(e)}')

# Initialization

if __name__ == '__main__':
    ip = subprocess.getoutput("hostname -I").strip()
    if ip.rfind(' ') > 0:
        ip = '192.168.0.201'
    print(f'IP address: {ip}')
    app.run(host=ip, port=80, debug=False)

