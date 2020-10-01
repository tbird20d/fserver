#!/bin/sh
#
# fix-permissions.sh
#
# make sure everything under fserver data is owned by www-data
# run this after making any manual edits

find fserver-data/ ! -user www-data | xargs sudo chown www-data.www-data
