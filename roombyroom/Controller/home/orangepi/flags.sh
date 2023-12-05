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
   sh /home/orangepi/update.sh
fi
