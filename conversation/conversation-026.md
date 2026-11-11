# 2026-11-11

## 10:45

When running a scenario headlessly, the Log panel only updates very intermittemtly. Is this because the runner doesn't yield? If so, perhaps it should have `wait 1 tick` before each step begins.

**Assistant**

No — the runner is not the constraint. It is a separate process, and `Events.emit` writes and flushes every JSONL line as it happens (`scenario_runner/protocol.py`). I ran `docs/examples/advance.json` headless with timestamps today: during the 9.4-second step `s10` (a 3-hour clock jump, 15:00 → 18:00) the runner emitted 216 `log` events *while the step was running* — one per 50-second clock slice. It streams throughout the step; it does not stall. The long silences fall at step boundaries, not inside them.

The batching is in the Studio's UI pump. The AllSpeak graphics runtime drains the process/MQTT intent queue on a 250 ms Qt timer (`allspeak/as_graphics.py:1600`), running every queued handler in one go and repainting once after the batch. I measured the real shell offscreen (`kitchen-temperature.json`, sampling every 20 ms): Console and Wire changed at 0.21–0.28 s intervals, i.e. four updates a second at best, however fast the child writes. `Log` changed only 8 times over the run, because of what it is fed.

That is the second half of the explanation: `RunnerLine` in `studio.allspeak` routes only `step.started`/`step.finished` and runner messages to `Log`; page console output goes to `Console`, raw JSONL to `Wire`. During a long step `Log` is genuinely silent while `Console` is streaming. Steps themselves take ~0.65 s each in the examples, so what looks like an update is often one step boundary landing in the next 250 ms tick.

`wait 1 tick` would not change either behaviour:

- the runner is Python; there is no tick — the nearest thing is `time.sleep(0.01)`;
- a tick is 10 ms (`as_core.py`, `multipliers['tick'] = 10`), so it cannot alter a 250 ms pump;
- pacing before each step only thins events; it cannot make the panel repaint more often. Even a full 250 ms sleep per step would just make the run slower while keeping the same 4 Hz cadence.

What would actually help, in order of effect:

1. Pass `--collapse-polls` to headless Run as Show already does. A long fast-forward currently sends one `Requesting map: refresh` line per 50-second slice to Console and Wire (~1,700 over a day); the complete stream still lands in the run's `console.log`.
2. Emit a progress event per fast-forward slice inside a long step, so `Log` has a line to show while the step is still running (still 4 Hz, but no longer silent).
3. Cut per-event cost in the shell: `FindStep` scans every row for every step event (linear, twice per step, on a 1,002-step journal scenario), and `TrimStepsLog` rewrites the whole log.
4. If the 4 Hz ceiling itself is the problem, that is upstream: the flush interval lives in the installed runtime, not this repo, so it wants a `REQUESTS.md` entry asking for a configurable or shorter graphics flush interval.

One doc/code disagreement turned up on the way: `TrimStepsLog`'s block says the trim runs "every hundred ticks (about a second)", but each `wait 1 tick` is requeued through the same 250 ms pump, so 100 ticks is about 25 seconds.

I have made no changes. Say which of 1–3 you want and I'll implement it.

## 11:02

I'm not able to judge which is best. In the Show tab, the log posts events either individually or in small  batches, whereas in the Scenarios tab it's often 100 or more with intervals of minutes, which tempt the user to suspect the program has hung. I'd put up with a slower run to have the Show behaviour.
Actually, I haven't timed it but subjectively, Show seems to run pretty well as fast as headless.

**Assistant**

Done — the Scenarios tab's **Run** now uses Show's Max pacing. `StartRun` adds `--collapse-polls --step-pause-ms 300` to the runner command; Show's other flags (`--view`, the speed selector, the breakpoint flags) stay Show-only.

Measured on `journal/live-2026-11-06-1107.json` in the real shell, offscreen, 45 steps all passed:

- Log: 41 updates, mostly two lines each (step started and passed in the same tick) every 0.38 s → 81 updates of one line each, median 0.27 s.
- Console: 61 live lines → 39, with no batch larger than four; polls now arrive as `refresh ×50` summaries, while the run's `console.log` still holds every poll.
- The run took about the same wall time, as you suspected.

Verified: `tests/studio-shell-check.py` passes (13/13, run passed), the doc-block checker is clean, and the probe run reports 45 passed. DIFF.md is rewritten; only the four intended files changed.

Two things remain that this does not fix: the 10–13 s browser boot before the first step logs anything (the real "has it hung?" moment), and the `TrimStepsLog` comment that says the trim runs about once a second when it is nearer 25 s. Say if you want either addressed.

## 11:07

It's not necessary to show errors in the title bar as they can occupy many lines and they appear in full in the Log. A warning indicator would however be useful instead.

**Assistant**

Done. The title row now carries a warning indicator rather than the failure text: a red `⚠` when a run fails, empty otherwise. The message stays in the Log, and the indicator's tooltip carries it in full.

I also covered the case where the message was only on the title row: `FinishRun` now appends a run-level failure to the Log in red when no step failure has already written one, so a start-up failure (the browser not connecting, say) is never only on the title. Step failures already logged themselves and are not duplicated.

Verified with a deliberately failing scenario through the real shell: status `run failed · 0 passed · 1 failed`, indicator text `⚠`, tooltip carrying the Playwright message, and the message present in the Log. `tests/studio-shell-check.py` still passes, including "a passing run leaves the title row clear", and the doc-block checker is clean. `README.md`, `docs/SPEC.md` and `docs/PROTOCOL.md` describe the indicator; `DIFF.md` is rewritten.

## 12:09

Running Journal 2026-11-09 in the Scenarios tab completes with no errors. In the Show tab: [two excerpts showing s909 expecting Office 10.1 but finding 10.3, and s975 expecting Sunroom 23.0 but finding 22.4]

**Assistant**

Found it — it was not the pacing, and it could have hit Run too. The page was losing a map when a poll's empty heartbeat landed just after it.

`PulseHeartbeat` tinted the heartbeat dot and then waited 500 ms before `OnMapReceived` read `ReceivedMessage`. That variable is shared: an empty reply arriving inside the window replaced the map, so the handler took it for a heartbeat and never applied it. The room card then stayed one reading behind — 10.3 from `s894` instead of 10.1 from `s908`, and 22.4 from `s931` instead of 23.0 from `s974`.

Reproduced exactly: the full 9 November journal in Show failed at `s909` (908 passed, 1 failed), and a direct probe — a map, then an empty payload 100 ms later — left the card at 13.8 instead of 10.1.

The fix forks the dot's clear, so the payload is read immediately. The forked task ends with `stop`, not `return`: a fork has no call frame, and its `return` popped the caller's, which ended `BuildHomeScreen` early and made demo mode open the About sheet before its chrome existed (the demo spec caught that).

Verified after the fix: the full 1002-step journal in Show passes (1002/1002), the probe shows 10.1, the new `tests/ui/map-vs-heartbeat.spec.js` passes, the whole UI suite is 7/7, the PWA compile check is 12/12, and the doc-block check is clean. `DIFF.md` is rewritten; restart Studio and, if you publish the PWA, rebuild `/heat/`.

## 12:34

My colleague is having trouble setting up RBR to send emails. I'd like a simple Python script to send a test email. The various items needed - server, port, username, password, message, sender etc - should all be supplied as manifest constants at the top of the script.

**Assistant**

Added `rbr-mail-test.py` at the repository root. It is stand-alone — it imports nothing from this repo — so it can be copied to the controller or to your colleague's machine.

Fill in the constants at the top: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM`, `MAIL_TO`, `MAIL_SUBJECT`, `MAIL_BODY` and `SMTP_TIMEOUT`. Port 587 uses STARTTLS and every other port (normally 465) uses implicit TLS — the same rule `rbr_mail.send_files` uses, so a success here means RBR's own sender will work.

It prints the settings before sending (never the password) and names the likely fix on failure: placeholder values, a rejected username/password (app passwords), a sender the provider will not allow, a rejected recipient, TLS on the wrong port, an unknown host or a refused connection.

Verified: it compiles; with the placeholders untouched it exits 1 with `SMTP_SERVER is still the placeholder smtp.example.com`; a filled-in probe produced the expected From/To/Subject/body and, pointed at a refused port, exited 1 with `could not connect to 127.0.0.1:1 … Check the server name, the port…` while never printing the password. It has not sent a real message — that needs the colleague's credentials.

## 13:19

Ensure that in all cases where a row of the table is selected and a run is not active or when run pauses, that the row is brought into view and its values are presented in the Step tab.

**Assistant**

Done. Selecting a row now scrolls it into view and fills the Step tab whenever no run is live, and at a pause. A pause the run makes goes through the same routine, so a marker pause and every Step advance present the finished step.

`StepSelected` now delegates to a new `PresentStep`, which fills `InspectorTitle`, `InspectorSub` and `Inspector` and scrolls the row into view when `Running` is 0 or `Paused` is 1. During a live run the Step tab still follows a selection, but the table does not move — the run owns the view. `PauseRun` calls `PresentStep` after selecting the paused row, so the details are presented even if the programmatic selection signal is missed.

Verified in the real shell, offscreen:
- Selecting row 900 of the 1002-step 9 November journal scrolled to 890/991, left the row visible, and showed `STEP s901` with its detail; selecting row 0 scrolled back and showed `STEP s1`.
- A Show with a Mark marker at `s900` paused with the table at 889 and `STEP s900` in the Step tab; pressing Step moved both to `STEP s901`.
- `tests/studio-shell-check.py` still passes, the doc-block checker is clean, and `git diff --check` is clean.

`README.md`, `docs/SPEC.md` and `DIFF.md` describe the rule.

## 13:34

I just ran import mbox and the log shows [Mbox import: QED6, five "already present" lines, 5 messages/0 saved/5 duplicates] but the SCENARIOS panel is not showing the 2026-11-10 journal. Why is this?

**Assistant**

The 11-10 journal is in your inbox, but the Studio's importer recorded it as **failed** earlier today and will not retry the same archive. The panel is built from the scenario library, not from the inbox, and mbox import only manages the inbox — hence "already present".

The cause is in the bundle: `rbr-2026-11-10.tar.gz` has `"maps": []` and `"baseMapHash": null`. Its journal has no `session.start` and no `plan.snapshot` (the controller had been running since 11-09 and the map did not change that day), so `journal-export.py` had no map hash to copy. `journal_to_scenario.py` needs a base map, failed with `no map snapshot in the journal; pass --map`, and `journal_inbox.py` recorded the archive as failed by its SHA-256 in `inbox-seen.json`; by design a failed archive is skipped on later scans.

Fixed at all three layers:
- `journal-export.py` now copies the last map snapshot from before the day when the day references none, and records it in `manifest.baseMapHash`, so the bundle stands alone.
- `journal_to_scenario.py` uses `baseMapHash` (or a bundled map when there is exactly one) when no event names a map.
- `journal_inbox.py` passes `--map` from the newest earlier full-day bundle when a bundle has no map, and retries a failed "no map snapshot" entry once such a bundle exists. Other failures stay recorded.

I re-ran the scan against your real inbox: 2026-11-10 imported as `journal/journal-2026-11-10-qed6.json` (989 steps, 8 heatlog CSVs) and is in the Journal index. Restart Studio or press Refresh scenarios to see it. Tests: `python3 -m unittest tests/unit/journal_export_test.py` (12 OK) and `python3 tools/rbr-studio/tests/journal_check.py` (17 OK). I also removed a stale `fixtures/local/studio-config-path` pointer left by the shell-check harness, which was pointing Studio at the test config instead of `studio-config.json`. Deploy the updated `journal-export.py` to the controller so future map-less days bundle their base map; the existing 11-10 archive did not need re-exporting.

## 13:56

On the Scenarios tab, make the Log/Wire/Console/Artifacts/Step panel occupy the entire window width and the 4 buttons on the left sit above it.

**Assistant**

Done. The Scenarios tab now has a vertical page: the library/table splitter on top, and the shared log panel below it spanning the page width. The four row-editing buttons (Duplicate…, Duplicate for room…, Rename…, Delete rows) remain at the bottom of the left library column, so they sit directly above the log panel on the left. The Show tab is unchanged: its log still sits under the table beside the viewer.

`studio.allspeak` gained `ScenariosPage`/`ScenariosPageCol`; `LogTabs` is added there instead of `ScenariosRightCol`, and `MainTabChanged` returns it there when Scenarios is selected.

Verified in the real shell, offscreen: the log is 976 px of the 986 px page, and all four buttons measure above its top edge. `tests/studio-shell-check.py` now asserts both, and it passes. `README.md`, `docs/SPEC.md` and `DIFF.md` describe the layout.
