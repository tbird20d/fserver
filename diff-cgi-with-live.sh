#!/bin/sh
# diff the live CGI script with the current development version (./fserver.py)

diff -u /usr/lib/cgi-bin/fserver.py ./fserver.py
