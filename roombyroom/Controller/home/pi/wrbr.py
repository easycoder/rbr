#!/usr/bin/env python3

import bottle, time, os, json
from bottle import Bottle, run, request

app = Bottle()

###############################################################################
# This is the RBR website

# Endpoint: Get <server-ip>/status
# Called to return a status message
@app.get('/')
def index():
    file = open('/home/pi/www/index.html', 'r')
    response = file.read()
    file.close()
    return response

# Initialization

if __name__ == '__main__':
    file = open('/home/pi/ip', 'r')
    ip = file.read().strip()
    file.close()
    if ip != '':
        print(f'wrbr.py: IP address = {ip}')
        app.run(host=f'{ip}', port=8080, debug=False)
    else:
        print('wrbr.py: No IP address found')

