#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/Settings-in-usr-lib-sysctl-d-take-precedence-over
#   Description: Test for BZ#1759597 (Settings in /usr/lib/sysctl.d take precedence over)
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
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlImport "tuned/basic"
        tunedProfileBackup
        rlServiceStart "tuned"

        rlRun "ORIG_VAL=$(sysctl -n sysctl kernel.yama.ptrace_scope)"

        rlAssertGrep "reapply_sysctl = 1" "/etc/tuned/tuned-main.conf"

        rlRun "mkdir /etc/tuned/test-profile"
        rlRun "pushd /etc/tuned/test-profile"
        cat << EOF > tuned.conf
[sysctl]
kernel.yama.ptrace_scope=1
EOF
        rlRun "popd"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "VAL_STATE=$(sysctl -n kernel.yama.ptrace_scope)"
        rlAssertEquals "val should be 0" "$VAL_STATE" "0"

        rlRun "tuned-adm profile test-profile"

        rlRun "VAL_STATE=$(sysctl -n kernel.yama.ptrace_scope)"
        rlAssertEquals "val should be 1" "$VAL_STATE" "1"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlFileRestore
        tunedProfileRestore
        rlServiceRestore "tuned"

        rlRun "sysctl -w kernel.yama.ptrace_scope=$ORIG_VAL"
        rlRun "rm -rf /etc/tuned/test-profile"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
