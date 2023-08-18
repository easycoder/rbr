try:
    import usocket as socket
except:
    import socket
import network
import esp
esp.osdebug(None)
import time
import urequests

import gc
gc.collect()

sta_ssid = 'RBRHeating'
sta_password = 'r00m8Yr00m'
ap_ssid = 'ESP32'
ap_password = '123456789'

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=ap_ssid, password=ap_password)
while ap.active() == False:
    pass
print('Access point initialised')

wifi = network.WLAN(network.STA_IF)
wifi.active(False)
time.sleep(0.5)
wifi.active(True)

wifi.connect(sta_ssid, sta_password)

timeout = 0
if not wifi.isconnected():
    print(f'Connecting to {sta_ssid}...')
    while (not wifi.isconnected() and timeout < 5):
        print(5 - timeout)
        timeout = timeout + 1
        time.sleep(1)

if wifi.isconnected():
    print('Connected to', wifi.ifconfig())
else:
    print(f'Timeout connecting to {sta_ssid}')

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)
print('Listening on', ap.ifconfig())
while True:
    conn, addr = s.accept()
    print('Connection established from %s' % str(addr))
    request = conn.recv(1024)
    print('Content = %s' % str(request))
    response = 'Hello'
    conn.send(response)
    conn.close()

