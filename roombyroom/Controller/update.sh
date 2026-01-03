#!/bin/sh

GREEN='\033[0;32m'
NOCOLOR='\033[0m'
echo `date` ---- "${GREEN}Start the update${NOCOLOR}" ----
echo `date` ---- "${GREEN}Stop root cron${NOCOLOR}" ----
echo `date` -- crontab empty.txt
crontab empty.txt
echo `date` ---- "${GREEN}Do software updates${NOCOLOR}" ----
echo `date` -- apt update
apt update
echo `date` -- apt upgrade
apt -y upgrade
echo `date` ---- "${GREEN}Update EasyCoder${NOCOLOR}" ----
echo `date` -- sudo -u linaro pip install -U easycoder
sudo -u linaro pip install -U easycoder
echo `date` ---- "${GREEN}Create the update folder and set its permissions${NOCOLOR}" ----
echo `date` -- mkdir -p /home/linaro/update
mkdir -p /home/linaro/update
echo `date` -- chmod a+rw /home/linaro/update
chmod a+rw /home/linaro/update
echo `date` ---- "${GREEN}Move to the update folder${NOCOLOR}" ----
echo `date` -- cd /home/linaro/update
cd /home/linaro/update
echo `date` ---- "${GREEN}Delete all files${NOCOLOR}" ----
echo `date` -- rm -rf *
rm -rf *
echo `date` ---- "${GREEN}Download the update pack${NOCOLOR}" ----
echo `date` -- wget https://raw.githubusercontent.com/easycoder/rbr/refs/heads/main/roombyroom/Controller/rbr.tgz
wget https://raw.githubusercontent.com/easycoder/rbr/refs/heads/main/roombyroom/Controller/rbr.tgz
echo `date` ---- "${GREEN}Test that the update pack is present${NOCOLOR}" ----
if test -f "rbr.tgz"; then
    echo `date` ---- "${GREEN}Unpack the update pack${NOCOLOR}" ----
    echo `date` -- sudo -u linaro tar zxf rbr.tgz
    sudo -u linaro tar zxf rbr.tgz
    echo `date` ---- "${GREEN}Restore root cron${NOCOLOR}" ----
    echo `date` -- crontab cronroot.txt
    crontab cronroot.txt
    echo `date` ---- "${GREEN}Set the user cron${NOCOLOR}" ----
    echo `date` -- sudo -u linaro crontab crondata.txt
    sudo -u linaro crontab crondata.txt
    echo `date` ---- "${GREEN}Remove the updater flag file${NOCOLOR}" ----
    echo `date` -- rm -f /mnt/data/version
    rm -f /mnt/data/version
    echo `date` ---- "${GREEN}Move back to the home folder${NOCOLOR}" ----
    echo `date` -- cd /home/linaro/rbr
    cd /home/linaro/rbr
    echo `date` ---- "${GREEN}Delete everything${NOCOLOR}" ----
    echo `date` -- rm -rf *
    rm -rf *
    echo `date` ---- "${GREEN}Copy everything from the update folder${NOCOLOR}" ----
    echo `date` -- sudo -u linaro cp -R /home/linaro/update/* .
    sudo -u linaro cp -R /home/linaro/update/* .
    echo `date` ---- "${GREEN}Update succeeded${NOCOLOR}" ----
    echo `date` ---- "${GREEN}Reboot${NOCOLOR}" ----
    echo `date` -- /usr/sbin/reboot
    /usr/sbin/reboot
    echo `date` ---- "${GREEN}Exit${NOCOLOR}" ----
    echo `date` -- exit
    exit
else
    echo `date` ---- "${GREEN}Update pack not found${NOCOLOR}" ----
    echo `date` ---- "${GREEN}Move back to the home folder${NOCOLOR}" ----
    echo `date` -- cd /home/linaro/rbr
    cd /home/rbr
    echo `date` ---- "${GREEN}Restore root cron${NOCOLOR}" ----
    echo `date` -- crontab cronroot.txt
    crontab cronroot.txt
    echo `date` ---- "${GREEN}Set the user cron${NOCOLOR}" ----
    echo `date` -- sudo -u linaro crontab crondata.txt
    sudo -u linaro crontab crondata.txt
    echo `date` ---- "${GREEN}Remove the updater flag file${NOCOLOR}" ----
    echo `date` -- rm /mnt/data/version
    rm -f /mnt/data/version
    echo `date` ---- "${GREEN}Update failed${NOCOLOR}" ----
fi
