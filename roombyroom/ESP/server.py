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
            print(f'hum={hum}, temp={temp}, source={source}, ts={ts}')
    except:
        print('Error')

# Initialization

if __name__ == '__main__':
    app.run(host='172.24.1.244', port=8080, debug=False)

