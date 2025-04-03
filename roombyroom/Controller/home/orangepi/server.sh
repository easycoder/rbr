#!/bin/sh

if [ $# -eq 0 ]
then
    if test -f "/mnt/data/running"
    then
        exit
    fi
fi
/usr/bin/touch "/mnt/data/running"

# Look for a running instance of http.server
p=$(ps -eaf | grep "[h]ttp.server")
# Get the second item; the process number
n=$(echo $p | awk '{print $2}')
# If it's not empty, kill the process
if [ "$n" ]
then
   kill $n
fi
/usr/bin/python3 -m http.server --cgi &
