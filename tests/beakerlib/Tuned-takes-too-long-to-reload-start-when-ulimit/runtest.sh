#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/Tuned-takes-too-long-to-reload-start-when-ulimit
#   Description: Test for BZ#1663412 (TuneD takes too long to reload/start when "ulimit)
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
        rlAssertRpm $PACKAGE
        rlImport "tuned/basic"
        tunedDisableSystemdRateLimitingStart
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlServiceStop "tuned"
        rlFileBackup "/etc/tuned/tuned-main.conf"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "sed 's/daemon = 1/daemon = 0/g' /etc/tuned/tuned-main.conf > /etc/tuned/tuned-main.conf.new"
        rlRun "mv /etc/tuned/tuned-main.conf.new /etc/tuned/tuned-main.conf"
        rlRun "ulimit -H -n 1048576"
        rlRun "ulimit -S -n 1048576"
        rlRun "tuned --debug 2>&1 | tee TEST_OUT"
        rlAssertNotGrep "tuned.plugins.plugin_sysctl: executing \['sysctl'," TEST_OUT
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"

        killall tuned
        rlRun "sleep 3"
        killall tuned

        tunedDisableSystemdRateLimitingEnd
        rlFileRestore
        rlServiceRestore "tuned"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
