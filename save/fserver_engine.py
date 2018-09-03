#!/usr/bin/python
# vim: set ts=4 sw=4 et :
#
# tbwiki - Tim Bird's modular wiki
#
# Copyright (C) 2005,2006,2007..2016,2017 Tim R. Bird
#

import os, sys
import time
import cgi
import re
import string

VERSION=(0,0,1)

class stub_class:
    pass

class config_class:
    def __init__(self):
        pass

class req_class:
    def __init__(self, config):
        self.config = config
        self.head_shown = 0
        self.message = ""
        self.page_name = ""
        self.page_url = "page_name_not_set_error"
        self.page_dir = "page_dir_not_set_error"
        self.form = None
        # name of page with data being pulled into current page
        # used for things like slideshows or blogs, that get their data
        # (potentially) from another page
        self.processed_page = ""

    def set_page_name(self, page_name):
        page_name = re.sub(" ","_",page_name)
        self.page_name = page_name
        self.page_url = self.make_url(page_name)

    def page_filename(self):
        if not hasattr(self, "page_name"):
            raise AttributeError, "Missing attribute"
        return self.page_dir+os.sep+self.page_name

    def read_page(self, page_name=""):
        if not page_name:
            page_filename = self.page_filename()
        else:
                page_filename = self.page_dir+os.sep+page_name

        return open(page_filename).read()

    def get_full_page_item(self, item_ref):
        # returns first line and block contents (in a tuple)

        # item_ref can be: page_name:block_name, or :block_name
        # of just block_name (which will infer the current page)
        if item_ref.find(":") >= 0:
            page_name, block_name = item_ref.split(":",1)
            if page_name=="":
                page_name = self.page_name
        else:
            page_name = self.page_name
            block_name = item_ref

        # return a block from a page, marked by:
        # {{{<block_name> }}}
        #self.add_to_message("in get_page_item: page_name=%s, block_name=%s" % (page_name, block_name))
        try:
            data = self.read_page(page_name)
        except:
            self.add_to_message("Problem reading page: %s" % page_name)
            return ""
        lines = data.split('\n')
        #block = get_named_block(lines, block_name)
        first, content = get_named_or_numbered_block(lines, block_name)
        return first, content

    def make_url(self, page_name):
        page_name = re.sub(" ","_",page_name)
        return self.config.base_url+"/"+page_name

    def html_escape(self, str):
        # this is a dup of the global func, but it's so short it doesn't matter
        # This is here so macros and processors don't have to import tbwiki_engine
        str = re.sub("&","&amp;",str)
        str = re.sub("<","&lt;",str)
        str = re.sub(">","&gt;",str)
        return str

    def add_to_message(self, msg):
        self.message += msg + "<br>\n"

    def add_msg_and_traceback(self, msg):
        self.add_to_message(msg)
        import traceback
        tb = traceback.format_exc()
        self.add_to_message("<pre>%s\n</pre>" % tb)

    def show_header(self, title):
        if self.head_shown:
            return

        self.head_shown = 1

        # if not found, asking for the header file to be created
        self.header = """Content-type: text/html\n\n"""

        # render the header markup
        print self.header
        print '<h1 align="center">%s</h1>' % title


# end of req_class
#######################

# NOTE: this can also be called as req.html_error("error message")
# (without having to import tbwiki_engine)
def html_error(msg):
    return "<font color=red>"+msg+"</font>"

def html_escape(str):
    str = re.sub("&","&amp;",str)
    str = re.sub("<","&lt;",str)
    str = re.sub(">","&gt;",str)
    return str


def make_link(href, cover):
    return '<a href="%s">%s</a>' % (href, cover)


def get_env(key):
    if os.environ.has_key(key):
        return os.environ[key]
    else:
        return ""

def show_env(env, full=0):
    env_keys = env.keys()
    env_keys.sort()

    env_filter=["PATH_INFO", "QUERY_STRING", "REQUEST_METHOD", "SCRIPT_NAME"]
    print "Here is the environment:"
    print "<ul>"
    for key in env_keys:
        if full or key in env_filter:
            print "<li>%s=%s" % (key, env[key])
    print "</ul>"


# returns the result of the macro (in HTML format)
def call_macro(macro_name, req, args):
	mod_name = "Macro"+macro_name
	try:
		module = __import__(mod_name)
	except:
		return html_error("Error: macro '%s' not found" % macro_name)

	try:
		main_func = getattr(module, "main")
	except:
		return html_error("Error: macro '%s' missing 'main' function" % macro_name)

	return main_func(req, args)

# returns the result of the processor (in HTML format)
def call_processor(processor_name, func_name, req, content=""):
	mod_name = "Processor"+processor_name
	try:
		module = __import__(mod_name)
	except:
		req.add_msg_and_traceback('exception in call_processor')
		return html_error("Error: processor '%s' not found" % processor_name)

	try:
		processor_func = getattr(module, func_name)
	except:
		return html_error("Error: processor '%s' missing function '%s'" % (processor_name, func_name))

	# fixthis - call sub-actions with content also
	if func_name=="main":
		return processor_func(req, content)
	else:
		# FIXTHIS - call sub-actions with content as well
		#return processor_func(req, content)
		return processor_func(req)


def main(req):
    # parse request
    query_string = get_env("QUERY_STRING")
    if query_string=="test":
        req.show_header("TBWiki test")
        show_env(os.environ)
        print "</body>"
        return

    # determine action, if any
    query_parts = query_string.split("&")
    action = "show"
    for qpart in query_parts:
        if qpart.split("=")[0]=="action":
            action=qpart.split("=")[1]

    #req.add_to_message('action="%s"<br>' % action)

    # get page name
    page_name = get_env("PATH_INFO")
    if page_name:
        page_name = page_name[1:]
        req.set_page_name(page_name)
    else:
        req.add_to_message("Missing page name")
        action = "error"

    req.action = action
    req.page_dir = req.config.data_dir + "pages"
    # NOTE: we could put themes somewhere else, if we considered
    # it a security issue.

    # put this in, when you get a 500 error
    req.show_header('TRB Debug')

    # perform action
    handled = 0
    page_data = ""
    req.form = cgi.FieldStorage()

    show_env(os.environ)


    print("in main request loop: action='%s'<br>" % action)
	# consolidate permission checking for many actions here
    if action=="show":
        try:
            page_data = open(req.page_filename()).read()
        except:
            # if page not found on a 'show', make form for creating it
            page_data = "page filename %s not found" % page_filename

	# check for processor actions (e.g. action=Blog)
	if action in req.processor_list:
		result = call_processor(action, "main", req, "")

	# check for processor sub-actions (e.g. action=SlideShow.show)
	if action.find(".")!=-1:
	    (action_processor, action_function) = action.split(".",1)
	    if action_processor in req.processor_list:
		# now call it (pass it the original block content)
		content = ""
		# FIXTHIS - look up original block content for sub-actions
		#try:
		#	block_name = req.form["block_name"].value
		#	content = req.get_page_item(block_name)
		#except:
		#	req.add_msg_and_traceback("problem getting block content")
		#	pass
		req.state = parse_state(req)

		data = call_processor(action_processor, action_function, req, content)

		#req.add_to_message("data from processor_func: %s = '%s'" % (action_processor, data))

    if not handled:
        req.show_header("TBWiki Error")
        print html_error("Unknown action '%s'" % action)

if __name__=="__main__":
	try:
	    main(req)
	except:
	    req.show_header("TBWIKI Error")
	    print """<font color="red">Exception raised by tbwiki software</font>"""
	    # show traceback information here:
	    print "<pre>"
	    import traceback
	    (etype, evalue, etb) = sys.exc_info()
	    traceback.print_exception(etype, evalue, etb, None, sys.stdout)
	    print "</pre>"


