#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/Expose-TuneD-API-to-the-Unix-Domain-Socket
#   Description: Test for BZ#2113900 (Expose TuneD API to the Unix Domain Socket)
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

send() {
  local data="$1"
  local socket=/run/tuned/tuned.sock
#  local send_only=--send-only
  
  printf "$data" | nc $send_only -U /run/tuned/tuned.sock
}

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"

        rlServiceStart "tuned"
        rlImport "tuned/basic"
        tunedProfileBackup

	rlFileBackup '/etc/tuned/tuned-main.conf'

	rlRun "sed -i '/#\? \?unix_socket_path =.*/ {s##unix_socket_path = /run/tuned/tuned.sock#;}' /etc/tuned/tuned-main.conf"
	rlRun "sed -i '/#\? \?enable_unix_socket =.*/ {s##enable_unix_socket = 1#;}' /etc/tuned/tuned-main.conf"
        rlServiceStop "tuned"
        rlServiceStart "tuned"
    rlPhaseEnd

    rlPhaseStartTest

    	rlRun "tuned-adm profile virtual-host"
    	rlRun "tuned-adm profile virtual-guest"
	sleep 2

	send '{"jsonrpc": "2.0", "method": "active_profile", "id": 1}' | tee TESTOUT

	rlAssertGrep "virtual-guest" "TESTOUT"

	# combination of calls
	send '[{"jsonrpc": "2.0", "method": "active_profile", "id": 1}, {"jsonrpc": "2.0", "method": "profiles", "id": 2}]' | tee TESTOUT
	rlAssertGrep '"result": "virtual-guest"' "TESTOUT"
	rlAssertGrep 'optimize-serial-console' "TESTOUT"

	send '{"jsonrpc": "2.0", "method": "switch_profile", "params": {"profile_name": "balanced"}, "id": 1}' | tee TESTOUT
	rlAssertGrep "true, \"OK\"" "TESTOUT"
	
	rlRun "tuned-adm active | tee TESTOUT"
	rlAssertGrep "balanced" TESTOUT
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"

        tunedProfileRestore
	rlServiceStop "tuned"

	rlFileRestore
        rlServiceRestore "tuned"
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
