#!/usr/bin/env bash
# rbr-watchdog.sh — RBR component watchdog.
#
# Run every 15 minutes by rbr-watchdog.timer (units installed by rbr-setup.sh
# STEP 6b; see the repo for reference copies). The script itself ships in
# rbr-controller.tar.gz and lives in the controller runtime dir, so the
# hourly updater refreshes it with each release. For each core service it:
#   1. re-enables it if it was disabled (so it survives reboots — the Sep-2026
#      outage was a bridge that never came back after a power-cut reboot), and
#   2. restarts it if it is not running, or if it is active but fails its
#      lightweight health probe (wedged process).
#
# It then checks whether the heating is actually happening. heatwatch.py reads
# the plan and the fresh readings (plus the heating log when enabled) and, if a
# scheduled room has been calling for heat for an hour without warming, restarts
# all four core services. See heatwatch.py for the rule and the cooldown.
#
# Read-only apart from the restarts it performs, the heating check's
# heat-watch-state.json in the volatile directory, and the log lines it writes
# via logger — see `journalctl -t rbr-watchdog`.
#
# Manual run (as root, e.g. for a test):
#     sudo /home/graham/rbr/rbr-watchdog.sh    (default install dir)
#
# Services checked (override for testing, e.g. RBR_WATCH_SERVICES="foo" ...):
# The heating check is skipped when RBR_WATCH_HEAT=0, and after this run has
# already restarted a core service (that service gets a fresh cycle first).
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DEFAULT_SERVICES=(mosquitto zigbee2mqtt rbr-zigbee-bridge controller)

if [ -n "${RBR_WATCH_SERVICES:-}" ]; then
    # shellcheck disable=SC2206
    SERVICES=($RBR_WATCH_SERVICES)
else
    SERVICES=("${DEFAULT_SERVICES[@]}")
fi

log() { logger -t rbr-watchdog "$*"; }

# Health probes: return 0 when the service looks alive. The systemd is-active
# check catches crashes (systemd already restarts those via Restart=on-failure);
# these probes catch processes that are up but wedged — the failure mode that
# Restart=on-failure never sees. Probes must be cheap and never false-positive,
# because a failed probe causes a restart.

# mosquitto — accept a TCP connection on 1883 (bash /dev/tcp, no nc dependency)
probe_mosquitto() {
    (exec 3<>/dev/tcp/127.0.0.1/1883) >/dev/null 2>&1
}

# zigbee2mqtt — its frontend answers HTTP on 8080
probe_zigbee2mqtt() {
    curl -sf -m 3 http://127.0.0.1:8080/ >/dev/null 2>&1
}

# rbr-zigbee-bridge — its /health endpoint answers on 8889
probe_rbr_zigbee_bridge() {
    curl -sf -m 3 http://127.0.0.1:8889/health >/dev/null 2>&1
}

# controller — AllSpeak daemon; no safe HTTP probe, is-active is sufficient
probe_controller() {
    return 0
}

failures=0
restarts_this_run=0

for svc in "${SERVICES[@]}"; do
    # 1) survive reboots — re-enable if someone/something disabled the unit
    if ! systemctl is-enabled --quiet "$svc" 2>/dev/null; then
        if systemctl enable "$svc" >/dev/null 2>&1; then
            log "$svc was disabled — re-enabled"
        else
            log "$svc could not be re-enabled (unknown unit?)"
            failures=$((failures + 1))
        fi
    fi

    # 2) running?
    if ! systemctl is-active --quiet "$svc" 2>/dev/null; then
        log "$svc is not running — restarting"
        if systemctl restart "$svc" >/dev/null 2>&1; then
            log "$svc restarted OK"
            restarts_this_run=$((restarts_this_run + 1))
        else
            log "$svc restart FAILED"
            failures=$((failures + 1))
        fi
        continue
    fi

    # 3) active but wedged? only if a probe is defined for this service
    #    (probe function names use '_' where the unit name uses '-')
    probe_fn="probe_$(printf '%s' "$svc" | tr -- '-.' '__')"
    if declare -F "$probe_fn" >/dev/null 2>&1; then
        if ! "$probe_fn"; then
            log "$svc is active but health probe failed — restarting"
            if systemctl restart "$svc" >/dev/null 2>&1; then
                log "$svc restarted OK"
                restarts_this_run=$((restarts_this_run + 1))
            else
                log "$svc restart FAILED"
                failures=$((failures + 1))
            fi
        fi
    fi
done

# 4) Is the heat actually arriving? The component checks above only prove the
#    services are up; a controller or bridge can be running and still fail to
#    drive the valves. heatwatch.py reads the plan and the readings and restarts
#    all four services when a scheduled room has not warmed. It is skipped for
#    one run after a service restart so the fresh process gets a full cycle.
if [ "${RBR_WATCH_HEAT:-1}" = "0" ]; then
    log "heating check disabled by RBR_WATCH_HEAT=0"
elif [ "$restarts_this_run" -gt 0 ]; then
    log "heating check deferred: a core service was restarted this run"
elif [ -f "$SCRIPT_DIR/heatwatch.py" ]; then
    if ! python3 "$SCRIPT_DIR/heatwatch.py" --rbr-dir "$SCRIPT_DIR"; then
        log "heating check reported a failed restart"
        failures=$((failures + 1))
    fi
else
    log "heatwatch.py not found — heating check skipped"
fi

if [ "$failures" -gt 0 ]; then
    log "completed with $failures failure(s)"
    exit 1
fi

log "all services OK"
exit 0
