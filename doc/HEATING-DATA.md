# Heating data logs

The controller records each room's heating demand and achieved temperature as
lines in text files, one line per change. The files live on the controller
machine under a configurable data root, in a per-room, per-day hierarchy:

```
<root>/<Room Name>/<YYYY>/<MM>/<DD>.csv
```

For example:

```
/data/rbr-heating/Kitchen/2026/09/02.csv
/data/rbr-heating/Main Bedroom/2026/09/02.csv
```

## Line format

Four comma-separated values per line:

```
epochMinutes,targetTenths,actualTenths,mode
```

| Field        | Meaning                                                            |
|--------------|--------------------------------------------------------------------|
| `epochMinutes` | Minutes since the Unix epoch (controller clock / 60000).         |
| `targetTenths` | Target temperature in tenths of a degree (207 = 20.7 °C).        |
| `actualTenths` | Actual temperature in tenths of a degree.                        |
| `mode`         | One letter: `o` off, `c` on (constant target), `p` timed (periods/schedule), `b` boost. |

Example rows:

```
30504123,207,205,p
30504231,207,207,c
30504312,207,207,o
```

The date in the file path is derived from the row's own `epochMinutes` in the
controller's local timezone, so a change at 23:59 lands in the correct day's
file. Values are rounded to whole tenths (internal hundredths, rounded half
up) before logging, so 0.01 °C sensor jitter does not create rows.

## When a row is written

Rows are **event-driven**: a row is appended only when a room's target,
actual, or mode changes since the last logged row. Between rows the values
are unchanged, so analysis should forward-fill (hold the last value).
Steady rooms therefore log very little; a room whose temperature drifts
continuously logs a few rows an hour.

A row is logged on:

- a change in the computed target (schedule period roll, advance/boost,
  manual target change), the fresh actual temperature, or the mode letter;
- startup, once a room's first fresh reading arrives (a baseline row — this
  also marks controller restarts in the data);
- off mode, where the logged target tracks the actual (`mode o`).

A row is **not** logged when:

- heat logging is disabled (no `heatlog-root` file in the controller working
  directory);
- the room has no thermometer configured;
- the room's relay is unlinked (`linked: no` — driven directly by mode, so
  target-vs-actual has no meaning for it);
- the sensor is stale (no fresh reading — a gap in the log means "no valid
  reading", not "no change"; the controller forces the relay off during
  staleness, so nothing heating-relevant is missed).

### Relay-state inference

A relay is on iff `mode` is one of `c`/`p`/`b` **and** `targetTenths` is
greater than `actualTenths`. Off-mode rows (`o`) never imply demand because
target equals actual by construction. The exceptions to the inference are
degraded states that the log intentionally does not capture:

- sensor staleness / relay-failure lockout (relay forced off — during these
  windows no rows are written once the reading goes stale, so there is
  nothing to misread);
- boost engaged with a dead sensor (relay on without a fresh actual — no row
  until the sensor returns).

If you ever need to tell "room was off" from "room was satisfied at
target", the `mode` letter does exactly that (`o` vs `c`/`p` with
target == actual).

## Configuration and storage

- The data root is the one-line content of a file named `heatlog-root` in
  the controller's working directory (e.g. `/home/linaro/heatlog-root`).
  Absent that file, heat logging is disabled and the controller logs that at
  startup. `rbr-setup.sh` (Step 5b) creates the file.
- The **same absolute root path is used on every machine**. On the
  controller the path is normally a dedicated data partition, e.g.
  mounted at `/data/rbr-heating`. On machines without the partition the
  same path is a symlink to a directory on the local disk:

  ```sh
  sudo mkdir -p /home/<user>/heating-data
  sudo chown <user>:<user> /home/<user>/heating-data
  sudo ln -s /home/<user>/heating-data /data/rbr-heating
  ```

  The writer follows the symlink transparently, so test and production
  behave identically.
- `heatlog-state.json` (working directory) holds each room's last logged
  target/actual/mode and is flushed once a minute. On restart the controller
  resumes from it, so a restart neither re-logs the current state as a
  spurious change nor misses the post-restart baseline.
- Both files are machine-specific data: they are never shipped in or
  replaced by the release tarball (`rbr-updater.py` only replaces code
  files), and they are git-ignored in the repo.
- To move the data later: mount the new partition, point
  `heatlog-root` at it (or replace the symlink), ensure the controller user
  can write it, and restart the controller.

## Updating, backup, housekeeping

- `heatlog.py` (shipped with the controller release) is the single writer:
  `python3 heatlog.py --root <root> --room <room> --ts <minutes> --target <t> --actual <a> --mode <m>`.
  It creates the day directories as needed and appends with one atomic
  `O_APPEND` write. The controller spawns it via `system background` on
  each change.
- Rows are tiny and sparse; a whole house-year is well under a megabyte.
  Back up `<root>` with the rest of the machine data. Files older than you
  care about can simply be deleted — nothing in the controller needs them.

## Testing

- `tests/unit/heatlog_test.py` — the writer (path/date derivation, symlink
  root, CLI). Runs via `tests/unit/run-unit-tests.sh` or directly.
- `tests/unit/unit-09-heatlog.as` — the controller-side decision logic
  (rounding, mode letters/off-mode rule, change predicate), mirrored from
  `HeatlogRecord` in `controller.as`.
