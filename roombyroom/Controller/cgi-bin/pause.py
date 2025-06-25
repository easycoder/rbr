#!/usr/bin/env python3

f = open('/mnt/data/pause', 'w')
mac = f.write('y')
f.close()
print(f'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK')
