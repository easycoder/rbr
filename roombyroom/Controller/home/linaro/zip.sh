#!/bin/sh

# This is used on the development machine to update the distribution.

tar zcf ../../../Server/rbrheating.com/ui/dist.tgz *
cp setup ../../../Server/rbrheating.com/ui
cp version ../../../Server/rbrheating.com/ui
