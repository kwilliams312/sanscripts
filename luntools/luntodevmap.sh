#!/bin/bash
#
# takes LUNID from Array and provides /dev/mapper device associated with it
# next steps: create multipath functionality (currently only single pathed)
#
# ken.williams@clearcapital.com
##########################################

if [ "X$1" == "X" ]; then
  echo "usage: luntodevid.sh LUNID"
  exit 1
fi
# runs the multipath command looking for LUNID $1 (from the command line)
MULTIPATH=$(multipath -ll |egrep -B3 "_ [0-9]:[0-9]:[0-9]:$1 ")

# sets DEVID to the device ID
DEVID=`echo $MULTIPATH | head -n1 | awk '{ print $1 }'`
STORAGETYPE=`echo $MULTIPATH | head -n1 | awk '{ print $3 }'`
DMID=`echo $MULTIPATH | head -n1 | awk '{ print $2 }'`

if [ "X$DEVID" == "X" ]; then
  echo "LUN not found"
  exit 1
fi

echo "/dev/mapper/$DEVID is connected to LUNID $1"
echo "Storage type is $STORAGETYPE"
echo "DMID is $DMID"

