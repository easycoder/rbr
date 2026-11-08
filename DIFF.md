# What to do

- **Restart RBR Studio.**
- The **Columns** window no longer shows the explanatory prompt, and its checkboxes now appear consistently; **Apply** applies the selection and closes the window, while **Close** closes it.
- The **System** selector now loads `studio-config.json` even when a stale test pointer is present or missing its target. QED6 should appear in the dropdown.
- **No controller or PWA release is needed.**

# What changed

- **Columns window.** The checkboxes and the persistent Apply/Close buttons live in one window created at startup. Opening the chooser no longer rebuilds the window or its buttons, so the blank-window and dead-button failures are gone. The explanatory prompt was removed.
- **Config fallback.** `fixtures/local/studio-config-path` is only used when its target file exists; otherwise the Studio falls back to `studio-config.json`. The stale test pointer was removed.
- **Busy feedback.** `LoadScenario` sets the status line to `Working…` before rebuilding the table. AllSpeak has no cursor/busy command, so the requested hourglass needs the new feature recorded in `REQUESTS.md` (`set the cursor of Win to wait`, or equivalent). The status text is the current workaround.
- **Tests.** The Studio shell check passes, including the config-isolation assertion.

# Try it

```bash
cd tools/rbr-studio
QT_QPA_PLATFORM=offscreen python3 tests/studio-shell-check.py
```

The shell check passes, and `git diff --check` is clean.
