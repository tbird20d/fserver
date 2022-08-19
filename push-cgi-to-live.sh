#!/bin/sh
# push the fserver cgi script to the live server
# (making a backup, just in case things go wrong)

DATE=$(date -Iseconds)
cp /usr/lib/cgi-bin/fserver.py ./fserver.py-$DATE
cp fserver.py /usr/lib/cgi-bin/fserver.py
