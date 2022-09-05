#!/bin/sh

rm -f rbr.tgz
wget https://rbrheating.com/resources/rbr.tgz
tar zxf rbr.tgz
mv rbr.ecs rbr.tmp
sudo apt update
sudo apt -y full-upgrade
echo "Get required Python modules"
sudo apt install -y python3-pip
pip3 install pytz bottle requests
mv rbr.tmp rbr.ecs
