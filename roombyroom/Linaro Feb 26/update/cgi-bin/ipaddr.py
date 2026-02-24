#!/usr/bin/env python3

import os
ipaddr = os.popen('hostname -I').read()

f = open('/mnt/data/ipaddr', 'w')
mac = f.write(ipaddr)
f.close()
print(f'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK')

# print(f'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(ipaddr)}\r\n\r\n{ipaddr}')
