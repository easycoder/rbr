#!/usr/bin/env python3
"""
This script runs every minute as a cron task.
Checks if an update is under way, and if so, locks the controller.
Then runs rbr.py. This will cancel the lock after 20 minutes
"""

import os
import subprocess

def main():
    # If an update is under way, do nothing
    if os.path.isfile("/mnt/data/update"):
        print("Update under way")
    
        # Lock the controller
        with open("/mnt/data/lock", "w") as f:
            f.write("lock")
    
    # Run rbr.py
    try:
        result = subprocess.run(["python3", "rbr.py"], check=True)
        # print("rbr.py completed successfully")
    except: pass

if __name__ == "__main__":
    main()
