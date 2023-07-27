#!/bin/sh

# This cron script restarts the server

# Restart rbr.py
pkill rbr.py && python3 rbr.py &

# Restart mijia.py
pkill mijia.py && python3 mijia.py &
