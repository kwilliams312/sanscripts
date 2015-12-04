#!/opt/python2.7/bin/python2.7
#
# common netapp functions
#####################################

import sys
# NetApp SDK
sys.path.append("/linux_scripts/common/NetApp")
from NaServer import *
from datetime import datetime, date, time # date/time 

import plog

global filerHost
global filerLogin
global filerPass
global filer

# connects to filer returns a filer object
def connect_filer(host,user,passwd):
   plog.print_debug("Host: %s, User: %s" %(host,user))
   s = NaServer(host, 1, 1)
   s.set_server_type("Filer")
   s.set_admin_user(user,passwd)
   response = s.set_transport_type('HTTP')

   if(response and response.results_errno() != 0 ):
      r = response.results_reason()
      plog.print_error("Unable to set HTTP transport " + r + "\n")
      sys.exit (1)

   response = s.set_style('LOGIN')
   if(response and response.results_errno() != 0 ):
      r = response.results_reason()
      plog.print_error("Unable to set authentication style " + r + "\n")
      sys.exit (1)

   return s

# checks for volume existance
def does_vol_exist(filer, volname):
   out = filer.invoke("volume-list-info", "volume", volname)

   if out.results_status() == "failed":
      plog.print_debug(out.results_reason())
      return False
   else:
      return True

# removes a snapshot on a volume
def remove_snap(filer, volname, snapshot):
   plog.print_log("%s: removing snapshot: %s" % (volname, snapshot))
   output = filer.invoke("snapshot-delete", "snapshot", snapshot, "volume", volname)

   if (output.results_errno() != 0):
      r = output.results_reason()
      plog.print_error("Delete of snapshot failed: %s" %(r) )
      return False
   else:
      plog.print_log("Snapshot %s removed from Volume: %s." %(snapshot,volname))
      return True

# creates a snapshot on a volume
def create_snap(filer, volname, snapshot):
   plog.print_log("%s: creating snapshot: %s" % (volname, snapshot))
   output = filer.invoke("snapshot-create", "snapshot", snapshot, "volume", volname)

   if (output.results_errno() != 0):
      r = output.results_reason()
      plog.print_error("Creation of snapshot failed: %s" %(r) )
      return False
   else:
      plog.print_log("Snapshot %s created on Volume: %s." %(snapshot,volname))
      return True

def destroy_vol(filer, volname):
   if (does_vol_exist(filer,volname) == True):

       plog.print_log("Offline %s" %(volname))
       output = filer.invoke("volume-offline", "name", volname)
       if (output.results_errno() != 0):
           r = output.results_reason()
           plog.print_error("Volume-Offline operation failed: %s" %(r) )
       else:
           plog.print_log("Volume Offline: %s." %(volname))
       
       plog.print_log("Destroy %s" %(volname))
       output = filer.invoke("volume-destroy", "name", volname)
       if (output.results_errno() != 0):
           r = output.results_reason()
           plog.print_error("Volume Destroy failed: %s" %(r) )
           return False
       else:
           plog.print_log("Volume Destroy: %s." %(volname))
           return True
   else:
       plog.print_warn("Volume: %s doesn't exist." %(volname))


def create_flexclone(filer, sourceVolume, destVolume, snapshot):
    plog.print_log("Creating Flexclone Vol: %s from source vol: %s. Using Snapshot: %s" % (destVolume, sourceVolume, snapshot))

    output = filer.invoke("volume-clone-create", "parent-snapshot", snapshot, "parent-volume", sourceVolume, "volume", destVolume, "space-reserve", "none") 
    if (output.results_errno() != 0):
        r = output.results_reason()
        plog.print_error("Creation of flexclone failed: %s" %(r) )
        return False
    else:
        plog.print_log("Flexclone %s created from Volume: %s." %(destVolume,sourceVolume))
        return True

def map_lun(filer, igroup, path, lunid):
    output = filer.invoke("lun-map", "initiator-group", igroup, "path", path, "lun-id", lunid) 

    if (output.results_errno() != 0):
        r = output.results_reason()
        plog.print_error("LUN map failed: %s" %(r) )
        return False
    else:
        plog.print_log("lun %s is mapped to igroup: %s as id: %s." %(path, igroup, lunid))
        return True

def online_lun(filer, path):
  plog.print_log("Status change %s to Online." %(path))
  output = filer.invoke("lun-online", "path", path)

  if (output.results_errno() != 0):
      r = output.results_reason()
      plog.print_error("Unable to get online lun %s. %s" %(path, r) )
      return False
  else:
      plog.print_log("lun %s is now online." %(path))
      return True
  
def get_volume_snap_list(filer, volume):
  output = filer.invoke("snapshot-list-info", "volume", volume)

  if (output.results_errno() != 0):
      r = output.results_reason()
      plog.print_error("Unable to get snapshots for %s. %s" %(volume, r) )
      return False
  else:
      plog.print_log("snapshots for %s:" %(volume) )
      # # get snapshot list
      snapshotlist = output.child_get("snapshots")
      if ((snapshotlist == None) or (snapshotlist == "")) :
          # no snapshots to report
          plog.print_log("No snapshots on volume " + vol + "\n\n")
          sys.exit(0)

      # iterate through snapshot list
      snapshots = snapshotlist.children_get()
      snaplist = []
      for ss in snapshots:
          snaplist.append(ss.child_get_string("name"))
      return snaplist