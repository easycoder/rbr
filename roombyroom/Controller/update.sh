#!/bin/sh

GREEN='\033[0;32m'
NOCOLOR='\033[0m'
echo `date` ---- "${GREEN}Start the update${NOCOLOR}" ---- >> /home/linaro/updatelog
echo `date` ---- "${GREEN}Stop root cron${NOCOLOR}" ---- >> /home/linaro/updatelog
echo `date` -- crontab empty.txt >> /home/linaro/updatelog
crontab empty.txt >> /home/linaro/updatelog 2>&1
echo `date` ---- "${GREEN}Do software updates${NOCOLOR}" ---- >> /home/linaro/updatelog
echo `date` -- apt update >> /home/linaro/updatelog
apt update >> /home/linaro/updatelog 2>&1
echo `date` -- apt upgrade >> /home/linaro/updatelog
apt -y upgrade >> /home/linaro/updatelog 2>&1
echo `date` ---- "${GREEN}Create the update folder and set its permissions${NOCOLOR}" ---- >> /home/linaro/updatelog
echo `date` -- mkdir /home/linaro/update >> /home/linaro/updatelog
mkdir /home/linaro/update >> /home/linaro/updatelog 2>&1
echo `date` -- chmod a+rw /home/linaro/update >> /home/linaro/updatelog
chmod a+rw /home/linaro/update >> /home/linaro/updatelog 2>&1
echo `date` ---- "${GREEN}Move to the update folder${NOCOLOR}" ---- >> /home/linaro/updatelog
echo `date` -- cd /home/linaro/update >> /home/linaro/updatelog
cd /home/linaro/update >> /home/linaro/updatelog 2>&1
echo `date` ---- "${GREEN}Delete all files${NOCOLOR}" ---- >> /home/linaro/updatelog
echo `date` -- rm -rf * >> /home/linaro/updatelog
rm -rf * >> /home/linaro/updatelog 2>&1
echo `date` ---- "${GREEN}Download the update pack${NOCOLOR}" ---- >> /home/linaro/updatelog
echo `date` -- sudo -u linaro wget https://rbrheating.com/home/dist.tgz >> /home/linaro/updatelog
sudo -u linaro wget https://rbrheating.com/ui/dist.tgz >> /home/linaro/updatelog 2>&1
if test -f "dist.tgz"; then
    echo `date` ---- "${GREEN}Unpack the update pack${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- sudo -u linaro tar zxf dist.tgz >> /home/linaro/updatelog
    sudo -u linaro tar zxf dist.tgz >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Remove unwanted files${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- rm -f dist.tgz backup mac map >> /home/linaro/updatelog
    rm -f dist.tgz backup mac map >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Restore root cron${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- crontab cronroot.txt >> /home/linaro/updatelog
    crontab cronroot.txt >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Set the user cron${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- sudo -u linaro crontab crondata.txt >> /home/linaro/updatelog
    sudo -u linaro crontab crondata.txt >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Remove the updater flag file${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- rm /mnt/data/version >> /home/linaro/updatelog
    rm /mnt/data/version >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Move back to the home folder${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- cd /home/linaro/rbr >> /home/linaro/updatelog
    cd /home/linaro/rbr >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Delete everything${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- rm -rf * >> /home/linaro/updatelog
    rm -rf * >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Copy everything from the update folder" ---- >> /home/linaro/updatelog
    echo `date` -- sudo -u linaro cp -R /home/linaro/update/* . >> /home/linaro/updatelog
    sudo -u linaro cp -R /home/linaro/update/* . >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Reboot${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- /usr/sbin/reboot >> /home/linaro/updatelog
    /usr/sbin/reboot >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Exit${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- exit >> /home/linaro/updatelog
    exit >> /home/linaro/updatelog 2>&1
else
    echo `date` ---- "${GREEN}Move back to the home folder${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- cd /home/linaro/rbr >> /home/linaro/updatelog
    cd /home/rbr >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Restore root cron${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- crontab cronroot.txt >> /home/linaro/updatelog
    crontab cronroot.txt >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Set the user cron${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- sudo -u linaro crontab crondata.txt >> /home/linaro/updatelog
    sudo -u linaro crontab crondata.txt >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Remove the updater flag file${NOCOLOR}" ---- >> /home/linaro/updatelog
    echo `date` -- rm /mnt/data/version >> /home/linaro/updatelog
    rm /mnt/data/version >> /home/linaro/updatelog 2>&1
    echo `date` ---- "${GREEN}Update failed${NOCOLOR}" ---- >> /home/linaro/updatelog
fi
