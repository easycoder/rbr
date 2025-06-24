#!/usr/bin/env python3

f = open('/mnt/data/profile', 'r')
profile = f.read()
f.close()

response = profile
print(f'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(response)}\r\n\r\n{response}')
