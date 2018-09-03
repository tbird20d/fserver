"""
MacroFuegoRunList - show a list of test runs
"""
import os

def main(req, args=""):
        full_dirlist = os.listdir(req.config.files_dir+os.sep+"runs")
	full_dirlist.sort()

	# each run is it's own directory
	dirlist = full_dirlist

	# FIXTHIS - look for test run json file

	if not dirlist:
		return req.html_error("No runs found.")

	runs_url = req.config.files_url_base + os.sep + "runs/"
	html = "<ul>"
        for item in dirlist:
                html += '<li><a href="'+runs_url+item+'">' + item + '</a></li>\n'
	html += "</ul>"

	return html

