#!/opt/python2.7/bin/python2.7
#
# some simple logging facilities
# todo: option to log to syslog
#####################################
from datetime import datetime, date, time # date/time

global DEBUGMODE
def print_log(logText):
    print '[INFO][' + datetime.now().strftime("%b %m %Y %H:%M:%S") + '] ' + logText
def print_warn(logText):
    print '[WARN][' + datetime.now().strftime("%b %m %Y %H:%M:%S") + '] ' + logText
def print_error(logText):
    print '[ERROR][' + datetime.now().strftime("%b %m %Y %H:%M:%S") + '] ' + logText
def print_debug(logText):
    if (DEBUGMODE==True):
        print '[DEBUG][' + datetime.now().strftime("%b %m %Y %H:%M:%S") + '] ' + logText

