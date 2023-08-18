#!/bin/sh

crontab empty.txt
cp map /mnt/data/map
apt update
apt -y upgrade
rm -rf *
wget https://rbrheating.com/home/resources/dist2.tgz
tar zxf dist2.tgz
rm -f dist2.tgz
rm backup mac map
cp /mnt/data/map map
crontab crondata2.txt
reboot
