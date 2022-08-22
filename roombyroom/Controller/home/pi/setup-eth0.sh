#!/bin/sh

echo "Set up cron"
crontab pi_cron
crontab -l
echo "Set up networking"
cat /sys/class/net/eth0/address > mac
iwgetid > essid
python easycoder.py setup-eth0.ecs
sudo cp dhcpcd.conf /etc/dhcpcd.conf
sudo dhclient -v
echo "Rebooting"
sudo reboot
