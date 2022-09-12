#!/bin/sh

echo "Set up cron"
crontab pi_cron
crontab -l
echo "Set up networking"
cat /sys/class/net/eth0/address > mac
iwgetid > essid
python3 easycoder.py setup-eth0-opi.ecs
sudo cp interfaces /etc/network/interfaces
echo "Please log in again at $essid"
sudo systemctl restart networking
