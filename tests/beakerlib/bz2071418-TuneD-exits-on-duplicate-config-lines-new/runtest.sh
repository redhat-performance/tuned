#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/bz2071418-TuneD-exits-on-duplicate-config-lines-new
#   Description: Test for BZ#2071418 (TuneD exits on duplicate config lines (new)
#   Author: something else <rhack@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2022 Red Hat, Inc.
#
#   This program is free software: you can redistribute it and/or
#   modify it under the terms of the GNU General Public License as
#   published by the Free Software Foundation, either version 2 of
#   the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE.  See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see http://www.gnu.org/licenses/.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="tuned"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE


        rlImport "tuned/basic"
        rlServiceStart "tuned"
        tunedProfileBackup

        rlRun "mkdir /etc/tuned/test-profile"
        rlRun "pushd /etc/tuned/test-profile"
        cat << EOF > tuned.conf
[sysctl]
kernel.sem = 1250 256000 100 8192
kernel.sem = 1250 256000 100 8192

[selinux]
avc_cache_threshold=8192 
avc_cache_threshold=16384
EOF

        rlRun "popd"

        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tuned-adm profile test-profile"
        rlRun "tuned-adm verify"

        rlAssertGrep "test-profile" "/etc/tuned/active_profile"

	# last value from config is used
	rlAssertGrep "16384$"  /sys/fs/selinux/avc/cache_threshold
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"

        tunedProfileRestore
        rlServiceRestore "tuned"

        rlRun "rm -rf /etc/tuned/test-profile"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
