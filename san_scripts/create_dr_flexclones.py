#!/usr/bin/python26
#
# for python2.6/2.7 
#
# This script simply clones from set location if they don't exist.
# After the clone process the script will make the file shares avail via CIFS
# The CIFS shares should be locked down to $lock_user
#############################################################################

#imports!
import commands
import datetime
import sys


#setup some inital vars

filerHost="SANITIZED"  # hostname or IP of the filer
rsh="/usr/bin/rsh"  # path to rsh application on the system
cifsaccess="SANITIZED" # user to lock the cifs shares down to
flex_prefix="flex_" # prefix for the flexclones

# will print command, not execute them
DEBUGMODE=True

# Add the volumes that will get flexcloned here.
# format: 'volumename': ['sharename', 'share path'],
# Do not use the same volume more than once

volume_config = {
        'files1': ['file1', 'SANITIZED'],
        'files2': ['file2', 'SANITIZED'],
        'files3': ['file3', 'SANITIZED'],
        'files4': ['file4', 'SANITIZED'],
        'files5': ['file5', 'SANITIZED'],
}

############################################## DO NOT EDIT BELOW HERE ##########################################

# just the volume names
volumes = list(volume_config.keys())

# set the datestamp
currdate=datetime.date
snapname=flex_prefix + "currdate"

# for ease of code
filerConnectString = rsh + ' ' + filerHost
filerVolStatus = filerConnectString + ' vol status '
filerSnapList = filerConnectString + ' snap list '
snaplistParse = "|tail -n1 |awk '{print $10}' "

#############################################
# This function ensures we are the root user
#############################################
def usingRoot():
	result = commands.getstatusoutput("whoami")
	if result[1] != "root":
		printError("this script needs to be run as root")
		sys.exit(1)

#############################################
# Simple error processing 
#############################################

def printError(errorText):
	print " * Error: " + errorText

#############################################
# Simple warning processing
#############################################

def printWarn(warnText):
	print " * Warning: " + warnText

#############################################
# Simple DEBUG processing
#############################################

def printDebug(debugText):
	print " * DEBUG: " + debugText

#############################################
# Checks to see if the volume exists
# returns true or false, will kill script
# if unable to connect to filer, script will exit
#############################################

def checkResult(result):
	if result [0] == 0:
       		return True
        else:
        	printError("Unable to connect to the filer: " + filerHost + result[1])
               	sys.exit(1)

def doesVolumeExist(volume):
	flexName = flex_prefix + volume
	result = commands.getstatusoutput(filerVolStatus + flexName)
	if result [0] == 0:
		str = 'vol status: No volume named \'' + flexName + '\' exists.'
		if result[1] == str:
			return False
		else:
			printWarn("Flexclone " + flexName + " already exists!")
			return True
	else:
		printError("Unable to connect to the filer: " + filerHost + result[1])
		sys.exit(1)

#############################################
# checks to see if a snapshot exists for the volume
# returns true + the snapname or false.
# exits the script if unable to connect to filer
#############################################

def doesSnapExist(volume):
	result = commands.getstatusoutput(filerConnectString + " snap list " + volume + "|tail -n1 |awk '{print $10}' ")
	if result[0] == 0:
		if result[1] != "":
			return True, result[1]
		else:
			return False, result[0]
	else:
                printError("Unable to connect to the filer: " + filerHost + result[1])
                sys.exit(1)

#############################################
# create the flexclone from volume and snapname
#############################################

def createFlexClone(volume, snapName):
        flexName = flex_prefix + volume
	print "Creating Flexclone: " + flexName + " on volume: " + volume + " using snapshot: " +snapName

	if DEBUGMODE == True:
		printDebug("Command: " + filerConnectString + " vol clone create " + flexName + " -s none -b " + volume + " " + "'" + snapName + "'")
	else:	
		checkResult(commands.getstatusoutput(filerConnectString + " vol clone create " + flexName + " -s none -b " + volume + " " + "'" + snapName + "'"))

#############################################
# this is the main loop for creating flex clones
#############################################

def flexCreation(volumes):
	for volume in volumes:
		thisFlexName = flex_prefix + volume
      	  	if doesVolumeExist(volume) == False:
      	        	print "Volume "+thisFlexName+" not found! Starting flex process."
      	        	result = doesSnapExist(volume)
		        if result[0] == True:	
				createFlexClone(volume, result[1])
			else:
	                        printWarn("Unable to create flexclone, no snapshots exist for volume: " + volume)

def doesShareExist(sharename):
        result = commands.getstatusoutput(filerConnectString + " cifs shares " + sharename)
        if result[0] == 0:
                if result[1] != "No share is matching that name.":
                        return False # the share doesnt exist
                else:
                        return True # The share does exist
        else:
                printError("Unable to connect to the filer: " + filerHost + result[1])
                sys.exit(1)


#############################################
# share creation function
#############################################
def createShare(sharename, sharepath):
	cifscreatecmd = "cifs shares -add " + sharename + " " + sharepath
	cifsnoaccesscmd = "cifs access " + sharename + " Everyone " + "\"No Access\""
        cifsaccesscmd = "cifs access " + sharename + " " + cifsaccess + " " + "\"Full Control\""
	cifsaccesscmd2 = "cifs access " + sharename + " CORP\\Domain Admins" + "\"Full Control\""
	
	print "Creating Share: " + sharename + ". At: " + sharepath
        if DEBUGMODE == True:
		printDebug("Command: " + filerConnectString + " " + cifscreatecmd)
		printDebug("Command: " + filerConnectString + " " + cifsnoaccesscmd)
		printDebug("Command: " + filerConnectString + " " + cifsaccesscmd)
	else:
	        checkResult(commands.getstatusoutput(filerConnectString + " " + cifscreatecmd))
                checkResult(commands.getstatusoutput(filerConnectString + " " + cifsnoaccesscmd))
                checkResult(commands.getstatusoutput(filerConnectString + " " + cifsaccesscmd))
	

	
def cifsCreation(volumes):
	for volume in volumes:
		sharename = volume_config[volume][0]
		sharepath = volume_config[volume][1]
		if doesShareExist(sharepath):
                        printWarn("Share "+ sharename +" already exists")
		else:
	        	createShare(sharename, sharepath)


#############################################
# This is the main loop of the script
#############################################

usingRoot()
print "Creating FlexClones"
flexCreation(volumes)
print "Creating Shares"
cifsCreation(volumes)
