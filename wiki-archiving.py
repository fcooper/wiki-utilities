# -*- coding: utf-8 -*-
# encoding=utf-8

# Initialize Site object
import configparser
import mwclient
import os
import re
import logger
import sys
import requests
import urllib
import os.path
import collections
from sys import stdin
import getpass
config = configparser.ConfigParser()

WikiLink = collections.namedtuple('WikiLink', 'url altname anchor latestrevid wikisyntax')

WIKI_DOMAINNAME = "processors.wiki.ti.com"
WIKI_URL = "http://"+WIKI_DOMAINNAME+"/index.php/"
#ARCHIVE_SDK_NAME = "Sitara Linux SDK 08.00.00.00"
#TEMPLATE_WIKI_PAGE = "Template:ArchiveLinks-AMSDKv08.00"

os.environ['no_proxy'] = '*.ti.com'

# Add Proxy. Fill out below line and uncomment
# os.environ['http_proxy'] =

site = mwclient.Site(('http',WIKI_DOMAINNAME),path='/')


if not os.path.exists("modified.txt"):
    open("modified.txt","w").close()

try:
    os.makedirs("images")
except OSError:
    if not os.path.isdir("images"):
        raise


print ("Enter Archive Config File Name:"),
configfile = stdin.readline().strip()


if not os.path.exists(configfile):
    print "Config file "+configfile+" does not exist."
    exit(1)
else:
    config.read(configfile)

try:

    ARCHIVE_SDK_NAME = config["DEFAULT"]["SDKFullName"] + " "+config["DEFAULT"]["SDKVersion"]
    ARCHIVE_SDK_NAME = ARCHIVE_SDK_NAME.strip()
    TEMPLATE_WIKI_PAGE = "Template:ArchiveLinks-"+config["DEFAULT"]["AbbreviatedSDKName"]+"v"+config["DEFAULT"]["SDKVersion"]
    TEMPLATE_WIKI_PAGE = TEMPLATE_WIKI_PAGE.strip()
except KeyError:
    print "Got a key error"
    exit(1)

print "Archived SDK Name: "+ARCHIVE_SDK_NAME
print "Template Wiki Page: "+TEMPLATE_WIKI_PAGE

def normalize_title(title):
	# TODO: Make site dependent
	title = title.strip()
	if title[0] == ':':
		title = title[1:]
	title = title[0].upper() + title[1:]
	title = title.replace(' ', '_')
	return title

def getLinks(pageText):

	links = []

	p = re.compile(ur'\[\[.*?\]\]')

	for output in re.findall(p,pageText):
		if "[[Image:" in output:
			continue
		if "[[Category:" in output:
			continue
		if "[[:Category:" in output:
			continue
		if "[[File:" in output:
			continue
		if "[[#" in output:
			continue

		originalsyntax = output


		output = output[2:]
		output = output[:-2]

		split = output.find("|")

		linkurl = None
		altname = None
		anchor = None

		if split is not -1:
			linkurl = output.split('|',1)[0]
			altname = output.split('|',1)[1]
		else:
			linkurl = output


		if linkurl.find("#") is not -1:
			anchor = linkurl.split("#",1)[1]
			linkurl = linkurl.split("#",1)[0]

		page2 = site.Pages[normalize_title(linkurl)]
		last_rev = -1
		for rev in page2.revisions():
			last_rev = rev['revid']
			break

		if last_rev == -1:
			raise ValueError("Rev ID shouldn't be -1", linkurl)

		links.append(WikiLink(url=linkurl,altname=altname,anchor=anchor,latestrevid=last_rev,wikisyntax=originalsyntax))

	return links


def addLinkToTemplate(url,revid,templateText):

	newTemplateURL = "{{#ifeq: {{{linkurl}}} |"+url+"|["+WIKI_URL+"?title="+url+"&oldid="+str(revid)+"{{{anchor}}} {{{altname}}}]|}}"

	verification = newTemplateURL.split("&oldid=")[0]+"&oldid="
	if verification not in templateText:
		templateText = templateText + newTemplateURL
	#else:
	#	print "String "+url+" already in template"

	return templateText

def updateLinkToTemplate(url,revid,templateText):

	newTemplateURL = "{{#ifeq: {{{linkurl}}} |"+url+"|["+WIKI_URL+"?title="+url+"&oldid="+str(revid)+"{{{anchor}}} {{{altname}}}]|}}"

	first = templateText.find("{{#ifeq: {{{linkurl}}} |"+url+"|["+WIKI_URL+"?title="+url+"&oldid")
	first = first + len("{{#ifeq: {{{linkurl}}} |"+url+"|["+WIKI_URL+"?title="+url+"&oldid") + 1

	second = templateText[first:].find("{{{anchor}}}") + first

	oldrev = templateText[first:second]

	oldURL = "{{#ifeq: {{{linkurl}}} |"+url+"|["+WIKI_URL+"?title="+url+"&oldid="+str(oldrev)+"{{{anchor}}} {{{altname}}}]|}}"


	print "Update"

	return templateText.replace(oldURL,newTemplateURL)


def convertLinksToTemplateLinks(pageText,templateText,templateName):

	try:
		links = getLinks(pageText)
	except ValueError as err:
		print "Broken link on page "+ARCHIVE_WIKI_PAGE
		print(err.args)
		return

	# neeed to ignore File:
	for link in links:

		altname = link.altname
		url = link.url
		anchor = link.anchor
		latestrevid = link.latestrevid

		if "File:" in url:
			print "Ignoring "+url+" since it isn't a link"
			continue

		if altname is None:
			if anchor is not None:
				altname = url+"#"+anchor
			else:
				altname = url


		pageurl = WIKI_URL+normalize_title(url)+"&oldid="+str(latestrevid)

		templateText = addLinkToTemplate(normalize_title(url),latestrevid,templateText)

		if anchor is None:
			anchor = ""
		else:
			anchor = "#"+anchor

		templateWikiName = templateName.replace("Template:","")
		newlink = "{{"+templateWikiName+"|linkurl="+normalize_title(url)+"|anchor="+anchor+"|altname="+altname+"}}"
		pageText = pageText.replace(link.wikisyntax,newlink)

	return (pageText, templateText)

def addArchivedPageWarning(pageText,pageTitle):

	url = "http://processors.wiki.ti.com/index.php/"+normalize_title(pageTitle)
	archivedMessage = "<blockquote>{{SpCaution|This is the archived page for " + ARCHIVE_SDK_NAME + " if you like to go to the latest version of the page click ["+url+" here]}} </blockquote>"

	return archivedMessage+" \n"+pageText


def addArchiveLink(pageTitle,pageText,templateName):
	last_rev = site.Pages[pageTitle].revisions

	templateWikiName = templateName.replace("Template:","")
	savedURL = "*{{"+templateWikiName+"|linkurl="+normalize_title(pageTitle)+"|anchor=''|altname=<u>'''"+ARCHIVE_SDK_NAME+"'''</u>}}"

	p = re.compile('=+\040*(?:Archived)+\040*(?:Versions)*\040*=+\n*\r*\040*', re.IGNORECASE)


	for m in p.finditer(pageText):

		begin , end = m.span()

		return (True,pageText[:end]+savedURL+"\n"+pageText[(end):])


	return (False,savedURL)

def switchImagesToArchiveImages(page,pageText):
	global site

	switchText = pageText

	p = re.compile('\[\[\040*(?:File|Image)?\040*:.*?\]\]')

	imageStr = []

	archive_prefix = "_"+"archive_"+ARCHIVE_SDK_NAME.replace(" ","_")

	for output in re.findall(p,pageText):
		#print output
		imageStr.append(output)

	for image in page.images():

		if "File:" in image.name:
			name = image.name[5:]
		else:
			name = image.name[6:]

		normalized_name = normalize_title(name)
		basename = name.rsplit(".",1)[0]
		ext = name.rsplit(".",1)[1]

		if ext == "zip" or ext == "tar" or ext == "gz" or ext == "pdf":
			continue

		imageinfo = image.imageinfo


		if archive_prefix in basename:
			print "Already archived image"
			continue

		saveimage = basename+archive_prefix+"."+ext




		#print saveimage

		if site.Images[saveimage].imageinfo.get('size',None) is None:


			imagedir = "/home/franklin/repositories/git/wiki-utilities/images/"
			if os.path.isfile(saveimage) is False:

				urllib.urlretrieve (imageinfo['url'], imagedir+saveimage)

			description = ARCHIVE_SDK_NAME+" archived image"
			site.upload(open(imagedir+saveimage,'rb'), filename=saveimage,description=description,ignore=True)

			if site.Images[saveimage].imageinfo.get('size',None) is not None:
				print "Upload successful"
			else:
				print "Upload failed"
		#else:
		#	print "Already uploaded"

		matches = filter(lambda x: name in x, imageStr);
		matches = matches + filter(lambda x: (name[0].lower() + name[1:]) in x, imageStr);
		matches = matches + filter(lambda x: normalized_name in x, imageStr);
		matches = matches + filter(lambda x: (normalized_name[0].lower() + normalized_name[1:]) in x, imageStr);

		for match in matches:
			if name in match:
				newStr = match.replace(name,saveimage,1)
			elif normalized_name in match:
				newStr = match.replace(normalized_name,saveimage,1)
			elif (name[0].lower() + name[1:]) in match:
				newStr = match.replace((name[0].lower() + name[1:]),saveimage,1)
			elif (normalized_name[0].lower() + normalized_name[1:]) in match:
				newStr = match.replace((normalized_name[0].lower() + normalized_name[1:]),saveimage,1)
			switchText = switchText.replace(match,newStr)


	p = re.compile('\[\[\040*(?:File|Image)?\040*:.*?\]\]')

	imageStr = []

	for output in re.findall(p,switchText):
		if archive_prefix not in output:
			print "Error image "+output+" has not switched to archive image"

	return switchText



while True is True:
	try:
		print ("Enter Wiki Username: "),
		username = stdin.readline().strip()
		password = getpass.getpass(prompt='Wiki Password: ')
		site.login(username, password)

		TEST_WIKI_PAGE = "ScratchPad-"+username
		break
	except mwclient.errors.LoginError as e:
		if e[1]['result'] == "WrongPass":
			print "Incorrect password"
		elif e[1]['result'] == "NotExists":
			print "Username does not exist"

while True is True:
	print ("Enter URL: "),
	url = stdin.readline().strip()

	url = url.replace("http://processors.wiki.ti.com/index.php/","")
	url = url.replace("processors.wiki.ti.com/index.php/","")
	url = url.replace("\n", "")

	if url.find("#") is not -1:
		url = url.split("#",1)[0]


	f = open('modified.txt', 'rw+')


	lines = f.read().splitlines()

	if url in lines:
		print "Already in list"
		continue


	ARCHIVE_WIKI_PAGE = url


	print url

	archivepage = site.Pages[ARCHIVE_WIKI_PAGE]
	testpage = site.Pages[TEST_WIKI_PAGE]
	templatepage = site.Pages[TEMPLATE_WIKI_PAGE]

	archivedtext = archivepage.text()
	originaltext = archivepage.text()
	templatetext = templatepage.text().strip()


	print archivepage.revision
	if archivepage.revision < 1:
		print "Invalid"
		continue


	# Convert Images to use new Uploaded Archived Images #
	archivedtext = switchImagesToArchiveImages(archivepage,archivedtext)


	# Convert Internal Links to use Template Links #
	archivedtext , templatetext = convertLinksToTemplateLinks(archivedtext,templatetext,TEMPLATE_WIKI_PAGE)


	# Add Archive Link to Template #
	templatetext = addLinkToTemplate(normalize_title(ARCHIVE_WIKI_PAGE),-1,templatetext)


	archivedtext = addArchivedPageWarning(archivedtext,ARCHIVE_WIKI_PAGE)

	testpage.save(archivedtext, summary = 'Archived for '+ARCHIVE_SDK_NAME)
	templatepage.save(templatetext, summary = 'Preparing to archive. Generate direct links')


	print "Pausing to allow page modifications for archived page version.\nGo to "+WIKI_URL+TEST_WIKI_PAGE+" to view"

	print ("Type continue or stop when ready: "),

	shouldContinue = False
	while True is True:
		command = stdin.readline().strip()

		if command == "continue" or command == "stop":
			if command == "continue":
				shouldContinue = True

			break

		print "Invalid command"


	if shouldContinue is False:
		print "Not making permanent changes"
		continue


	archivedtext =  testpage.text()

	result , value = addArchiveLink(ARCHIVE_WIKI_PAGE,originaltext,TEMPLATE_WIKI_PAGE)

	if result is False:
		print "Could not find archive links. Please manually add archive links:\n" + value
	else:
		originaltext = value

	testpage.save(originaltext, summary = 'Restoring page with original content plus archive link')


	print "Pausing to allow page modifications for original page version.\nGo to "+WIKI_URL+TEST_WIKI_PAGE+" to view"
	print ("Type continue or stop when ready: "),

	shouldContinue = False
	while True is True:
		command = stdin.readline().strip()

		if command == "continue" or command == "stop":
			if command == "continue":
				shouldContinue = True

			break

		print "Invalid command"


	if shouldContinue is False:
		print "Not making permanent changes"
		continue

	originaltext = testpage.text()

	archivepage.save(archivedtext, summary = 'Archiving Page')


	# Need to call again to get latest values including revision id
	archivepage = site.Pages[ARCHIVE_WIKI_PAGE]


	templatetext = updateLinkToTemplate(normalize_title(ARCHIVE_WIKI_PAGE),archivepage.revision,templatetext)

	templatepage.save(templatetext, summary = 'Preparing to archive. Generate direct links')
	archivepage.save(originaltext, summary = 'Restoring page with original content plus archive link')

	f.flush()
	f.close()
