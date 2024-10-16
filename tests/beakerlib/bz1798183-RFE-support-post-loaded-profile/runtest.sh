#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /CoreOS/tuned/Regression/bz1798183-RFE-support-post-loaded-profile
#   Description: Test for BZ#1798183 (RFE support post-loaded profile)
#   Author: Ondřej Lysoněk <olysonek@redhat.com>
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
SYSCONF_DIR="/etc/tuned"
ACTIVE_PROFILE=/etc/tuned/active_profile
POST_LOADED_PROFILE="/etc/tuned/post_loaded_profile"
PROFILE_MODE=/etc/tuned/profile_mode
SWAPPINESS=vm.swappiness
DIRTY_RATIO=vm.dirty_ratio
PID_FILE=/run/tuned/tuned.pid
SERVICE_OVERRIDE_DIR=/etc/systemd/system/tuned.service.d
PYTHON_CHECK="python3 /usr/libexec/platform-python python2 python"
PYTHON=python3

function wait_for_tuned()
{
    local timeout=$1
    local elapsed=0
    while ! $PYTHON -c 'import dbus; bus = dbus.SystemBus(); exit(0 if bus.name_has_owner("com.redhat.tuned") else 1)'; do
        sleep 1
        elapsed=$(($elapsed + 1))
        if [ "$elapsed" -ge "$timeout" ]; then
            return 1
        fi
    done
    return 0
}

function wait_for_tuned_stop()
{
    local timeout=$1
    local elapsed=0
    while test -f "$PID_FILE"; do
        sleep 1
        elapsed=$(($elapsed + 1))
        if [ "$elapsed" -ge "$timeout" ]; then
            return 1
        fi
    done
    return 0
}


rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE

        rlImport "tuned/basic"
        tunedDisableSystemdRateLimitingStart
        rlRun "for PYTHON in $PYTHON_CHECK; do \$PYTHON --version 2>/dev/null && break; done" 0 "Detect python"
        PROFILE_DIR=$(tunedGetProfilesBaseDir)

        rlRun "rlFileBackup --clean $SYSCONF_DIR"
        rlRun "cp -r parent $PROFILE_DIR"
        rlRun "cp -r parent2 $PROFILE_DIR"
        rlRun "cp -r parent-vars $PROFILE_DIR"
        rlRun "cp -r post $PROFILE_DIR"
        rlRun "cp -r post2 $PROFILE_DIR"
        rlRun "cp -r post-vars $PROFILE_DIR"
        rlRun "cp -r conflicting $PROFILE_DIR"
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "cp wait_for_signal.py $TmpDir"
        rlRun "pushd $TmpDir"
        rlRun "rlFileBackup --clean $SERVICE_OVERRIDE_DIR"
        rlRun "mkdir -p $SERVICE_OVERRIDE_DIR"
        rlRun "echo -e '[Service]\\nStartLimitBurst=0' > $SERVICE_OVERRIDE_DIR/limit.conf"
        rlRun "systemctl daemon-reload"
        rlRun "rlServiceStop tuned"
        SWAPPINESS_BACKUP=$(sysctl -n $SWAPPINESS)
        DIRTY_RATIO_BACKUP=$(sysctl -n $DIRTY_RATIO)
        rlRun "rlServiceStart tuned"
    rlPhaseEnd

    rlPhaseStartTest "Check that settings from the post-loaded profile are applied"
        rlRun "tuned-adm profile parent"
        rlRun "echo post > $POST_LOADED_PROFILE"
        # Restart TuneD so that the post-loaded profile gets applied
        rlRun "rlServiceStart tuned"
        rlAssertEquals "Check that swappiness is set correctly" \
                       "$(sysctl -n $SWAPPINESS)" 20
        rlAssertEquals "Check that dirty ratio is set correctly" \
                       "$(sysctl -n $DIRTY_RATIO)" 8
    rlPhaseEnd

    rlPhaseStartTest "Check that the post-loaded profile name gets reloaded when HUP is received"
        rlRun "tuned-adm profile parent"
        rlRun "echo post > $POST_LOADED_PROFILE"
        rlRun "rlServiceStart tuned"
        rlRun "echo parent2 > $ACTIVE_PROFILE"
        rlRun "echo post2 > $POST_LOADED_PROFILE"
        timeout 25s $PYTHON ./wait_for_signal.py &
        pid=$!
        # Give the wait_for_signal script a chance to connect to the bus
        sleep 1
        rlRun "kill -HUP '$(< $PID_FILE)'" 0 "Send HUP to TuneD"
        rlRun "wait $pid"
        rlAssertEquals "Check that swappiness is set correctly" \
                       "$(sysctl -n $SWAPPINESS)" 30
        rlAssertEquals "Check that dirty ratio is set correctly" \
                       "$(sysctl -n $DIRTY_RATIO)" 7
    rlPhaseEnd

    rlPhaseStartTest "Check that 'tuned-adm profile' does not cause TuneD to touch the post-loaded profile"
        rlRun "tuned-adm profile parent"
        rlRun "echo post > $POST_LOADED_PROFILE"
        # Restart TuneD so that the post-loaded profile gets applied
        rlRun "rlServiceStart tuned"
        # Change the active profile. After this, the profile 'post' must remain applied.
        rlRun "tuned-adm profile parent2"
        rlAssertEquals "Check that swappiness is set correctly" \
                       "$(sysctl -n $SWAPPINESS)" 30
        rlAssertEquals "Check that dirty ratio is set correctly" \
                       "$(sysctl -n $DIRTY_RATIO)" 8
    rlPhaseEnd

    rlPhaseStartTest "Check that settings from the post-loaded profile take precedence"
        rlRun "tuned-adm profile parent"
        rlRun "echo conflicting > $POST_LOADED_PROFILE"
        # Restart TuneD so that the post-loaded profile gets applied
        rlRun "rlServiceStart tuned"
        rlAssertEquals "Check that swappiness is set correctly" \
                       "$(sysctl -n $SWAPPINESS)" 10
    rlPhaseEnd

    rlPhaseStartTest "Check that conflicts in the post-loaded profile do not cause verification to fail"
        rlRun "tuned-adm profile parent"
        rlRun "echo conflicting > $POST_LOADED_PROFILE"
        # Restart TuneD so that the post-loaded profile gets applied
        rlRun "rlServiceStart tuned"
        rlRun "tuned-adm verify"
    rlPhaseEnd

    rlPhaseStartTest "Check that 'tuned-adm off' causes TuneD to clear the post-loaded profile"
        rlRun "tuned-adm profile parent"
        rlRun "echo post > $POST_LOADED_PROFILE"
        # Restart TuneD so that the post-loaded profile gets applied
        rlRun "rlServiceStart tuned"
        rlRun "tuned-adm off"
        rlAssertEquals "Check the output of tuned-adm active" \
                       "$(tuned-adm active)" \
                       "No current active profile."
        rlAssertEquals "Check that swappiness has not been changed" \
                       "$(sysctl -n $SWAPPINESS)" "$SWAPPINESS_BACKUP"
        rlAssertEquals "Check that dirty ratio has not been changed" \
                       "$(sysctl -n $DIRTY_RATIO)" "$DIRTY_RATIO_BACKUP"
    rlPhaseEnd

    rlPhaseStartTest "Check that the post-loaded profile is applied even if active_profile is empty"
        rlRun "> $ACTIVE_PROFILE"
        rlRun "echo manual > $PROFILE_MODE"
        rlRun "echo post > $POST_LOADED_PROFILE"
        # Restart TuneD so that the post-loaded profile gets applied
        rlRun "rlServiceStart tuned"
        rlAssertEquals "Check the output of tuned-adm active" \
                       "$(tuned-adm active)" \
                       "Current active profile: post"$'\n'"Current post-loaded profile: post"
        rlAssertEquals "Check that dirty ratio is set correctly" \
                       "$(sysctl -n $DIRTY_RATIO)" 8
    rlPhaseEnd

    rlPhaseStartTest "Check that the post-loaded profile is listed among active profiles by 'tuned-adm active'"
        rlRun "tuned-adm profile parent"
        rlRun "echo post > $POST_LOADED_PROFILE"
        # Restart TuneD so that the post-loaded profile gets applied
        rlRun "rlServiceStart tuned"
        rlAssertEquals "Check the output of tuned-adm active" \
                       "$(tuned-adm active | grep 'Current active profile')" \
                       "Current active profile: parent post"
    rlPhaseEnd

    rlPhaseStartTest "Check that 'tuned -p <profile_name>' applies the post-loaded profile"
        rlRun "rlServiceStop tuned"
        rlRun "> $ACTIVE_PROFILE"
        rlRun "echo post > $POST_LOADED_PROFILE"
        rlRun "tuned -p parent &"
        rlRun "wait_for_tuned 15" 0 "Wait for the profile to become applied"
        rlAssertEquals "Check that swappiness is set correctly" \
                       "$(sysctl -n $SWAPPINESS)" 20
        rlAssertEquals "Check that dirty ratio is set correctly" \
                       "$(sysctl -n $DIRTY_RATIO)" 8
        rlAssertEquals "Check the output of tuned-adm active" \
                       "$(tuned-adm active | grep 'Current active profile')" \
                       "Current active profile: parent post"
        rlRun "kill '$(< $PID_FILE)'" 0 "Kill TuneD"
        rlRun "wait_for_tuned_stop 15" 0 "Wait for TuneD to exit"
    rlPhaseEnd

    rlPhaseStartTest "Check that the DBus signal 'profile_changed' contains only the active_profile"
        rlRun "rlServiceStop tuned"
        rlRun "echo parent > $ACTIVE_PROFILE"
        rlRun "echo post > $POST_LOADED_PROFILE"
        timeout 25s $PYTHON ./wait_for_signal.py > output &
        pid=$!
        # If the 'wait $pid' command below fails but everything else
        # in this phase succeeds, try adding a sleep here.
        rlRun "rlServiceStart tuned"
        rlRun "wait $pid"
        rlAssertEquals "Check the profiles listed in the signal" \
                       "$(< output)" \
                       "parent"

        timeout 25s $PYTHON ./wait_for_signal.py > output &
        pid=$!
        rlRun "tuned-adm profile parent"
        rlRun "wait $pid"
        rlAssertEquals "Check the profiles listed in the signal" \
                       "$(< output)" \
                       "parent"
    rlPhaseEnd

    rlPhaseStartTest "Check that 'tuned-adm profile' does not cause TuneD to reload the post-loaded profile name from disk"
        rlRun "tuned-adm profile parent"
        rlRun "echo post > $POST_LOADED_PROFILE"
        rlRun "rlServiceStart tuned"
        rlRun "echo post2 > $POST_LOADED_PROFILE"
        # Change the active profile. After this, the profile 'post' must remain applied.
        rlRun "tuned-adm profile parent2"
        rlAssertEquals "Check that swappiness is set correctly" \
                       "$(sysctl -n $SWAPPINESS)" 30
        rlAssertEquals "Check that dirty ratio is set correctly" \
                       "$(sysctl -n $DIRTY_RATIO)" 8
        rlAssertEquals "Check the output of tuned-adm active" \
                       "$(tuned-adm active | grep 'Current active profile')" \
                       "Current active profile: parent2 post"
    rlPhaseEnd

    rlPhaseStartTest "Check that 'tuned-adm profile' overwrites the post-loaded profile on disk"
        rlRun "tuned-adm profile parent"
        rlRun "echo post > $POST_LOADED_PROFILE"
        rlRun "rlServiceStart tuned"
        rlRun "echo post2 > $POST_LOADED_PROFILE"
        rlRun "tuned-adm profile parent"
        rlAssertEquals "Check the post-loaded profile name on disk" \
                       "$(< $POST_LOADED_PROFILE)" \
                       "post"
    rlPhaseEnd

    rlPhaseStartTest "Check that variables are shared among the active_profile and the post-loaded profile"
        rlRun "tuned-adm profile parent-vars"
        rlRun "echo post-vars > $POST_LOADED_PROFILE"
        # Restart TuneD so that the post-loaded profile gets applied
        rlRun "rlServiceStart tuned"
        rlAssertEquals "Check that swappiness is set correctly" \
                       "$(sysctl -n $SWAPPINESS)" 12
        rlAssertEquals "Check that dirty ratio is set correctly" \
                       "$(sysctl -n $DIRTY_RATIO)" 12
    rlPhaseEnd

    rlPhaseStartCleanup
        tunedDisableSystemdRateLimitingEnd
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
        rlRun "rlFileRestore"
        rlRun "systemctl daemon-reload"
        rlRun "sysctl $SWAPPINESS=$SWAPPINESS_BACKUP"
        rlRun "sysctl $DIRTY_RATIO=$DIRTY_RATIO_BACKUP"
        rlRun "rlServiceRestore tuned"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
