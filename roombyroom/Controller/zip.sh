#!/bin/sh

# This is used on the development machine to update the distribution.

tar zcf rbr.tgz *
rm -rf ui/__pycache__
tar zcf ui.tgz ui
rm -rf ../../dev/rbr/__pycache__
tar zcf dev.tgz ../../dev/rbr
