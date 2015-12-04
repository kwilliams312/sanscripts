#!/opt/python2.7/bin/python2.7 -u
#
# NetApp/RHEV-M FC-lUN refresh script
# by, ken williams (ken.williams@clearcapital.com)
#
# Used for refreshing the postgres serve servers.
# Command line option is simply the server you wish to refresh.
# - Example: $ pgds_refresh.py -d repo
#
# Requirements:
#  - Python 2.7
#  - NetApp Manageability SDK 4.1 or higher
#  - Red Hat Enterprise Virtualization Management server. 3.0
#
# Notes:
# - Seeing some difficulty shutting down VM, might need to wait X cycles and issue a remote shutdown -h now
# - filer handler should stay in the netapp.py module.
# - more error handling, var checking! 
#########################################################################
import sys # various system stuff
sys.path.append("/linux_scripts/common/")
sys.path.append("/linux_scripts/common/NetApp")

from optparse import OptionParser
import subprocess # for cli command execution
#import argparse # for argument parsing
import ConfigParser # configuration file parser (for the .conf file)
from datetime import datetime, date, timedelta
import time # date/time 
import plog # pretty logging
import netapp # import netapp functions
import rhevm # import redhat enterprise virtualization management tools
import linux # linux toolset
import httpcheck # http check

VERSION = 1.0

plog.DEBUGMODE=True
today = datetime.now().strftime("%Y%m%d")

guestList = [] # this will be populated by the config init area, all guest configs will go here.

# read in the config file
config = ConfigParser.ConfigParser()
config.read('./rhev_lun_refresh.conf')

# get a list of sections, the first items should be Filer and Source.
sections = config.sections()

# initalizes vars from config file
for section in sections:
    if section == "FILER":
      # get filer credentials
        netapp.filerHost = config.get(section, 'host')
        netapp.filerLogin = config.get(section, 'login')
        netapp.filerPass = config.get(section, 'password')

    elif section == "RHEV-M":
      # get rhevm credentials
        rhevm.rm_host = config.get(section, 'host')
        rhevm.rm_user = config.get(section, 'login')
        rhevm.rm_pass = config.get(section, 'password')
        rhevm.rm_port = config.get(section, 'port')

    elif section == "RHEV-H":
        hostlist = config.items(section)

    elif section == "SOURCE":
      # populate source volume set
        sourceHost = config.get(section, 'host')
        sourceVolume = config.get(section, 'volume')
        sourceLun = config.get(section, 'lunname')
        sourceiGroup = config.get(section, 'igroup')
        keepSnapsDays = config.get(section, 'keepsnapsdays')
        sourceSnapPrefix = config.get(section, 'snapprefix')

    else:
      # at this point any entry thats not FILER, RHEV-M, or SOURCE is a guest vm.
        guestList.append(section)

today_snap = "%s%s" %(sourceSnapPrefix, today)

# connect to filer
filer = netapp.connect_filer(netapp.filerHost,netapp.filerLogin,netapp.filerPass)

def create_sourcesnap():
    plog.print_log("Creating source volume snapshot on %s." %(sourceVolume))
        # check for existance (on the filer) of source volume 
    if (netapp.does_vol_exist(filer,sourceVolume) == False):
        plog.print_error("Source volume %s doesnt exist." % (sourceVolume))
    else:
        plog.print_log("Volume: %s exists, continuing." % (sourceVolume))

    # create volume snapshot in ISO date format (pgds_refresh_2012_01_31)
    if (netapp.create_snap(filer, sourceVolume, today_snap) == False):
       plog.print_error("Unable to continue, snapshot failed.")

def refresh_flexclone(destination):
    plog.print_log("Starting flexclone refresh process for %s" %(destination))
    
    if not (destination in guestList):
        plog.print_error("Guest %s not found, please check config." %(destination))

    for guest in guestList: 
        # if this is the guest specified in the command line parameter, then do your work!
        if (destination == guest):
            thisguest = config.get(guest, 'vm_name')
            thislunid = config.get(guest, 'lunid')
            thisvolume = "%s_%s" %(sourceVolume, thisguest)
            thislun = sourceLun
            thislunpath = "/vol/%s/%s" %(thisvolume, thislun)

            plog.print_log("%s %s" %(thisguest, thislunid))
          
          # shutdown the guest

            if not (rhevm.is_guest_down(thisguest)):
                linux.shutdown(thisguest)
            i = 0
            while (rhevm.is_guest_down(thisguest) == False):
                if (i < 30):
                    time.sleep(15)
                    plog.print_log("Waiting 15s for %s to shutdown." %(thisguest))
                    i += 1
                else:
                    plog.print_error("Unable to shutdown %s." %(thisguest))
                    exit(1)


            plog.print_log("%s is now down." %(thisguest))          
            #plog.print_log("Clearing %s directlun property." %(thisguest))
            #rhevm.guest_set_directlun(thisguest, "donothinghere", "68719476736")

            for thishost in hostlist:
                 plog.print_log("removing lun: %s from %s on %s." %(thislunid, thisguest, thishost[1]))         
                 linux.remove_multipath_devices(thishost[1], thislunid)

            # clean the old flexclone and lUN, remove the flexclone volume.
            netapp.destroy_vol(filer,thisvolume)
            time.sleep(10)

            # create a new flexclone based on today's snapshot
            if not (netapp.create_flexclone(filer, sourceVolume, thisvolume, today_snap)):
                plog.print_error("Unable to continue. Flexclone create failed.")
                sys.exit(1)

            time.sleep(10)

            # online the new lun
            netapp.online_lun(filer, thislunpath)

            time.sleep(10)
            
            netapp.map_lun(filer, sourceiGroup, thislunpath, thislunid)
            time.sleep(10)

            #for each host rescan scsi bus, run multipath
            #then get the device id and map it to the guest
            for thishost in hostlist:
                 plog.print_log("Scanning for new luns.")

                 #scan the scsi bus for new devices
                 linux.rescan_scsi(thishost[1])
                 time.sleep(10)

                 #add new devices to multipath
                 linux.add_multipath_devices(thishost[1])
                 time.sleep(10)

                 # I do this on each host scan, realistically it should be identical on all hosts.
                 thisdeviceid = linux.get_device_id_from_lun(thishost[1], thislunid)
                 time.sleep(10)

             #    attach new directlun with deviceid to guest
            rhevm.guest_set_directlun(thisguest, thisdeviceid, "68719476736")
            time.sleep(10)

             #    power on guest
            rhevm.guest_start(thisguest)
            i = 0
            while not (httpcheck.get_status_code("%s:8888" %(thisguest))):
                if (i < 10):
                    time.sleep(15)
                    plog.print_log("Waiting 15s for %s for startup." %(thisguest))
                    i += 1
                else:
                    plog.print_error("Unable to startup %s." %(thisguest))
                    exit(1)
            plog.print_log("Refresh complete.")

def create_rollsnaps():
    plog.print_log("removing snapshots older than %s days" %(keepSnapsDays))
    for item in netapp.get_volume_snap_list(filer, sourceVolume):
        if (sourceSnapPrefix in item):
            snapdate = datetime.strptime(item.rsplit("_")[1], "%Y%m%d")
            now = datetime.now()
            maxdelta = timedelta(days=int(keepSnapsDays))
            thisdelta = now - snapdate
            if (thisdelta > maxdelta):
                plog.print_log("Deleting snap %s" %(item))
                netapp.remove_snap(filer, sourceVolume, item)
            else:
                plog.print_log("Leaving snap %s" %(item))

def main():
  
    ##################################################################
    # command line parsing
    ##################################################################
    parser = OptionParser()
    
    parser.add_option("-s", dest="createsnap", action="store_true",default=False,help="Create snapshot from source volume")
    parser.add_option("-r", dest="rollsnaps", action="store_true", default=False, help="Roll-off old snapshots on source volume")
    parser.add_option("-f", dest="flexclone", metavar="guest", help="Refresh flexclone from source snapshot. GUEST is the RHEV-M guest that will be refreshed.")
    (options, args) = parser.parse_args()


    if options.createsnap:
        create_sourcesnap()
        exit(0)

    elif options.rollsnaps:
        create_rollsnaps()

    elif options.flexclone:
        refresh_flexclone(options.flexclone)
        exit(0)

    else:
        plog.print_error("No options.")
        exit(1)
    
    
if __name__ == '__main__':
    main()
