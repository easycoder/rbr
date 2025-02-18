import network
import espnow
import time
import asyncio
import socket
from ubinascii import hexlify, unhexlify
import json
from machine import Pin,reset
        
class Master():
    peers = []
    
    def setMAC(self, mac):
        self.mac = hexlify(sta.config('mac')).decode('utf-8')
        print('\n\nMAC Address:', self.mac)

    def addPeer(self, peer):
        peer = unhexlify(peer.encode('utf-8'))
        if not peer in peers:
            peers.append(peer)
            esp.add_peer(peer)

    def webServer(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 80))
        s.listen(5)
        while True:
            conn, addr = s.accept()
            request = conn.recv(1024)
            response = self.handleRequest(request)
            conn.send(response)
            conn.close()

    def handleRequest(self, request):
        request = request.decode('utf-8').split(' ')[1]
        if request == '/':
            return self.createResponse(200, f'RBR-XR {mac}')
        request = request.split('?')
        if len(request) > 1:
            peer = None
            request = request[1].split('&')
            for n in range(0, len(request)):
                item = request[n].split('=')
                if item[0] =='mac': peer = item[0]
                elif item[0] == 'msg': msg = item[1]
            if peer != None: esp.send(peer, f'{self.mac} {msg}')
            return createResponse(200, 'OK')
        else: return self.createResponse(404, 'No message')

    def createResponse(self, status, content):
        response = f'HTTP/1.1 {status}\r\nContent-Type: text/plain\r\n\r\n{content}'
        return response.encode('utf-8')

master = Master()
sta = network.WLAN(network.STA_IF)
sta.active(True)
master.setMAC(sta.config('mac'))
sta.connect('PLUSNET-N7C3KC','Ur4nXVQKJPrQcJ')
print('Connecting...', end='')
timeout=60
while sta.isconnected()==False:
    time.sleep(1)
    print('.',end='')
    timeout-=1
    if timeout==0:
        print('\nCan\'t connect')
        time.sleep(2)
        reset()
station=sta.ifconfig()
print('\nConnected to',station)
    
esp = espnow.ESPNow()
esp.active(True)

async def main():
    asyncio.create_task(master.webServer())
    while True:
        await asyncio.sleep(0.1)

asyncio.run(main())

