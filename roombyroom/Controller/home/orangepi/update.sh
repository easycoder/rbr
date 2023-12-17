#!/bin/sh

echo `date` -- Start the update >> /root/updatelog
echo `date` -- crontab empty.txt >> /root/updatelog
crontab empty.txt >> /root/updatelog 2>&1
echo `date` -- apt update >> /root/updatelog
apt update >> /root/updatelog 2>&1
echo `date` -- apt upgrade >> /root/updatelog
apt -y upgrade >> /root/updatelog 2>&1
echo `date` -- mkdir /home/update >> /root/updatelog
mkdir /home/update >> /root/updatelog 2>&1
echo `date` -- chmod a+rw /home/update >> /root/updatelog
chmod a+rw /home/update >> /root/updatelog 2>&1
echo `date` -- cd /home/update >> /root/updatelog
cd /home/update >> /root/updatelog 2>&1
echo `date` -- rm dist*.tgz >> /root/updatelog
rm dist*.tgz >> /root/updatelog 2>&1
echo `date` -- sudo -u orangepi wget https://rbrheating.com/home/dist.tgz >> /root/updatelog
sudo -u orangepi wget https://rbrheating.com/home/dist.tgz >> /root/updatelog 2>&1
if test -f "dist.tgz"; then
    echo `date` -- "Move the update pack" >> /root/updatelog
    echo `date` -- mv dist.tgz .. >> /root/updatelog
    mv dist.tgz .. >> /root/updatelog 2>&1
    echo `date` -- "Delete all files" >> /root/updatelog
    echo `date` -- rm -rf * >> /root/updatelog
    rm -rf * >> /root/updatelog 2>&1
    echo `date` -- "Restore the update pack" >> /root/updatelog
    echo `date` -- mv ../dist.tgz . >> /root/updatelog
    mv ../dist.tgz . >> /root/updatelog 2>&1
    echo `date` -- "Unpack the update pack" >> /root/updatelog
    echo `date` -- sudo -u orangepi tar zxf dist.tgz >> /root/updatelog
    sudo -u orangepi tar zxf dist.tgz >> /root/updatelog 2>&1
    echo `date` -- rm -f dist.tgz backup mac map >> /root/updatelog
    rm -f dist.tgz backup mac map >> /root/updatelog 2>&1
    echo `date` -- crontab cronroot.txt >> /root/updatelog
    crontab cronroot.txt >> /root/updatelog 2>&1
    echo `date` -- "Finish the update" >> /root/updatelog
    echo `date` -- sudo -u orangepi crontab crondata.txt >> /root/updatelog
    sudo -u orangepi crontab crondata.txt >> /root/updatelog 2>&1
    echo `date` -- rm /mnt/data/version >> /root/updatelog
    rm /mnt/data/version >> /root/updatelog 2>&1
    echo `date` -- cd /home/orangepi >> /root/updatelog
    cd /home/orangepi >> /root/updatelog 2>&1
    echo `date` -- rm -rf * >> /root/updatelog
    rm -rf *
    echo `date` -- cp -R ../update/* . >> /root/updatelog
    cp -R ../update/* .
    echo `date` -- "Reboot" >> /root/updatelog
    echo `date` -- /usr/sbin/reboot >> /root/updatelog
    /usr/sbin/reboot >> /root/updatelog 2>&1
    echo `date` -- exit >> /root/updatelog
    exit >> /root/updatelog 2>&1
fi
echo `date` -- Unable to complete the update pack >> /root/updatelog
echo "Unable to complete the update" >> /root/updatelog
