#!/bin/sh

cd /home/pi
rm -f map
hostname -I > ip
python rbr.py > log.txt &
