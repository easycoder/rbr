#!/bin/sh

crontab crondata-empty.txt
rm *.*
wget https://rbrheating.com/home/resources/dist.tgz
tar zxf dist.tgz
rm -f dist.tgz
rm backup mac map
crontab crondata.txt
apt update
apt -y upgrade
