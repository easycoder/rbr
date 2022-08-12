#!/bin/sh

sudo apt update
sudo apt -y full-upgrade
echo "Get required Python modules"
sudo apt install -y python3-pip
pip3 install pytz bottle
