#!/bin/sh

if [ ! -d "/home/linaro/backup" ];
then
    mkdir /home/linaro/backup
fi
cat /mnt/data/map > /home/linaro/backup/map-$(date +%Y%m%d).txt
