#!/bin/sh

apt update
apt -y upgrade
cd /home/orangepi
rm -rf *
sudo -u orangepi wget https://rbrheating.com/home/dist.tgz
sudo -u orangepi tar zxf dist.tgz
rm -f dist.tgz backup mac map
crontab cronroot.txt
sudo -u orangepi crontab crondata.txt
sudo -u orangepi cp /mnt/data/map map
sudo -u orangepi mv /mnt/data/version version
reboot
