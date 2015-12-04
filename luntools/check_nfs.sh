#!/bin/bash
#
# check if a nfs mount exists
#############################################################

# checking command line parameters
if [ "$1x" == "x" ]; then
   echo "Usage: $0: location_to_check"
   exit 1
else
   location="$1"
fi

# check to see the type of mount at $location
mounttype=$( stat -f -L -c %T $location  )

if [ $mounttype != "nfs" ]; then
   # if its not NFS, error out
   echo 1
else
   echo 0
fi

