#!/bin/sh

# This script runs every minute as a cron task

# If an update is under way, do nothing
if test -f "/mnt/data/version"; then
   echo "Update under way"
   exit
fi

# Look for a running instance of rbr.ecs
p=$(ps -eaf | grep "[r]br.ecs")
# Get the second item; the process number
n=$(echo $p | awk '{print $2}')
# If it's not empty, kill the process
if [ "$n" ]
then
   kill $n
fi
# Start a new instance
ec rbr.ecs
