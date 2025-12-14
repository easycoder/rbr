#!/usr/bin/env python3
"""
This script runs every minute as a cron task.
Restarts rbr.ecs by killing any running instance and starting a new one.
"""

import os
import sys
import subprocess
import signal
import time

def main():
    # If locked, do nothing
    if os.path.isfile("/mnt/data/lock"):
        # Read the lock file
        try:
            with open("/mnt/data/lock", "r") as f:
                content = f.read().strip()
            
            if content == "lock":
                # Replace 'lock' with current timestamp
                current_time = int(time.time())
                with open("/mnt/data/lock", "w") as f:
                    f.write(str(current_time))
                print("Locked for 5 minutes")
                sys.exit(0)
            else:
                # Assume content is a timestamp
                try:
                    stored_timestamp = int(content)
                    current_time = int(time.time())
                    time_diff_minutes = (current_time - stored_timestamp) / 60
                    
                    if time_diff_minutes < 5:
                        remaining = 5 - int(time_diff_minutes)
                        if remaining == 1: print("Locked for <1 minute")
                        else: print(f"Locked for <{remaining} minutes")
                        sys.exit(0)
                    else:
                        # More than 5 minutes, delete the lock file
                        os.remove("/mnt/data/lock")
                        print(f"Lock file deleted (stale after {int(time_diff_minutes)} minutes)")
                        # Continue (do not exit)
                except ValueError:
                    # Invalid content, delete the file and continue
                    os.remove("/mnt/data/lock")
                    # Continue (do not exit)
        except Exception as e:
            print(f"Error processing lock file: {e}")
            # Continue anyway (do not exit)
    
    # Look for a running instance of rbr.ecs
    try:
        # Use ps to find rbr.ecs processes
        result = subprocess.run(
            ["ps", "-eaf"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Filter for rbr.ecs (excluding grep itself and this script)
        pid = None
        for line in result.stdout.splitlines():
            if "rbr.ecs" in line and "grep" not in line and str(os.getpid()) not in line:
                # Get the second field (PID)
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        break
                    except ValueError:
                        continue
        
        # If we found a PID, kill the process
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Killed process {pid}")
            except ProcessLookupError:
                print(f"Process {pid} already terminated")
            except PermissionError:
                print(f"Permission denied to kill process {pid}")
                sys.exit(1)
    
    except subprocess.CalledProcessError as e:
        print(f"Error running ps command: {e}")
        sys.exit(1)
    
    # Start a new instance and wait for it to complete
    try:
        result = subprocess.run(["ec", "rbr.ecs"], check=True)
        # print("rbr.ecs completed successfully")
    except:
        print("Terminated")

if __name__ == "__main__":
    main()
