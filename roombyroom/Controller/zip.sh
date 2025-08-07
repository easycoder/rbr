#!/bin/sh

# This is used on the development machine to update the distribution.

tar zcf /home/graham/dev/rbr/roombyroom/Server/rbrheating.com/ui/dist.tgz *
cp setup /home/graham/dev/rbr/roombyroom/Server/rbrheating.com/ui
cp version /home/graham/dev/rbr/roombyroom/Server/rbrheating.com/ui

cd /home/graham/dev/rbr/roombyroom/Controller
rm -rf ui/__pycache__
tar zcf ui.tar.gz ui
