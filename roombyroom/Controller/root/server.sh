#!/bin/sh

# This cron script restarts the server
# Look for a running instance of rbr.py
p=$(ps -eaf | grep "[r]br.py")
# Get the second item; the process number
n=$(echo $p | awk '{print $2}')
# If it's not empty, kill the process
if [ "$n" ]
then
   kill $n
fi
# Start a new instance
python3 rbr.py &

# Look for a running instance of mijia.py
p=$(ps -eaf | grep "[m]ijia.py")
# Get the second item; the process number
n=$(echo $p | awk '{print $2}')
# If it's not empty, kill the process
if [ "$n" ]
then
   kill $n
fi
# Start a new instance
python3 mijia.py &
# Remove the restart flag (if it exists)
rm /mnt/data/restart
