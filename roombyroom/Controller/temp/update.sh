#!/bin/sh

crontab empty.txt
cp map /mnt/data/map
apt update
apt -y upgrade
rm -rf *
wget https://rbrheating.com/home/resources/dist.tgz
tar zxf dist.tgz
rm -f dist.tgz
rm backup mac map
cp /mnt/data/map map
crontab crondata.txt
reboot
