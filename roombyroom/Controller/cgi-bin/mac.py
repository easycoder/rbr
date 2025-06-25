#!/usr/bin/env python3

f = open('mac', 'r')
mac = f.read().strip()
f.close()
f = open('/mnt/data/password', 'r')
password = f.read()
f.close()
f = open('/mnt/data/name', 'r')
name = f.read()
f.close()

response = f'{mac} {password} {name}'
print(f'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(response)}\r\n\r\n{response}')
