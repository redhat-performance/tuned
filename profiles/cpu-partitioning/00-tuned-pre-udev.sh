#!/bin/sh

type getargs >/dev/null 2>&1 || . /lib/dracut-lib.sh

cpumask="$(getargs tuned.non_isolcpus)"

file=/sys/devices/virtual/workqueue/cpumask

log()
{
  echo "tuned: $@" >> /dev/kmsg
}

if [ -n "$cpumask" ]; then
  log "setting workqueue CPU mask to $cpumask"
  if ! echo $cpumask > $file 2>/dev/null; then
    log "ERROR: could not write workqueue CPU mask"
  fi
fi
