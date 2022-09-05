#!/bin/sh

cd /home/pi
cat /sys/class/net/eth0/address >mac
python3 easycoder.py rbr.ecs
