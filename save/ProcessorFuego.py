"""
ProcessorFuego - Handle actions for the fuego server

To do:
 - add ability for query_requests to process attributes inside the file
 instead of just in the filename, and handle wildcards
 - for put_<item> - creat a tbwiki page as a cover for the data (json or yaml) pages
   - with {{{#!FuegoShow\nitem_ref=page_name.[yaml|json]\n}}}

"""

import os
import sys
import json
import time
import re

def help(req):
	req.show_header("ProcessorFuego Help")
	print req.html_from_markup("""The Fuego processor is used to implement
the server functions of a Fuego central server.

This includes handling things like file uploads and downloads, and data queries.

By default, this module just shows a list of things that can be done manually.
""")

def get_timestamp():
    t = time.time()
    tfrac = int((t - int(t))*100)
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S.")+str(tfrac)
    return timestamp

# maybe I can use the tbwiki_engine function save_uploaded_file,
# but use our own routine for now
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

def put_test(req):
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

--------
{{{#!FuegoShow
item_ref=page_name.yaml
}}}
--------

Go to [[Tests]] page.
"""
	req.write_page(page_content, test_name)
	msg += "Created %s page\n" % test_name

	send_response("OK", msg)

def put_run(req):
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


def put_request(req):
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
        target = mydict["target"]
    except:
        result = "FAIL"
        msg += "Error: missing target in form data"

    filename = "request-%s-%s:%s" % (timestamp, host, target)
    jfilepath = upload_dir + filename + ".json"

    msg += "Filename '%s' calculated!\n" % jfilepath

    # convert to json and save to file here
    data = json.dumps(mydict, sort_keys=True, indent=4, separators=(',', ': '))
    fout = open(jfilepath, "w")
    fout.write(data+'\n')
    fout.close()

    tbfilepath = req.page_dir + os.sep + filename

    # convert to tbwikidb and save to file here
    keylist = mydict.keys()

    # FIXTHIS - could write only known fields here, to prevent abuse
    # remove the 'action' key
    keylist.remove("action")

    keylist.sort()
    fout = open(tbfilepath, "w")

    # FIXTHIS - this doesn't handle multi-line fields.  They should be put
    # into a section
    for k in keylist:
        fout.write("; %s: %s\n" % (k, mydict[k]))
    fout.close()

    msg += "data=%s\n" % data
    msg += "tbfilepath=%s\n" % tbfilepath

    send_response(result, msg)

# try matching with simple wildcards (* at start or end of string)
def req_match(pattern, item):
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

def query_requests(req):
    download_dir = req.config.files_dir + os.sep + "requests/"
    # some debugging...
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
        query_target = req.form["target"].value
    except:
        query_target = "*"

    # handle host and target-based queries
    match_list = []
    for f in filelist:
        if f.startswith("request-") and f.endswith("json"):
            full_target = f[31:-5]
            if not full_target:
                continue
            if not req_match(query_host, full_target.split(":")[0]):
                continue
            if not req_match(query_target, full_target.split(":")[1]):
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
def get_request(req):
    msg = ""

    # handle host and target-based queries
    msg += "In ProcessorFuego.py:get_request\n"
    try:
        request_id = req.form["request_id"].value
    except:
        msg += "Error: can't read request_id from form"
        send_response("FAIL", msg)

    # strip '.json' from filename (we're in flux on this)
    if request_id.endswith(".json"):
	request_id = request_id[:-5]

    filepath = req.page_dir + os.sep + request_id
    if not os.path.exists(filepath):
        msg += "Error: filepath %s does not exist" % filepath
        send_response("FAIL", msg)

    # read requested page, as a tbwikidb
    mydict = read_tbwikidb_file(filepath)

    # turn into json
    # I don't need pretty json, but beautify it for now
    data = json.dumps(mydict, sort_keys=True, indent=4, separators=(',', ': '))
    send_response("OK", data)

def main(req, content):
	return """<table bgcolor="c0c0c0"><tr><td>
<font color="004000">This is from ProcessorFuego:main()<BR>
If you see this, it means there were no syntax errors in the processor!</font>
</td></tr></table>"""

