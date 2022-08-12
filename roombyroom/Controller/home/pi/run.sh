#!/bin/sh

cd /home/pi
cat /sys/class/net/wlan0/address >mac
python easycoder.py rbr.ecs
