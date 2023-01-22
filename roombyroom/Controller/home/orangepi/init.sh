#!/bin/sh

echo $(cat mypass) | sudo mkdir /mnt/data
echo $(cat mypass) | sudo mount -t tmpfs -o size=1M tmpfs /mnt/data
echo $(cat mypass) | sudo chmod -R a+w /mnt/data/.*

rm -f map log.txt
#python3 rbr.py >> log.txt 2>&1 &
python3 rbr.py &
