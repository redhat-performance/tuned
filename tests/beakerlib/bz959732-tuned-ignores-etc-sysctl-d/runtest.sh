#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/bz959732-tuned-ignores-etc-sysctl-d
#   Description: Test for BZ#959732 (tuned ignores /etc/sysctl.d)
#   Author: Robin Hack <rhack@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright Red Hat
#
#   SPDX-License-Identifier: GPL-2.0-or-later WITH GPL-CC-1.0
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="tuned"

rlJournalStart
    rlPhaseStartSetup

        DEFAULT_PROFILE="balanced"
        rlIsRHEL 6 && DEFAULT_PROFILE="default"

        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlServiceStart "tuned"
        rlRun "mkdir -p /etc/sysctl.d"
	rlRun "OLD_VALUE=$(sysctl -n fs.file-max)"
        rlRun "NEW_VALUE=$(($OLD_VALUE-1))"
        rlLog "Create file in /etc/sysctl.d/ with custom value"
        rlRun "echo \"fs.file-max = $NEW_VALUE\" > /etc/sysctl.d/custom.conf"
    rlPhaseEnd

    rlPhaseStartTest
	for profile in $(tuned-adm list | awk '/^-/ {print $2}')
        do
            rlLog "Profile: ${profile}"
	    rlRun "test $(sysctl -n fs.file-max) -eq $OLD_VALUE"
            rlRun "tuned-adm profile ${profile}"
	    sleep 1
	    rlRun "test $(sysctl -n fs.file-max) -eq $NEW_VALUE"
            rlRun "sysctl -w fs.file-max=$OLD_VALUE"
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlServiceRestore "tuned"
        rlRun "sysctl fs.file-max=$OLD_VALUE"
        rlRun "rm -rf /etc/sysctl.d/custom.conf"
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
