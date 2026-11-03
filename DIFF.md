# What to do

- **Deploy** with `./deploy.sh --release`; `rbr-setup.sh` ships in the update tarball.
- On a controller, re-running `sudo ./rbr-setup.sh` now installs `controller.service` when you press Enter at Step 7. Answer `n` only if you deliberately want to skip it.
- No map change and no other action.

# What changed

Step 7 asked `Run the controller as a service (auto-restart after updates)? (y/N)` and skipped unless the answer was exactly `y`. The default is now **yes**: pressing Enter installs the service, and only an explicit `n`/`no` skips it (the check is case-insensitive, and `yes` also installs).

The prompt now goes through the existing `prompt_value` helper, so a closed stdin aborts with a clear message instead of silently taking an empty answer. The install guide and `doc/setupRBR.md` describe the new default.

# Tests

`bash -n rbr-setup.sh` and `git diff --check` pass. The acceptance table was exercised directly: `y`, `Y`, `yes`, `YES` install; `n`, `N`, `no`, `NO` skip. The backup/restore tests are unaffected.
