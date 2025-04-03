#!/usr/bin/env python3

f = open('mac', 'r')
mac = f.read()
f.close()
print(f'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(mac)}\r\n\r\n{mac}')
