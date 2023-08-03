#!/bin/sh

crontab empty.txt
apt update
apt -y upgrade
rm -rf *
wget https://rbrheating.com/home/resources/dist.tgz
tar zxf dist.tgz
rm -f dist.tgz
rm backup mac map
crontab crondata.txt
reboot
