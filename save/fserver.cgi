#!/usr/bin/python
#
# fuego wiki - using Tim Bird's wiki (tbwiki)
#
# Copyright 2016 Tim R. Bird
#

import sys
import os

base_dir = "/home/tbird/work/fserver"


sys.path.append(base_dir)
from fserver_engine import *

# set up config class and req class

# define an instance to hold config vars
config = config_class()
config.data_dir = base_dir + "data"

req = req_class(config)

if __name__=="__main__":
	try:
	    main(req)
	except:
	    req.show_header("FSERVER Error")
	    print """<font color="red">Exception raised by fserver software</font>"""
	    # show traceback information here:
	    print "<pre>"
	    import traceback
	    (etype, evalue, etb) = sys.exc_info()
	    traceback.print_exception(etype, evalue, etb, None, sys.stdout)
	    print "</pre>"

