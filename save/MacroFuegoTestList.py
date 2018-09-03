"""
MacroFuegoTestList - show a list of tests
"""
import os

def main(req, args=""):
        full_dirlist = os.listdir(req.config.files_dir+os.sep+"tests")
	full_dirlist.sort()

	# filter list to only .ftp files
	filelist = []
	for d in full_dirlist:
		if d.endswith(".ftp"):
			filelist.append(d)
	
	if not filelist:
		return req.html_error("No tests found.")

	files_url = req.config.files_url_base + os.sep + "tests/"
	html = "<ul>"
        for item in filelist:
                html += '<li><a href="'+files_url+item+'">' + item + '</a></li>\n'
	html += "</ul>"

	return html

