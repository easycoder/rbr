#!/bin/sh

# This is used on the development machine to update the distribution.

tar zcf ../../../Server/rbrheating.com/resources/rbr.tgz *.*
cd root
tar zcf ../../../Server/rbrheating.com/resources/start.tgz *
