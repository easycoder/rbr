#!/usr/bin/python3

import urllib.request
import os

with open("version", "r") as f:
    myversion = f.read().strip()
link = "https://raw.githubusercontent.com/easycoder/rbr/refs/heads/main/roombyroom/Controller/version"
f = urllib.request.urlopen(link)
myfile = f.read()
repoversion = myfile.decode().strip()
if myversion != repoversion:
    print(f'Update to version {repoversion}')
    os.system('sh update.sh 2>>../updatelog')
