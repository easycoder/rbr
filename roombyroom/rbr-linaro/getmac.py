#!/usr/bin/env python3

with open('interfaces') as f:
    lines = list(f)

for id, line in enumerate(lines):
    n = line.find(' ')
    mac = line.strip()[n:].strip()
    if line[0:n] == 'wlan0:':
        print(mac)
        exit
