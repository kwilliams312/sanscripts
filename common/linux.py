#!/opt/python2.7/bin/python2.7
#
# various linux tasks
#
########################################

import plog
import subprocess

def run_remote_command(host, command):
    # this requires sshkeys to function!
    plog.print_log("%s: running command: %s" %(host, command))
    process = subprocess.Popen("ssh root@%s %s" % (host, command), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output,stderr = process.communicate()
    status = process.poll()
    return output

def rescan_scsi(host):
    plog.print_log("Re-Scanning SCSI bus on %s" %(host))
    rescan_bus = '/usr/bin/rescan-scsi-bus.sh'
    return run_remote_command(host, rescan_bus)

def get_device_id_from_lun(host, lunid):
    plog.print_log("Getting SCSI id for lun %s on %s" %(lunid, host))
    multipath = "multipath -ll |egrep -B3 \" [0-9]:[0-9]:[0-9]:%s \" | head -n1 | awk '{ print $1 }'" %(lunid)
    return run_remote_command(host, multipath)

def add_multipath_devices(host):
    plog.print_log("Adding new multipath devices on %s" %(host))
    cmd = "multipath"
    return run_remote_command(host, cmd)
    
def remove_multipath_devices(host, lunid):
    device_id = get_device_id_from_lun(host, lunid)
    cmd = "multipath -f %s" %(device_id)
    plog.print_log("Removing multipath device with command: %s, on: %s" %(cmd, host))
    return run_remote_command(host, cmd)
        
def xfs_freeze(host,path):
    plog.print_log("freezeing xfs mount: %s on %s" %(path, host))
    cmd = "xfs_freeze -f %s" %(path)
    return run_remote_command(host, cmd)

def xfs_unfreeze(host,path):
    plog.print_log("unfreezeing xfs mount: %s on %s" %(path,host))
    cmd = "xfs_unfreeze -u %s" %(path)
    return run_remote_command(host, cmd)

def shutdown(host):
    plog.print_log("Sending shutdown command to %s" %(host))
    cmd = "shutdown -h now"
    return run_remote_command(host, cmd)