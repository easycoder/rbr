#!/usr/bin/env python3

f = open('/mnt/data/systemdata', 'r')
systemdata = f.read()
f.close()

response = systemdata
print(f'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(response)}\r\n\r\n{response}')
