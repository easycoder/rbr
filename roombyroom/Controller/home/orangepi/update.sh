#!/bin/sh

crontab crondata-empty.txt
rm *.*
wget https://rbrheating.com/resources/rbr2.tgz
tar zxf rbr2.tgz
rm -f rbr2.tgz
apt update
upgrade
crontab crondata.txt
