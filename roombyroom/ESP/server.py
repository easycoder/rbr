#!/usr/bin/env python3

import bottle, time, os, json, subprocess, base64, requests
from os import listdir
from os.path import isfile, join
from bottle import Bottle, run, request, static_file

app = Bottle()

###############################################################################
# This is a server running on my PC

# Endpoint: GET <server-ip>/
# Called to return an HTML file
@app.get('/<name>')
def getHTML(name):
    # print('getHTML')
    return static_file(name, root='.')

# Endpoint: GET <server-ip>/
# Called to return the index file
@app.get('/')
def getIndex():
    # print('getIndex')
    return 'Nothing'

# Endpoint: GET <server-ip>/reflashable/version
# Called to get the current reflashable version
@app.get('/reflashable/version')
def relayversion():
    f = open('esp32_reflashable/version', 'r');
    version = f.read()
    f.close()
    return version

# Endpoint: GET <server-ip>/reflashable/binary
# Called to get the current reflashable binary
@app.get('/reflashable/binary')
def relaybinary():
    return static_file('esp32_reflashable/build/esp32.esp32.esp32da/esp32_reflashable.ino.bin', root='.')

# Endpoint: GET <server-ip>/extender/version
# Called to get the current extender version
@app.get('/extender/version')
def extenderversion():
    f = open('esp32_wifi_extender/version', 'r');
    version = f.read()
    f.close()
    return version

# Endpoint: GET <server-ip>/extender/binary
# Called to get the current extender binary
@app.get('/extender/binary')
def extenderbinary():
    return static_file('esp32_wifi_extender/build/esp32.esp32.esp32da/esp32_wifi_extender.ino.bin', root='.')

# Initialization

if __name__ == '__main__':
    ip = subprocess.getoutput("hostname -I").strip()
    if ip.rfind(' ') > 0:
        ip = '172.24.1.1'
    print(f'IP address: {ip}')
    app.run(host=ip, port=8080, debug=False)

