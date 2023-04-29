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
    f = open('reflashable/version', 'r');
    version = f.read()
    f.close()
    return version

# Endpoint: GET <server-ip>/reflashable/binary
# Called to get the current reflashable binary
@app.get('/reflashable/binary')
def relaybinary():
    return static_file('reflashable/reflashable.ino.bin', root='.')

# Initialization

if __name__ == '__main__':
    ip = subprocess.getoutput("hostname -I").strip()
    if ip.rfind(' ') > 0:
        ip = '172.24.1.1'
    print(f'IP address: {ip}')
    app.run(host=ip, port=8080, debug=False)

