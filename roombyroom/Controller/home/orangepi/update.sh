#!/bin/sh

echo `date` -- apt update >> /root/updatelog
apt update
echo `date` -- apt upgrade >> /root/updatelog
apt -y upgrade
cd /home/orangepi
echo `date` -- sudo -u orangepi cp map /mnt/data/map >> /root/updatelog
sudo -u orangepi cp map /mnt/data/map
echo `date` -- sudo -u orangepi wget https://rbrheating.com/home/dist.tgz >> /root/updatelog
sudo -u orangepi wget https://rbrheating.com/home/dist.tgz
if test -f "dist.tgz"; then
    echo "Move the update pack"
    echo `date` -- mv dist.tgz .. >> /root/updatelog
    mv dist.tgz ..
    echo "Delete all files"
    echo `date` -- rm -rf * >> /root/updatelog
    rm -rf *
    echo "Restore the update pack"
    echo `date` -- mv ../dist.tgz . >> /root/updatelog
    mv ../dist.tgz .
    echo "Unpack the update pack"
    echo `date` -- sudo -u orangepi tar zxf dist.tgz >> /root/updatelog
    sudo -u orangepi tar zxf dist.tgz
    echo `date` -- rm -f dist.tgz backup mac map >> /root/updatelog
    rm -f dist.tgz backup mac map
    echo `date` -- crontab cronroot.txt >> /root/updatelog
    crontab cronroot.txt
    echo "Finish the update"
    echo `date` -- sudo -u orangepi crontab crondata.txt >> /root/updatelog
    sudo -u orangepi crontab crondata.txt
    echo `date` -- -u orangepi cp /mnt/data/map map >> /root/updatelog
    sudo -u orangepi cp /mnt/data/map map
    rm /mnt/data/version
    echo "Reboot"
    echo `date` -- -u reboot >> /root/updatelog
    reboot
fi
echo `date` -- Unable to download the update pack >> /root/updatelog
echo "Unable to download the update pack"
