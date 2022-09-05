#!/bin/sh

cd /home/pi
rm -f map
python3 rbr.py > log.txt &
