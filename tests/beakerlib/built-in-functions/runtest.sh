#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Sanity/built-in-functions
#   Description: built-in functions for various conversions. New functionality according to BZ#1225135.
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
TUNED_DIR="/usr/lib/tuned"
PROFILE="myprofile"


rlJournalStart

    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlImport "tuned/basic"
        rlServiceStart "tuned"
        tunedProfileBackup


	PSITE_PATH=$(python3 -c "import site; print(site.getsitepackages()[3])")

	# RHEL7 is not supported
        if rlIsRHEL '>=8' || rlIsCentOS >= 8 || rlIsFedora; then
	    TEST_SCRIPT="rhel8_function_testfunc.py"
	fi
	rlRun "cp -v ${TEST_SCRIPT} ${PSITE_PATH}/tuned/profiles/functions/function_testfunc.py"

        # Prepare balanced profile
        rlRun "mkdir $TUNED_DIR/$PROFILE"
        rlRun -l "echo '[main]
summary=My testing profile

[variables]
VAR1 = \${f:testfunc:/var/tmp/test1:IamTestingThis1}
VAR2 = \${f:testfunc:/var/tmp/test2:\${VAR1}}
cmd = echo
cmd_out = \${f:exec:\${cmd}:output}
VAR3 = \${f:testfunc:/var/tmp/test3:\${cmd_out}}

' >> $TUNED_DIR/$PROFILE/tuned.conf"
        rlRun -l "cat $TUNED_DIR/$PROFILE/tuned.conf"
    
	    echo > /var/log/tuned/tuned.log
        rlRun "tuned-adm profile $PROFILE"
        rlRun -l "cat /var/log/tuned/tuned.log"
    rlPhaseEnd

    rlPhaseStartTest
        rlLog "Custom function and variable propagation"
        rlAssertGrep "IamTestingThis1" "/var/tmp/test1"
        rlAssertGrep "IamTestingThis1returned" "/var/tmp/test2"

        rlLog "Built in 'exec' function"
        rlAssertGrep "output" "/var/tmp/test3"	    
    rlPhaseEnd

    rlPhaseStartCleanup
        rlFileRestore
        tunedProfileRestore
        rlServiceRestore "tuned"
        rlRun "rm -rf $TUNED_DIR/$PROFILE"
        rlRun "rm ${PSITE_PATH}/tuned/profiles/functions/function_testfunc.py"
        rlRun "rm /var/tmp/test1 /var/tmp/test2"
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
