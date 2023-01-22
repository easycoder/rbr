#!/usr/bin/env python3

import bottle, subprocess
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

# Initialization

if __name__ == '__main__':
    ip = subprocess.getoutput("hostname -I").strip()
    print(f'wrbr.py: IP address = {ip}')
    app.run(host=ip, port=8080, debug=False)

