#!/bin/sh

mkdir /mnt/data
mount -t tmpfs -o size=1M tmpfs /mnt/data
chmod -R a+w /mnt/data
python3 mijia.py

