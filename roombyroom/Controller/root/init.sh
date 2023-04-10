#!/bin/sh

mkdir /mnt/data
mount -t tmpfs -o size=1M tmpfs /mnt/data
python3 rbr.py

