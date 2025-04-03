#!/usr/bin/env python3

import os
ipaddr = os.popen('hostname -I').read()
print(f'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(ipaddr)}\r\n\r\n{ipaddr}')
