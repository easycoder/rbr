#!/bin/sh

# This is used on the development machine to update the distribution.

tar zcf rbr.tgz *
rm -rf ui/__pycache__
tar zcf ui.tgz ui
cd ../../dev
rm -rf rbr/__pycache__ rbr.tgz
tar zcf rbr.tgz rbr
