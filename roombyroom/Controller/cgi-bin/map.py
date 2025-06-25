#!/usr/bin/env python3

f = open('/mnt/data/map', 'r')
sysmap = f.read()
f.close()

response = sysmap
print(f'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(response)}\r\n\r\n{response}')
