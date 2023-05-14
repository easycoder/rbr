#!/usr/bin/env python3

with open('interfaces') as f:
    lines = list(f)

for id, line in enumerate(lines):
    n = line.rfind(' ')
    lines[id] = line.strip()[n:].strip()

len = len(lines)
print(lines[len - 1])

