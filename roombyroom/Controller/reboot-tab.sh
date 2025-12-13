#!/bin/sh

mkdir /mnt/data
chown graham:graham /mnt/data
mount -t tmpfs -o size=1M tmpfs /mnt/data
rm /home/graham/dev/roombyroom/Controller/log.txt
