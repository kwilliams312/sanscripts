#!/bin/bash

if [ "X$1" == "X" ]; then
  echo "usage: cleanup_lun.sh LUNID"
  exit 1
fi

for a in `multipath -ll |egrep [0-9]:[0-9]:[0-9]:$1 | awk -F":" '{ print $4 }'|awk '{print $2}'`; do
   echo removing device ${a} on lun $1
   echo 1 > /sys/block/${a}/device/delete
done

