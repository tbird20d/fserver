"""
MacroFuegoRequestList - show a list of tests
"""
import os

def main(req, args=""):
        full_dirlist = os.listdir(req.config.files_dir+os.sep+"requests")
	full_dirlist.sort()

	# filter crud out of the dirlist
	dirlist = []
	for d in full_dirlist:
		if d.endswith(".json"):
			dirlist.append(d)
	
	if not dirlist:
		return "No requests found."

	html = ""
	# show the items
        for item in dirlist:
                html += '<a href="'+req.make_url(item)+'">' + item + '</a><br>\n'
	return html

