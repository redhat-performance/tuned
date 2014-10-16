#!/bin/bash

systemctl restart tuned
tuned-adm recommend
PROFILES=`tuned-adm list | sed -n '/^\-/ s/^- // p'`
for p in $PROFILES
do
  tuned-adm profile "$p"
  sleep 5
  tuned-adm active
done
tuned-adm profile `tuned-adm recommend`
