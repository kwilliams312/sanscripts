#!/bin/bash

rescan-scsi-bus.sh && multipath && multipath -ll
