#!/bin/sh

type getargs >/dev/null 2>&1 || . /lib/dracut-lib.sh

cpumask="$(getargs tuned.non_isolcpus)"

files=$(echo /sys/devices/virtual/workqueue{/,/*/}cpumask)

log()
{
  echo "tuned: $@" >> /dev/kmsg
}

if [ -n "$cpumask" ]; then
  log "setting workqueues CPU mask to $cpumask"
  for f in $files; do
    if [ -f $f ]; then
      if ! echo $cpumask > $f 2>/dev/null; then
        log "ERROR: could not write workqueue CPU mask '$cpumask' to '$f'"
      fi
    fi
  done
fi
