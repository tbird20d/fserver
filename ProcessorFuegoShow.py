"""
ProcessorFuegoShow - Handle showing Fuego items

To do:

Conf Arguments
item_ref=<filename>.json

item_ref can be [run-|request-]<r_id>.json in implied directory
or <test_id>.yaml in implied directory

or "page_name.yaml", which means a yaml file with the same name as this page.

"""

import os
import sys
import json
import time
import re
import yaml

def help(req):
	req.show_header("ProcessorFuegoShow Help")
	print req.html_from_markup("""The FuegoShow processor is used to
implement some of the server functions of a Fuego central server.

This includes showing certain uploaded files, and handling automatic refresh.
An item_ref argument must be provided, which maps to a correct filename
on the server.  The processor will convert the filename contents into
the output of the block (in html).

Example:
{{{
{ {{#!FuegoShow
item_ref=request-....json
} }}
}}}

""")

def main(req, content):
	conf_map = req.parse_conf(content)
	try:
		item_ref = conf_map["item_ref"]
	except:
		return req.html_error("Missing item_ref in FuegoShow")

	if item_ref.startswith("page_name"):
		item_ref = req.page_name + item_ref[9:]

	# figure out item_type automatically
	item_type = "unknown"
	if item_ref.startswith("request-"):
		item_type = "request"
		file_type = "json"
		item_path = req.config.files_dir + "/requests/" + item_ref
		section_fields = []
		list_fields = []
	elif item_ref.startswith("run-"):
		item_type = "run"
		file_type = "json"
		item_path = req.page_dir + os.sep + item_ref
		section_fields = ["description"]
		list_fields = ["files"]
	elif item_ref.endswith(".yaml"):
		item_type = "test"
		file_type = "yaml"
		item_path = req.page_dir + os.sep + item_ref
		section_fields = ["description"]
		list_fields = ["tags", "data_files"]

	if item_type=="unknown":
		return req.html_error("Cannot determine type of item %s in FuegoShow" % item_ref)


	if file_type=="yaml":
		try:
			yaml_data = open(item_path, "r").read()
		except:
			return req.html_error("Cannot open %s in FuegoShow" % item_path)

		try:
			data = yaml.safe_load(yaml_data)
		except:
			req.add_msg_and_traceback("Cannot load %s as yaml data" % item_path)
			return req.html_error("Error in FuegoShow")

	else:
		# must be a json file
		try:
			fp = open(item_path, "r")
		except:
			return req.html_error("Cannot open %s in FuegoShow" % item_path)

		try:
			data = json.load(fp)
		except:
			req.add_msg_and_traceback("Cannot load %s as json data" % item_path)
			return req.html_error("Error in FuegoShow")

	markup = ""
	field_list = data.keys()
	field_list.sort()
	for field in field_list:
		value = data[field]
		if field in section_fields:
			markup += "== %s ==\n%s\n" % (field, value)
			continue

		if field in list_fields:
			markup += "== %s ==\n" % field
			for v in value:
				markup += "  * %s\n" % v
			markup += "\n"
			continue

		markup += "; %s: %s\n" % (field, value)


	save_flag = req.config.section_edit_links

	req.config.section_edit_links=0
	html = req.html_from_markup(markup)
	req.config.section_edit_links = save_flag

	return html
