#!/bin/sh

cd /home/pi
if ! [ -s mac ]
then
   cat "/sys/class/net/$(cat network)/address" >mac
fi
#exit
p=$(ps -eaf | grep "[r]br.ecs")
if [ -z "$p" ]
then
   python3 easycoder.py rbr.ecs
fi
