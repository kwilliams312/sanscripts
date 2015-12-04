#!/opt/python2.7/bin/python2.7
# rhevm api tools
#####################################

import urllib2
import base64
import time
from xml.etree import ElementTree
import plog
import sys

global rm_host
global rm_user
global rm_pass
global rm_port 

# Get VM ID based on VM_NAME
def getVMId(vm_name):

        URL = "https://%s:%s/api/vms/" %(rm_host,rm_port)
        request = urllib2.Request(URL)
        base64string = base64.encodestring('%s:%s' % (rm_user, rm_pass)).strip()
        request.add_header("Authorization", "Basic %s" % base64string)

        try:
                xmldata = urllib2.urlopen(request).read()
        except urllib2.URLError, e:
                plog.print_error("Error: cannot connect to REST API: %s" % (e))
                sys.exit(1)

        tree = ElementTree.XML(xmldata)
        list = tree.findall("vm")

        vm_id = None
        for item in list:
                if vm_name == item.find("name").text:
                        vm_id = item.attrib["id"]
                        plog.print_log("vm id %s" % (vm_id))
                        break

        return vm_id

# shutdown VM_NAME
def guest_shutdown(vm_name):
   plog.print_log("shutdown vm: %s" %(vm_name))

   vm_id = getVMId(vm_name)

   if vm_id == None:
       plog.print_error("Cannot find virtual machine: %s" %(vm_name))
       sys.exit(1)

   xml_request ="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
   <action/>
   """

   # Setting URL
   URL = "https://%s:%s/api/vms/%s/shutdown" %(rm_host,rm_port,vm_id)

   request = urllib2.Request(URL)
   plog.print_log("Connecting to: %s" %(URL))

   base64string = base64.encodestring('%s:%s' % (rm_user, rm_pass)).strip()
   request.add_header("Authorization", "Basic %s" % base64string)
   request.add_header('Content-Type', 'application/xml')
   request.get_method = lambda: 'POST'

   try:
   	ret = urllib2.urlopen(request, xml_request)
   except urllib2.URLError, e:
          plog.print_error( "guest is already Down.")

def guest_start(vm_name):
   plog.print_log("starting up vm: %s" %(vm_name))

   vm_id = getVMId(vm_name)

   if vm_id == None:
       plog.print_error("Cannot find virtual machine: %s" %(vm_name))
       sys.exit(1)

   xml_request ="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
   <action/>
   """

   # Setting URL
   URL = "https://%s:%s/api/vms/%s/start" %(rm_host,rm_port,vm_id)

   request = urllib2.Request(URL)
   plog.print_log("Connecting to: %s" %(URL))

   base64string = base64.encodestring('%s:%s' % (rm_user, rm_pass)).strip()
   request.add_header("Authorization", "Basic %s" % base64string)
   request.add_header('Content-Type', 'application/xml')
   request.get_method = lambda: 'POST'

   try:
        ret = urllib2.urlopen(request, xml_request)
   except urllib2.URLError, e:
          plog.print_error( "guest is already Up.")


def is_guest_down(vm_name):
    vm_id = getVMId(vm_name)

    if vm_id == None:
        plog.print_error("Cannot find virtual machine: %s" %(vm_name))
        sys.exit(1)

    URL = "https://%s:%s/api/vms/%s" %(rm_host,rm_port,vm_id)
    request = urllib2.Request(URL)
    base64string = base64.encodestring('%s:%s' % (rm_user, rm_pass)).strip()
    request.add_header("Authorization", "Basic %s" % base64string)
    xmldata = urllib2.urlopen(request).read()

    tree = ElementTree.XML(xmldata)
    list = tree.findall("status")

    for item in list:
        plog.print_debug("Current state is: %s" %(item.find("state").text))
        if (item.find("state").text == "down"):
            return True
        else:
            return False

def is_guest_up(vm_name):
    vm_id = getVMId(vm_name)

    if vm_id == None:
        plog.print_error("Cannot find virtual machine: %s" %(vm_name))
        sys.exit(1)

    URL = "https://%s:%s/api/vms/%s" %(rm_host,rm_port,vm_id)
    request = urllib2.Request(URL)
    base64string = base64.encodestring('%s:%s' % (rm_user, rm_pass)).strip()
    request.add_header("Authorization", "Basic %s" % base64string)
    xmldata = urllib2.urlopen(request).read()

    tree = ElementTree.XML(xmldata)
    list = tree.findall("status")

    for item in list:
        plog.print_debug("Current state is: %s" %(item.find("state").text))
        if (item.find("state").text == "up"):
            return True
        else:
            return False

# sets the custom property on a vm  for DIRECTLUN only
def guest_set_directlun(vm_name, deviceid, memorysize):
    xml_request ="""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <vm>
    <custom_properties>
    <custom_property value="%s" name="directlun"/>
    </custom_properties>
    <memory>%s</memory>
    </vm>
    """ %(deviceid.strip(),memorysize)

    vm_id = getVMId(vm_name)

    if vm_id == None:
        plog.print_error("Cannot find virtual machine: %s" %(vm_name))
        sys.exit(1)

    # Setting URL
    URL = "https://%s:%s/api/vms/%s" %(rm_host,rm_port,vm_id)

    request = urllib2.Request(URL)
    plog.print_log("Connecting %s to %s. " %(deviceid,vm_name))

    base64string = base64.encodestring('%s:%s' % (rm_user, rm_pass)).strip()
    request.add_header("Authorization", "Basic %s" % base64string)
    request.add_header('Content-Type', 'application/xml')
    request.get_method = lambda: 'PUT'

    try:
        xmldata = urllib2.urlopen(request, xml_request)
    except urllib2.URLError, e:
        plog.print_log("Cannot connect to REST API: %s" % (e))
        plog.print_log("Possible errors: ")
        plog.print_log("\t- Try to login using the same user/pass by the Admin Portal and check the error!")
        sys.exit(1)

