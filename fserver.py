#!/usr/bin/python
# vim: set ts=4 sw=4 et :
#
# fserver.py - Fuego server CGI script
#
# Copyright 2018 Sony
#
# Implementation notes:
#  files directory = place where uploaded file bundles are stored
#  data directory = place where yaml/json (data) files are stored
#  pages directory = place where web pages are stored
#
# When a file bundle is uploaded, the meta-data file (either json or yaml)
# is extracted, and placed in the data directory.
#
# The server implements both the human user interace (web pages showing
# the status of the object store), and the computer ReST interface (used
# for sending, modifying and retrieving the data in the store)
#
# To do:
# - queries:
#1   - add ability for query_requests to process attributes inside
#     the file instead of just in the filename
#   - handle regex wildcards instead of just start/end wildcards
# - actions:
#   - support update-request
# - objects:
#   - support host registration
#   - support board registration
# - security:
#   - add otp authentication to all requests
#     - check host's otp file for specified key
#     - erase key after use
# - add hosts
#    - so we can: 1) save an otp file, 2) validate requests?
# - see also items marked with FIXTHIS
#

import sys
import os
import time
import cgi
import re
# import these as needed
#import json
#import yaml

VERSION=(0,2,0)

# precedence of installation locations:
# 1. global fserver on fuegotest.org (/home/ubuntu/work/fserver)
# 2. local fserver in Fuego container
# 3. test fserver on Tim's home desktop machine
base_dir = "/home/ubuntu/work/fserver/fserver-data"
if not os.path.exists(base_dir):
    base_dir = "/usr/local/lib/fserver/fserver-data"
if not os.path.exists(base_dir):
    base_dir = "/home/tbird/work/fserver/fserver-data"

# this is used for debugging only
def log_this(msg):
    with open(base_dir+"/fserver.log" ,"a") as f:
        f.write("[%s] %s\n" % (get_timestamp(), msg))

# define an instance to hold config vars
class config_class:
    def __init__(self):
        pass

    def __getitem__(self, name):
        return self.__dict__[name]

config = config_class()
config.data_dir = base_dir + "/data"

# crude attempt at auto-detecting url_base
if os.path.exists("/usr/lib/cgi-bin/fserver.py"):
    config.url_base = "/cgi-bin/fserver.py"
else:
    config.url_base = "/fserver.py"

config.files_url_base = "/fserver-data"
config.files_dir = base_dir + "/files"
config.page_dir = base_dir + "/pages"

class req_class:
    def __init__(self, config):
        self.config = config
        self.header_shown = False
        self.message = ""
        self.page_name = ""
        self.page_url = "page_name_not_set_error"
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
        return self.config.page_dir+os.sep+self.page_name

    def read_page(self, page_name=""):
        if not page_name:
            page_filename = self.page_filename()
        else:
                page_filename = self.config.page_dir+os.sep+page_name

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

    def html_error(self, msg):
        return "<font color=red>" + msg + "</font><BR>"


# end of req_class
#######################

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
    sys.stdout.flush()
    sys.exit(0)

def do_put_test(req):
    upload_dir = req.config.files_dir + os.sep + "tests"
    result, msg, filepath = save_file(req, "file1", upload_dir)

    if result != "OK":
        send_response(result, msg)

    # FIXTHIS - should sanity-check the manifest (yaml) file here!
    filename = os.path.basename(filepath)
    if not filename.endswith(".ftp"):
        msg += "Invalid filename for test specified: %s (expected .ftp extension)\n" % filename
        os.unlink(filepath)
        send_response("FAIL", msg)

    msg += "Created %s\n" % filepath

    test_name = filename.split("-",1)[0]

    test_data_dir = req.config.data_dir + os.sep + "tests"

    # extract yaml file into data dir
    tdd = test_data_dir
    tn = test_name
    tn_with_version = filename[:-4]
    cmd = "tar -C %s -xf %s %s/test.yaml" % (tdd, filepath, tn)
    result = os.system(cmd)
    yaml_src_name = "%s/%s/test.yaml" % (tdd, tn)
    yaml_dest_name = "%s/%s.yaml" % (tdd, tn_with_version)
    if not os.path.exists(yaml_src_name):
        msg += "Error: can't find %s\n in extracted .ftp contents" % yaml_src_name
        send_response("FAIL", msg)

    os.rename(yaml_src_name, yaml_dest_name)
    os.rmdir("%s/%s" % (tdd, tn))

    msg += "Extracted %s from uploaded file\n" % yaml_dest_name

    # create wrapper tbwiki page for test
#    page_content = """Here is data for test package %(page_name)s:
#
#<hr>
#{{{#!FuegoShow
#item_ref=page_name.yaml
#}}}
#--------
#
#Go to [[Tests]] page.
#"""
#    req.write_page(page_content, test_name)
#    msg += "Created %s page\n" % test_name

    send_response("OK", msg)

def do_put_run(req):
    # FIXTHIS - could consolidate put_test and put_run
    upload_dir = req.config.files_dir + os.sep + "runs"
    result, msg, filepath = save_file(req, "file1", upload_dir)

    # should sanity-check the manifest (json) file here!

    # should be something like:
    # run-2016-02-16_12-21-00-Functional.bc-on-timdesk:bbb.frp
    filename = os.path.basename(filepath)
    if not filename.startswith("run-") or not filename.endswith(".frp"):
        msg += "Invalid filename for run specified: %s" % filename
        send_response("FAIL", msg)

    run_name = filename[4:-4]
    msg += "Created %s\n" % filepath

    # extract json file into data dir
    run_data_dir = req.config.data_dir + os.sep + "runs"

    rdd = run_data_dir
    rn = run_name
    cmd = "tar -C %s -xf %s run/run.json --force-local" % (rdd, filepath)
    msg += "Tar cmd=%s\n" % cmd
    rcode = os.system(cmd)
    if rcode != 0:
        send_response("FAIL", msg+"Could not extract run/run.json file")

    json_src_name = "%s/run/run.json" % (rdd)
    json_dest_name = "%s/run-%s.json" % (rdd, rn)
    if not os.path.exists(json_src_name):
        msg += "Error: can't find %s\n in extracted .frp contents" % json_src_name
        send_response("FAIL", msg)

    os.rename(json_src_name, json_dest_name)
    os.rmdir("%s/run" % rdd)

    # FIXTHIS - should return url here instead of full server path??
    msg += "Extracted %s from uploaded file\n" % json_dest_name

    # create tbwiki page for test??
    # skip for now

    send_response("OK", msg)


def do_put_request(req):
    req_data_dir = req.config.data_dir + os.sep + "requests"
    result = "OK"
    msg = ""

    #convert form (cgi.fieldStorage) to dictionary
    mydict = {}
    for k in req.form.keys():
        mydict[k] = req.form[k].value

    mydict["state"] = "pending"
    timestamp = get_timestamp()
    mydict["request_time"] = timestamp

    # remove action
    del(mydict["action"])

    # sanity check the submitted data
    # check for host and board
    try:
        host = mydict["host"]
        board = mydict["board"]
        # FIXTHIS - check that host and board are registered
    except:
        result = "FAIL"
        msg += "Error: missing host or board in form data"

    filename = "request-%s-%s:%s" % (timestamp, host, board)
    jfilepath = req_data_dir + os.sep + filename + ".json"

    msg += "Filename '%s' calculated!\n" % jfilepath

    # convert to json and save to file here
    import json
    data = json.dumps(mydict, sort_keys=True, indent=4, separators=(',', ': '))
    fout = open(jfilepath, "w")
    fout.write(data+'\n')
    fout.close()

    send_response(result, msg)

def do_update_request(req):
    req_data_dir = req.config.data_dir + os.sep + "requests"
    msg = ""

    try:
        request_id = req.form["request_id"].value
    except:
        msg += "Error: can't read request_id from form"
        send_response("FAIL", msg)

    filename = request_id
    filepath = req_data_dir + os.sep + filename
    if not os.path.exists(filepath):
        msg += "Error: filepath %s does not exist" % filepath
        send_response("FAIL", msg)

    # read requested file
    import json
    request_fd = open(filepath, "r")
    req_dict = json.load(request_fd)
    request_fd.close()

    # update fields from (cgi.fieldStorage)
    for k in req.form.keys():
        if k in ["request_id", "action"]:
            # skip these
            continue
        if k in ["state", "run_id"]:
            # FIXTHIS - could check the data input here
            req_dict[k] = req.form[k].value
        else:
            msg = "Error - can't change field '%s' in request" % k
            send_response("FAIL", msg)

    # put dictionary back in json format (beautified)
    data = json.dumps(req_dict, sort_keys=True, indent=4, separators=(',', ': '))
    fout = open(filepath, "w")
    fout.write(data+'\n')
    fout.close()

    send_response("OK", data)

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
    #log_this("TRB: in do_query_requests 1")
    req_data_dir = req.config.data_dir + os.sep + "requests"
    msg = ""

    filelist = os.listdir(req_data_dir)
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

    # read files and filter by attributes
    # (particularly filter on 'state')
    if match_list:
        import json

        # read the first file to get the list of possible attributes
        f = match_list[0]
        with open(req_data_dir + os.sep + f) as jfd:
            data = json.load(jfd)
            # get a list of valid attributes
            fields = data.keys()

            # get rid of fields already processed
            fields.remove("host")
            fields.remove("board")

        # check the form for query attributes
        # if they have the same name as a valid field, then add to list
        query_fields={}
        for field in fields:
            try:
                query_fields[field] = req.form[field].value
            except:
                pass

        # if more to query by, then go through files, preserving matches
        if query_fields:
            ml_tmp = []
            for f in match_list:
                drop = False
                with open(req_data_dir + os.sep + f) as jfd:
                    data = json.load(jfd)
                    for field, pattern in query_fields.items():
                        if not item_match(pattern, str(data[field])):
                            drop = True
                if not drop:
                    ml_tmp.append(f)
            match_list = ml_tmp

    for f in match_list:
       msg += f+"\n"

    send_response("OK", msg)

def do_query_runs(req):
    run_data_dir = req.config.data_dir + os.sep + "runs"
    msg = ""

    filelist = os.listdir(run_data_dir)
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
        if f.startswith("run-") and f.endswith("json"):
            # last item after dashes, with '.json' removed
            host_and_board = f.split("-")[-1][:-5]
            if not host_and_board:
                continue
            if not item_match(query_host, host_and_board.split(":")[0]):
                continue
            if not item_match(query_board, host_and_board.split(":")[1]):
                continue
            match_list.append(f)

    # FIXTHIS - read files and filter by attributes
    # should particularly filter on 'requestor'

    for f in match_list:
       msg += f+"\n"

    send_response("OK", msg)

def do_query_tests(req):
    test_data_dir = req.config.data_dir + os.sep + "tests"
    test_files_dir = req.config.files_dir + os.sep + "tests"
    msg = ""

    filelist = os.listdir(test_data_dir)
    filelist.sort()

    # can query by different fields, all in the name for now
    try:
        query_name = req.form["name"].value
    except:
        query_name = "*"
    try:
        query_version = req.form["version"].value
    except:
        query_version = "*"

    try:
        query_release = req.form["release"].value
    except:
        query_release = "*"


    # handle queries
    match_list = []
    for f in filelist:
        if f.endswith(".yaml"):
            ftp_filename = f[:-5] + ".ftp"
            # remove '.yaml' and separate into parts
            try:
                name, version, release = f[:-5].split("-")
            except:
                continue
            if not item_match(query_name, name):
                continue
            if not item_match(query_version, version):
                continue
            if not item_match(query_release, release):
                continue
            match_list.append(ftp_filename)

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
    req_data_dir = req.config.data_dir + os.sep + "requests"
    msg = ""

    # handle host and target-based queries
    msg += "In fserver.py:get_request\n"
    try:
        request_id = req.form["request_id"].value
    except:
        msg += "Error: can't read request_id from form"
        send_response("FAIL", msg)

    filepath = req_data_dir + os.sep +request_id
    if not os.path.exists(filepath):
        msg += "Error: filepath %s does not exist" % filepath
        send_response("FAIL", msg)

    # read requested file
    import json
    request_fd = open(filepath, "r")
    mydict = json.load(request_fd)

    # beautify the data, for now
    data = json.dumps(mydict, sort_keys=True, indent=4, separators=(',', ': '))
    send_response("OK", data)

def do_remove_request(req):
    req_data_dir = req.config.data_dir + os.sep + "requests"
    msg = ""

    try:
        request_id = req.form["request_id"].value
    except:
        msg += "Error: can't read request_id from form"
        send_response("FAIL", msg)

    filepath = req_data_dir + os.sep + request_id
    if not os.path.exists(filepath):
        msg += "Error: filepath %s does not exist" % filepath
        send_response("FAIL", msg)

    # FIXTHIS - should check permissions here
    # original-submitter and requested-host only are allowed to remove

    os.remove(filepath)

    msg += "Request file %s was removed" % filepath
    send_response("OK", msg)

def do_remove_run(req):
    run_data_dir = req.config.data_dir + os.sep + "runs"
    run_file_dir = req.config.files_dir + os.sep + "runs"
    msg = ""

    try:
        run_id = req.form["run_id"].value
    except:
        msg += "Error: can't read run_id from form"
        send_response("FAIL", msg)

    datapath = run_data_dir + os.sep + run_id + ".json"
    if not os.path.exists(datapath):
        msg += "Error: filepath %s does not exist" % datapath
        send_response("FAIL", msg)

    # FIXTHIS - should check permissions here
    # original-submitter and requested-host only are allowed to remove
    try:
        os.remove(datapath)
    except:
        send_response("FAIL", "Error: could not remove %s" % datapath)
    msg += "Run file %s was removed\n" % datapath

    filepath = run_file_dir + os.sep + run_id + ".frp"
    if not os.path.exists(filepath):
        msg += "Error: filepath %s does not exist" % filepath
        send_response("FAIL", msg)

    try:
        os.remove(filepath)
    except:
        msg += "Error: could not remove %s" % filepath
        send_response("FAIL", msg)
    msg += "Run file %s was removed\n" % filepath

    send_response("OK", msg)


def file_list_html(req, file_type, subdir, extension):
    if file_type == "files":
        src_dir = req.config.files_dir + os.sep + subdir
    elif file_type == "data":
        src_dir = req.config.data_dir + os.sep + subdir
    elif file_type == "page":
        src_dir = req.config.page_dir
    else:
        raise ValueError("cannot list files for file_type %s" % file_type)

    full_dirlist = os.listdir(src_dir)
    full_dirlist.sort()

    # filter list to only ones with requested extension
    filelist = []
    for d in full_dirlist:
        if d.endswith(extension):
            filelist.append(d)

    if not filelist:
        return req.html_error("No %s files found." % subdir[:-1])

    files_url = "%s/%s/%s/" % (config.files_url_base, file_type, subdir)
    html = "<ul>"
    for item in filelist:
        html += '<li><a href="'+files_url+item+'">' + item + '</a></li>\n'
    html += "</ul>"
    return html

def show_request_table(req):
    src_dir = req.config.data_dir + os.sep + "requests"

    full_dirlist = os.listdir(src_dir)
    full_dirlist.sort()

    # filter list to only request....json files
    filelist = []
    for f in full_dirlist:
        if f.startswith("request") and f.endswith(".json"):
            filelist.append(f)

    if not filelist:
        return req.html_error("No request files found.")

    files_url = config.files_url_base + "/data/requests/"
    html = """<table border="1" cellpadding="2">
  <tr>
    <th>Request</th>
    <th>State</th>
    <th>Requestor</th>
    <th>Host</th>
    <th>Board</th>
    <th>Test</th>
    <th>Run (results)</th>
  </tr>
"""
    import json
    for item in filelist:
        request_fd = open(src_dir+os.sep + item, "r")
        req_dict = json.load(request_fd)
        request_fd.close()

        # add data, in case it's missing
        try:
            run_id = req_dict["run_id"]
        except:
            req_dict["run_id"] = "Not available"

        html += '  <tr>\n'
        html += '    <td><a href="'+files_url+item+'">' + item + '</a></td>\n'
        for attr in ["state", "requestor", "host", "board", "test_name",
                "run_id"]:
            html += '    <td>%s</td>\n' % req_dict[attr]
        html += '  </tr>\n'
    html += "</table>"
    print(html)

def show_run_table(req):
    src_dir = req.config.data_dir + os.sep + "runs"

    full_dirlist = os.listdir(src_dir)
    full_dirlist.sort()

    # filter list to only run....json files
    filelist = []
    for f in full_dirlist:
        if f.startswith("run-") and f.endswith(".json"):
            filelist.append(f)

    if not filelist:
        return req.html_error("No request files found.")

    data_url = config.files_url_base + "/data/runs/"
    files_url = config.files_url_base + "/files/runs/"
    html = """<table border="1" cellpadding="2">
  <tr>
    <th>Run Id</th>
    <th>Test</th>
    <th>Spec</th>
    <th>Host</th>
    <th>Board</th>
    <th>Result</th>
    <th>Run File bundle</th>
  </tr>
"""
    import json
    for item in filelist:
        # run_id is the filename with "run-" and ".json" removed
        run_id = item[4:-5]
        run_fd = open(src_dir+os.sep + item, "r")
        run_dict = json.load(run_fd)
        run_fd.close()

        html += '  <tr>\n'
        html += '    <td>%s</td>\n' % run_id
        html += '    <td>%s</td>\n' % run_dict["name"]
        html += '    <td>%s</td>\n' % run_dict["metadata"]["test_spec"]
        html += '    <td>%s</td>\n' % run_dict["metadata"]["host_name"]
        html += '    <td>%s</td>\n' % run_dict["metadata"]["board"]
        html += '    <td><a href="'+data_url+item+'">' + run_dict["status"] + '</a></td>\n'
        filename = item[:-4]+"frp"
        html += '    <td><a href="'+files_url+filename+'">' + filename + '</a></td>\n'
        html += '  </tr>\n'
    html += "</table>"
    print(html)


def do_show(req):
    req.show_header("Fuego server objects")
    log_this("in do_show, req.page_name='%s'\n" % req.page_name)
    #print("req.page_name='%s' <br><br>" % req.page_name)

    if req.page_name not in ["tests", "requests", "runs"]:
        title = "Error - unknown object type '%s'" % req.page_name

    if req.page_name=="tests":
        # FIXTHIS - convert to pretty-printed list of tests, with link
        # to test.yaml and .ftp file
        print("<H1>List of tests</h1>")
        print(file_list_html(req, "data", "tests", ".yaml"))
        print(file_list_html(req, "files", "tests", ".ftp"))

    if req.page_name=="requests":
        print("<H1>Table of requests</H1>")
        show_request_table(req)

    if req.page_name=="runs":
        # FIXTHIS - convert to pretty-printed list of tests, with link
        # to test.yaml and .ftp file
        print("<H1>Table of runs</h1>")
        show_run_table(req)
        #print(file_list_html(req, "data", "runs", ".json"))
        #print(file_list_html(req, "files", "runs", ".frp"))

    if req.page_name!="main":
        print("<br><hr>")
    print("<H1>Fuego objects on this server</h1>")
    print("""
Here are links to the different Fuego objects:<br>
<ul>
<li><a href="%(url_base)s/tests">Tests</a></li>
<li><a href="%(url_base)s/requests">Requests</a></li>
<li><a href="%(url_base)s/runs">Runs</a></li>
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
    if not page_name:
        page_name = "/main"
    page_name = os.path.basename(page_name)
    req.set_page_name(page_name)

    #req.add_to_message("page_name=%s" % page_name)

    req.action = action

    # NOTE: uncomment this when you get a 500 error
    #req.show_header('TRB Debug')
    #show_env(os.environ)
    log_this("in main request loop: action='%s'<br>" % action)
    #print("in main request loop: action='%s'<br>" % action)

    # perform action
    req.form = cgi.FieldStorage()

    # map action names to "do_<action>" functions
    if action in ["show", "put_test", "put_run", "put_request",
            "query_requests", "query_runs", "query_tests",
            "get_request", "get_run", "get_test",
            "remove_request", "remove_test", "remove_run",
            "update_request"]:
    # FIXTHIS: missing get_run, get_test, remove_test, remove_run do functions
        action_function = globals().get("do_" + action)
        action_function(req)
        # NOTE: computer actions don't return to here, but 'show' does
        return

    req.show_header("TBWiki Error")
    print(req.html_error("Unknown action '%s'" % action))


req = req_class(config)

if __name__=="__main__":
    try:
        main(req)
        req.show_message()
    except SystemExit:
        pass
    except:
        req.show_header("FSERVER Error")
        print """<font color="red">Exception raised by fserver software</font>"""
        # show traceback information here:
        print "<pre>"
        import traceback
        (etype, evalue, etb) = sys.exc_info()
        traceback.print_exception(etype, evalue, etb, None, sys.stdout)
        print "</pre>"

