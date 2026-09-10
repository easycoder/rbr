#!/usr/bin/env bash
# rbr-watchdog.sh — RBR component watchdog.
#
# Run hourly by rbr-watchdog.timer (units installed by rbr-setup.sh STEP 6b;
# see the repo for reference copies). The script itself ships in
# rbr-controller.tar.gz and lives in the controller runtime dir, so the
# hourly updater refreshes it with each release. For each core service it:
#   1. re-enables it if it was disabled (so it survives reboots — the Sep-2026
#      outage was a bridge that never came back after a power-cut reboot), and
#   2. restarts it if it is not running, or if it is active but fails its
#      lightweight health probe (wedged process).
#
# Read-only apart from the restarts it performs and the log lines it writes via
# logger — see `journalctl -t rbr-watchdog`.
#
# Manual run (as root, e.g. for a test):
#     sudo /home/graham/rbr/rbr-watchdog.sh    (default install dir)
#
# Services checked (override for testing, e.g. RBR_WATCH_SERVICES="foo" ...):
set -u

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
            else
                log "$svc restart FAILED"
                failures=$((failures + 1))
            fi
        fi
    fi
done

if [ "$failures" -gt 0 ]; then
    log "completed with $failures failure(s)"
    exit 1
fi

log "all services OK"
exit 0
