#!/usr/bin/env python3

import bottle, time, os, json, subprocess
from bottle import Bottle, run, request, static_file

app = Bottle()

###############################################################################
# This is the RBR website

# Endpoint: Get <server-ip>/register/<mac>
# Called to register
@app.get('/register/<mac>')
def register(mac):
    print('Register')
    return static_file('map', root='.')

# Endpoint: Get <server-ip>/resources/php/rest.php/map/<mac>
# Called to return the map
@app.get('/resources/php/rest.php/map/<mac>')
def getMap(path):
    print('Get the map')
    return static_file('map', root='.')

# Endpoint: Get <server-ip>/resources/<path:path>
# Called to return a resource file
@app.get('/resources/<path:path>')
def getFile(path):
    return static_file(path, root='resources')

# Endpoint: Get <server-ip>/
# Called to return the index file
@app.get('/')
def index():
    print('Get the index file')
    file = open('index.html', 'r')
    response = file.read()
    file.close()
    return response

# Endpoint: Get <server-ip>/sim/<data>
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

# Endpoint: Get <server-ip>/ms/<data>
# Called to report movement
@app.get('/ms/<message>')
def ms(message):
    print(message)
    return

# Endpoint: Get <server-ip>/?hum=hhh&temp=ttt&id=id
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
            message = '{"temperature": "' + str(temp) + '", "timestamp": "' + str(ts) + '"}'
            file.write(message)
            file.close()
#            print(f'Written {message} to {source}.txt')
        return
    except:
        print('Error')
        return

# Initialization

if __name__ == '__main__':
    # ip = subprocess.getoutput("hostname -I").strip()
    ip = '172.24.1.1'
    print(f'rbr.py: IP address = {ip}')
    app.run(host=ip, port=8080, debug=False)

