#!/bin/sh

cd /home/pi
rm -f map
python rbr.py > log.txt &
