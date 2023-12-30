#!/bin/sh

GREEN='\033[0;32m'
NOCOLOR='\033[0m'
echo `date` ---- "${GREEN}Start the update${NOCOLOR}" ---- >> /root/updatelog
echo `date` ---- "${GREEN}Stop root cron${NOCOLOR}" ---- >> /root/updatelog
echo `date` -- crontab empty.txt >> /root/updatelog
crontab empty.txt >> /root/updatelog 2>&1
echo `date` ---- "${GREEN}Do software updates${NOCOLOR}" ---- >> /root/updatelog
echo `date` -- apt update >> /root/updatelog
apt update >> /root/updatelog 2>&1
echo `date` -- apt upgrade >> /root/updatelog
apt -y upgrade >> /root/updatelog 2>&1
echo `date` ---- "${GREEN}Create the update folder and set its permissions${NOCOLOR}" ---- >> /root/updatelog
echo `date` -- mkdir /home/update >> /root/updatelog
mkdir /home/update >> /root/updatelog 2>&1
echo `date` -- chmod a+rw /home/update >> /root/updatelog
chmod a+rw /home/update >> /root/updatelog 2>&1
echo `date` ---- "${GREEN}Move to the update folder${NOCOLOR}" ---- >> /root/updatelog
echo `date` -- cd /home/update >> /root/updatelog
cd /home/update >> /root/updatelog 2>&1
echo `date` ---- "${GREEN}Delete all files${NOCOLOR}" ---- >> /root/updatelog
echo `date` -- rm -rf * >> /root/updatelog
rm -rf * >> /root/updatelog 2>&1
echo `date` ---- "${GREEN}Download the update pack${NOCOLOR}" ---- >> /root/updatelog
echo `date` -- sudo -u orangepi wget https://rbrheating.com/home/dist.tgz >> /root/updatelog
sudo -u orangepi wget https://rbrheating.com/home/dist.tgz >> /root/updatelog 2>&1
if test -f "dist.tgz"; then
    echo `date` ---- "${GREEN}Unpack the update pack${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- sudo -u orangepi tar zxf dist.tgz >> /root/updatelog
    sudo -u orangepi tar zxf dist.tgz >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Remove unwanted files${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- rm -f dist.tgz backup mac map >> /root/updatelog
    rm -f dist.tgz backup mac map >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Restore root cron${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- crontab cronroot.txt >> /root/updatelog
    crontab cronroot.txt >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Set the user cron${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- sudo -u orangepi crontab crondata.txt >> /root/updatelog
    sudo -u orangepi crontab crondata.txt >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Remove the updater flag file${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- rm /mnt/data/version >> /root/updatelog
    rm /mnt/data/version >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Move back to the home directory${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- cd /home/orangepi >> /root/updatelog
    cd /home/orangepi >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Delete everything${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- rm -rf * >> /root/updatelog
    rm -rf * >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Copy everything from the update directory${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- sudo -u orangepi cp -R ../update/* . >> /root/updatelog
    sudo -u orangepi cp -R ../update/* . >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Reboot${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- /usr/sbin/reboot >> /root/updatelog
    /usr/sbin/reboot >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Exit${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- exit >> /root/updatelog
    exit >> /root/updatelog 2>&1
else
    echo `date` ---- "${GREEN}Restore root cron${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- crontab cronroot.txt >> /root/updatelog
    crontab cronroot.txt >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Set the user cron${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- sudo -u orangepi crontab crondata.txt >> /root/updatelog
    sudo -u orangepi crontab crondata.txt >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Remove the updater flag file${NOCOLOR}" ---- >> /root/updatelog
    echo `date` -- rm /mnt/data/version >> /root/updatelog
    rm /mnt/data/version >> /root/updatelog 2>&1
    echo `date` ---- "${GREEN}Update failed${NOCOLOR}" ---- >> /root/updatelog
fi
