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
   cd /home/linaro/rbr
#   python3 ec.py router.ecs
   ./ecrun.py router.ecs
fi

if test -f "/mnt/data/version"
then
   rm /home/linaro/updatelog
   cd /home/linaro/rbr/
   sh update.sh >> /home/linaro/updatelog 2>&1
fi
