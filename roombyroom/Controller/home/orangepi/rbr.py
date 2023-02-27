#!/usr/bin/env python3

import bottle, time, os, json, subprocess, base64, requests
from os import listdir
from os.path import isfile, join
from bottle import Bottle, run, request, static_file

app = Bottle()

# Endpoint: GET <server-ip>/?hum=hhh&temp=ttt&id=id
# Called when temperature changes
@app.get('/')
def index():
    try:
        source = request.get("REMOTE_ADDR")
        hum = request.query.hum
        temp = request.query.temp
        if hum and temp:
            ts = round(time.time())
            temp = round(float(temp), 1)
            # print(f'hum={hum}, temp={temp}, source={source}, ts={ts}')
            # dir = f'{os.getcwd()}/sensors'
            dir = '/mnt/data/sensors'
            if not os.path.exists(f'{dir}'):
                os.makedirs(f'{dir}')
            file = open(f'{dir}/{source}.txt', 'w')
            message = '{"temperature": "' + str(temp) + '", "timestamp": "' + str(ts) + '"}'
            file.write(message)
            file.close()
    except:
        print('Error')

# Initialization

if __name__ == '__main__':
    ip = subprocess.getoutput("hostname -I").strip()
    app.run(host=ip, port=8080, debug=False)

