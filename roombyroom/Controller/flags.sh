#!/bin/sh

if test -f "/mnt/data/halt"
then
   rm /mnt/data/halt
   /usr/sbin/halt
fi

if test -f "/mnt/data/reboot"
then
   rm /mnt/data/reboot
   /usr/sbin/reboot
fi

if test -f "/mnt/data/setrouter"
then
   cd /home/orangepi
#   python3 ec.py router.ecs
   ./ecrun.py router.ecs
fi

if test -f "/mnt/data/version"
then
   rm /root/updatelog
   cd /home/orangepi/
   sh update.sh >> /root/updatelog 2>&1
fi
