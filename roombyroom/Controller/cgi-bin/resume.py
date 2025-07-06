#!/usr/bin/env python3

import os
if os.path.isfile('/mnt/data/pause'): os.remove('/mnt/data/pause')
print(f'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK')
