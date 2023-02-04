#!/bin/sh

mkdir /mnt/data
mount -t tmpfs -o size=1M tmpfs /mnt/data
sleep 10
python3 rbr.py &

