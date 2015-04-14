# Initialize Site object
import mwclient
import os
import logger
print os.environ['no_proxy']

site = mwclient.Site(('http','processors.wiki.ti.com'),path='/')


site.login("fcooper", "presario1")


page = site.Pages['Sitara_Linux_SDK_CCS_Users_Guide']

thepage =  page.text()

originalpage = page.text()



original = thepage.find("==")

for dog in page.links():
	#print dog.normalize_title(dog.name)
	last_rev = -1
	for rev in dog.revisions():
		last_rev = rev['revid']
		break
	#print last_rev
	
	used_named = dog.name
	first = thepage.find("[["+used_named,original)

	if first is -1:
		used_named = dog.normalize_title(dog.name)
		first = thepage.find("[["+used_named,original)

	if first is not -1:
		second = thepage.find("]]",first)
		print used_named
		print second  - (first + len("[["+used_named)) 
		addmore = ""
		if  (second - (first + len("[["+used_named))  ) < 10:
			addmore = "|<u>'''"+used_named+"'''</u>"
			#print "Doggyyyyyyyyyyyy"
		
		thepage = thepage.replace("[["+used_named,"[http://processors.wiki.ti.com/index.php?title="+dog.normalize_title(dog.name)+"&oldid="+str(last_rev)+addmore,first)
		num = thepage.find("]]",first)
		thepage = thepage[:num] + thepage[num+1:]
		
	#print first


last_rev = -1
for rev in page.revisions():
	last_rev = rev['revid']
	break

page.save(thepage, summary = 'Preparing to archive. Generate direct links')


page = site.Pages['Sitara_Linux_SDK_CCS_Users_Guide']
last_rev = -1
for rev in page.revisions():
	last_rev = rev['revid']
	break



archived = originalpage.find("= Archived versions  =")
archived = archived + len("= Archived versions  =")+1

sdk = "Sitara SDK 8.0"
archivedlink = "*[http://processors.wiki.ti.com/index.php?title="+page.normalize_title(page.name)+"&oldid="+str(last_rev)+" <u>'''"+sdk + " -  "+ page.name+" (archived)'''</u>]"

originalpage =  originalpage[:archived] + archivedlink + originalpage[archived:]



page.save(originalpage, summary = 'Created Archived Links and restoring page')	

	
#print thepage

#[[Sitara Linux SDK CCS GDB Setup|<u>'''Running GDB Server on CCSv5'''</u>]]

#[http://processors.wiki.ti.com/index.php?title=Sitara Linux SDK CCS GDB Setup&oldid=137210 <u>'''Sitara SDK 05.07 CCSv5 User Guide (archived)'''</u>]
