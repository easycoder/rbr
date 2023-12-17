#!/bin/sh

if test -f "/mnt/data/halt"
then
   halt
fi

if test -f "/mnt/data/reboot"
then
   reboot
fi

if test -f "/mnt/data/version"
then
   rm /root/updatelog
   sh /home/orangepi/update.sh >> /root/updatelog 2>&1
fi
