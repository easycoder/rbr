#!/usr/bin/env python3

import bottle, time, os
from bottle import Bottle, run, request

app = Bottle()

###############################################################################
# This is the RBR controller

# Endpoint: Get <server-ip>/?hum=hhh&temp=ttt&id=id
# Called when temperature changes
@app.get('/')
def index():
    try:
        source = request.get("REMOTE_ADDR")
        hum = request.query.hum
        temp = request.query.temp
        if hum and temp:
            ts = time.time()
            temp = round(float(temp), 1)
#            print(f'hum={hum}, temp={temp}, source={source}, ts={ts}')
            dir = f'/home/pi/sensors/{source}'
            if not os.path.exists(f'{dir}'):
                os.makedirs(f'{dir}')
            file = open(f'{dir}/value.txt', 'w')
            message = '{"temperature": "' + str(temp) + '", "timestamp": "' + str(ts) + '"}'
            file.write(message)
            file.close()
#            print(f'Written {message} to {dir}/value.txt')
        return
    except:
        print('Error')
        return

# Initialization

if __name__ == '__main__':
    file = open('/home/pi/ip', 'r')
    ip = file.read()
    file.close()
    p = ip.rfind('.')

    app.run(host=f'{ip}', port=5555, debug=False)
