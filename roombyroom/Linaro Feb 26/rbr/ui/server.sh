#!/bin/sh

# Look for a running instance of http.server
p=$(ps -eaf | grep "[h]ttp.server")
# Get the second item; the process number
n=$(echo $p | awk '{print $2}')
# If it's not empty, kill the process
if [ "$n" ]
then
   kill $n
fi
cd /home/linaro/rbr
/usr/bin/python3 -m http.server 17348 --cgi &
