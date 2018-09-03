#!/usr/bin/python
# vim: set ts=4 sw=4 et :
#
# fserver.py - Fuego server CGI script
#
# Copyright 2018 Sony
#

import sys
import os
import time
import cgi
import re
import json

VERSION=(0,1,0)

base_dir = "/home/tbird/work/fserver"

class config_class:
    def __init__(self):
        pass

    def __getitem__(self, name):
        return self.__dict__[name]

class req_class:
    def __init__(self, config):
        self.config = config
        self.header_shown = False
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

    def make_url(self, page_name):
        page_name = re.sub(" ","_",page_name)
        return self.config.url_base+"/"+page_name

    def html_escape(self, str):
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

    def show_message(self):
        if self.message:
            print("<h2>fserver message(s):</h2>")
            print(self.message)

    def show_header(self, title):
        if self.header_shown:
            return

        self.header_shown = True

        self.header = """Content-type: text/html\n\n"""

        # render the header markup
        print(self.header)
        print('<body><h1 align="center">%s</h1>' % title)

    def show_footer(self):
        self.show_message()
        print("</body>")

    def html_error(msg):
        return "<font color=red>" + msg + "</font>"


# end of req_class
#######################

# NOTE: this can also be called as req.html_error("error message")
# (without having to import tbwiki_engine)

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

"""
To do:
 - add ability for query_requests to process attributes inside the file
 instead of just in the filename, and handle wildcards

"""
def do_help(req):
    req.show_header("ProcessorFuego Help")
    print("""The Fuego processor is used to implement
the server functions of a Fuego central server.
<p>
This includes handling things like file uploads and downloads, and data queries.
<p>
By default, this module just shows a list of things that can be done manually.
""")

def get_timestamp():
    t = time.time()
    tfrac = int((t - int(t))*100)
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S.") + "%02d" % tfrac
    return timestamp

def save_file(req, file_field, upload_dir):
    # some debugging...
    F = "FAIL"
    msg = ""

    #msg += "req.form=\n"
    #for k in req.form.keys():
    #   msg += "%s: %s\n" % (k, req.form[k])

    if not req.form.has_key(file_field):
        return F, msg+"Form is missing key %s\n" % file_field, ""

    fileitem = req.form[file_field]
    if not fileitem.file:
        return F, msg+"fileitem has no attribute 'file'\n", ""

    if not fileitem.filename:
        return F, msg+"fileitem has no attribute 'filename'\n", ""

    filepath = upload_dir + os.sep +  fileitem.filename
    if os.path.exists(filepath):
        return F, msg+"Already have a file %s. Cannot proceed.\n" % fileitem.filename, ""

    fout = open(filepath, 'wb')
    while 1:
        chunk = fileitem.file.read(100000)
        if not chunk:
            break
        fout.write(chunk)
    fout.close()
    msg += "File '%s' uploaded successfully!\n" % fileitem.filename
    return "OK", msg, filepath

def send_response(result, data):
    sys.stdout.write("Content-type: text/html\n\n%s\n" % result)
    sys.stdout.write(data)

def do_put_test(req):
    upload_dir = req.config.files_dir + os.sep + "tests"
    result, msg, filepath = save_file(req, "file1", upload_dir)

    if result != "OK":
        send_response(result, msg)
        return

    # should sanity-check the manifest (yaml) file here!
    filename = os.path.basename(filepath)
    if not filename.endswith(".ftp"):
        msg += "Invalid filename for test specified: %s (expected .ftp extension)\n" % filename
        os.unlink(filepath)
        send_response("FAIL", msg)
        return

    msg += "Created %s\n" % filepath

    test_name = filename.split("-",1)[0]

    # extract yaml file
    pd = req.page_dir
    tn = test_name
    cmd = "tar -C %s -xf %s %s/test.yaml" % (pd, filepath, tn)
    result = os.system(cmd)
    yaml_fname = "%s/%s/test.yaml" % (pd, tn)
    yaml_pname = "%s/%s.yaml" % (pd, tn)
    if not os.path.exists(yaml_fname):
        msg += "Error: can't find %s\n after extraction" % yaml_fname
        send_response("FAIL", msg)
        return

    os.rename(yaml_fname, yaml_pname)
    os.rmdir("%s/%s" % (pd, tn))

    msg += "Created %s page\n" % yaml_pname

        # create wrapper tbwiki page for test
    page_content = """Here is data for test package %(page_name)s:

<hr>
{{{#!FuegoShow
item_ref=page_name.yaml
}}}
--------

Go to [[Tests]] page.
"""
    req.write_page(page_content, test_name)
    msg += "Created %s page\n" % test_name

    send_response("OK", msg)

def do_put_run(req):
    # FIXTHIS - could consolidate put_test and put_run
    upload_dir = req.config.files_dir + os.sep + "runs"
    result, msg, filepath = save_file(req, "file1", upload_dir)

    # should sanity-check the manifest (json) file here!

    # should be something like:
    # run-2016-02-16_12-21-00-Functional.bc-timdesk:bbb-poky-sdk.frp
    filename = os.path.basename(filepath)
    if not filename.startswith("run-") or not filename.endswith(".frp"):
        msg ++ "Invalid filename for run specified: %s" % filename
        send_response("FAIL", msg)
        return

        run_name = filename[4:-4]
    msg += "Created %s\n" % filepath

    # extract json file
    pd = req.page_dir
    rn = run_name
    cmd = "tar -C %s -xf %s run/run.json --force-local" % (pd, filepath)
    msg += "Tar cmd=%s\n" % cmd
    rcode = os.system(cmd)
    if rcode != 0:
        send_response("FAIL", msg+"Could not extract run/run.json file")
        return

    json_fname = "%s/run/run.json" % (pd)
    json_pname = "%s/run-%s.json" % (pd, rn)
    if not os.path.exists(json_fname):
        send_response("FAIL", msg+"Missing run/run.json file in %s" % pd)
        return

    os.rename(json_fname, json_pname)
    os.rmdir("%s/run" % pd)

    # FIXTHIS - should return url here instead of full server path??
    msg += "Created %s page\n" % json_pname

        # read json file and create tbwiki page for test??

    send_response("OK", msg)


def do_put_request(req):
    upload_dir = req.config.files_dir + os.sep + "requests/"
    result = "OK"
    msg = ""


    #convert form (cgi.fieldStorage) to dictionary
    mydict = {}
    for k in req.form.keys():
        mydict[k] = req.form[k].value

    mydict["state"] = "new"
    timestamp = get_timestamp()
    mydict["request_time"] = timestamp

    try:
        host = mydict["host"]
        board = mydict["board"]
    except:
        result = "FAIL"
        msg += "Error: missing host or board in form data"

    filename = "request-%s-%s:%s" % (timestamp, host, board)
    jfilepath = upload_dir + filename + ".json"

    msg += "Filename '%s' calculated!\n" % jfilepath

    # convert to json and save to file here
    data = json.dumps(mydict, sort_keys=True, indent=4, separators=(',', ': '))
    fout = open(jfilepath, "w")
    fout.write(data+'\n')
    fout.close()

    page_filepath = req.page_dir + os.sep + filename

    # convert to tbwikidb and save to file here
    keylist = mydict.keys()

    # FIXTHIS - could write only known fields here, to prevent abuse
    # remove the 'action' key
    keylist.remove("action")

    keylist.sort()
    fout = open(page_filepath, "w")

    # FIXTHIS - this doesn't handle multi-line fields.  They should be put
    # into a section
    for k in keylist:
        fout.write("; %s: %s\n" % (k, mydict[k]))
    fout.close()

    msg += "data=%s\n" % data
    msg += "page_filepath=%s\n" % page_filepath

    send_response(result, msg)

# try matching with simple wildcards (* at start or end of string)
def item_match(pattern, item):
    if pattern=="*":
        return True
    if pattern==item:
        return True
    if pattern.endswith("*") and \
        pattern[:-1] == item[:len(pattern)-1]:
        return True
    if pattern.startswith("*") and \
        pattern[1:] == item[-(len(pattern)-1):]:
        return True
    return False

def do_query_requests(req):
    download_dir = req.config.files_dir + os.sep + "requests/"
    msg = ""
    filelist = os.listdir(download_dir)
    filelist.sort()

    # can query by different fields, some in the name and some inside
    # the json

    try:
        query_host = req.form["host"].value
    except:
        query_host = "*"

    try:
        query_board = req.form["board"].value
    except:
        query_board = "*"

    # handle host and board-based queries
    match_list = []
    for f in filelist:
        if f.startswith("request-") and f.endswith("json"):
            host_and_board = f[31:-5]
            if not host_and_board:
                continue
            if not item_match(query_host, host_and_board.split(":")[0]):
                continue
            if not item_match(query_board, host_and_board.split(":")[1]):
                continue
            match_list.append(f)

    # FIXTHIS - read files and filter by attributes
    # particularly filter on 'state'

    for f in match_list:
       msg += f+"\n"

    send_response("OK", msg)

def read_tbwikidb_file(file_path):
    # try opening the file
    fin = open(file_path)

    record = {}
    first_attr_name = ""
    in_section = 0
    section_name = "no section"
    section_data = ""
    line_no = 0
    for line in fin.readlines():
        line_no += 1
        #dtprint(tb, "line='%s'" % line)

        # check for definition (e.g "; field_name: field value")
        m = re.match(r"^; (.*?):(.*)", line)
        if m:
            attr = m.groups()[0].strip()
            value = m.groups()[1]

            #dtprint(tb, "found a definition: %s = '%s'" % (attr, value))
            # convert spaces to underscores
            attr = re.sub(" ","_",attr)

            # this is a single-line, just record the attribute
            # no leading or trailing whitespace is allowed on single-line values
            record[attr] = value.strip()
            if not first_attr_name:
                first_attr_name = attr

        # check for L1 section
        m = re.match(r"^= +([^=]*)=.*", line)
        if m:
            if in_section:
                record[section_name] = section_data

            in_section = 1
            section_name = m.groups()[0].strip()
            #dtprint(tb, "found an L1 section: %s" % section_name)
            if not first_attr_name:
                first_attr_name = section_name
            continue

        if in_section:
            section_data += line

    # finish the last section, if any
    if in_section:
        record[section_name] = section_data

    return record

# FIXTHIS - could do get_next_request (with wildcards) to save a query
def do_get_request(req):
    requests_dir = req.config.files_dir + "/requests"
    msg = ""

    # handle host and target-based queries
    msg += "In ProcessorFuego.py:get_request\n"
    try:
        request_id = req.form["request_id"].value
    except:
        msg += "Error: can't read request_id from form"
        send_response("FAIL", msg)

    filepath = requests_dir + os.sep +request_id
    if not os.path.exists(filepath):
        msg += "Error: filepath %s does not exist" % filepath
        send_response("FAIL", msg)

    # read requested file
    request_fd = open(filepath, "r")
    mydict = json.load(request_fd)

    # beautify the data, for now
    data = json.dumps(mydict, sort_keys=True, indent=4, separators=(',', ': '))
    send_response("OK", data)

def do_remove_request(req):
    requests_dir = req.config.files_dir + "/requests"
    msg = ""

    try:
        request_id = req.form["request_id"].value
    except:
        msg += "Error: can't read request_id from form"
        send_response("FAIL", msg)
        return

    filepath = requests_dir + os.sep +request_id
    if not os.path.exists(filepath):
        msg += "Error: filepath %s does not exist" % filepath
        send_response("FAIL", msg)
        return

    os.remove(filepath)

    msg += "Request file %s was removed" % filepath
    send_response("OK", msg)


def file_list_html(req, subdir, extension):
    full_dirlist = os.listdir(req.config.files_dir+os.sep+subdir)
    full_dirlist.sort()

    # filter list to only .ftp files
    filelist = []
    for d in full_dirlist:
        if d.endswith(extension):
            filelist.append(d)

    if not filelist:
        return req.html_error("No %s files found." % subdir[:-1])

    files_url = "/files/%s/" % subdir
    html = "<ul>"
    for item in filelist:
        html += '<li><a href="'+files_url+item+'">' + item + '</a></li>\n'
    html += "</ul>"
    return html


def do_show(req):
    req.show_header("Fuego server objects")
    #print("req.page_name='%s' <br><br>" % req.page_name)

    if req.page_name == "fserver.py":
        title = "Links to object lists"
    else:
        title = "List of %s" % req.page_name

    print("<H1>%s</h1>" % title)

    if req.page_name=="Tests":
        print(file_list_html(req, "tests", ".ftp"))

    if req.page_name=="Requests":
        print(file_list_html(req, "requests", ".json"))

    if req.page_name=="Runs":
        print(file_list_html(req, "runs", ".frp"))

    print("""Here are links to the different Fuego objects:<br>
<ul>
<li><a href="%(url_base)s/Tests">Tests</a></li>
<li><a href="%(url_base)s/Requests">Requests</a></li>
<li><a href="%(url_base)s/Runs">Runs</a></li>
</ul>
<hr>
""" % req.config )

    print("""<a href="%(url_base)s">Back to home page</a>""" % req.config)

def old_do_show(req):
    page_filename = req.page_filename()
    try:
        page_data = open(req.page_filename()).read()
    except:
        # if page not found on a 'show', make form for creating it
        page_data = "page filename %s not found" % page_filename
    return

def main(req):
    # parse request
    query_string = get_env("QUERY_STRING")

    # determine action, if any
    query_parts = query_string.split("&")
    action = "show"
    for qpart in query_parts:
        if qpart.split("=")[0]=="action":
            action=qpart.split("=")[1]

    #req.add_to_message('action="%s"<br>' % action)

    # get page name
    page_name = get_env("PATH_INFO")
    if "/" in page_name:
        page_name = os.path.basename(page_name)
        req.set_page_name(page_name)
    else:
        req.add_to_message("Missing page name")
        action = "error"

    #req.add_to_message("page_name=%s" % page_name)

    req.action = action
    req.page_dir = req.config.data_dir + "/pages"

    # NOTE: uncomment this when you get a 500 error
    #req.show_header('TRB Debug')
    #show_env(os.environ)
    #print("in main request loop: action='%s'<br>" % action)

    # perform action
    req.form = cgi.FieldStorage()

    # map action names to "do_<action>" functions
    if action in ["show", "put_test", "put_run", "put_request",
            "query_requests", "get_request", "remove_request"]:
        action_function = globals().get("do_" + action)
        action_function(req)
        return

    req.show_header("TBWiki Error")
    print(req.html_error("Unknown action '%s'" % action))


# define an instance to hold config vars
config = config_class()
config.data_dir = base_dir
config.url_base = "/fserver.py"
config.files_dir = base_dir + "/files"

req = req_class(config)

if __name__=="__main__":
    try:
        main(req)
        req.show_message()
    except:
        req.show_header("FSERVER Error")
        print """<font color="red">Exception raised by fserver software</font>"""
        # show traceback information here:
        print "<pre>"
        import traceback
        (etype, evalue, etb) = sys.exc_info()
        traceback.print_exception(etype, evalue, etb, None, sys.stdout)
        print "</pre>"
