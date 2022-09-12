#!/bin/sh

rm -f rbr.tgz
wget https://rbrheating.com/resources/rbr.tgz
tar zxf rbr.tgz
mv rbr.ecs rbr.tmp
sudo apt update
sudo apt -y full-upgrade
mv rbr.tmp rbr.ecs
