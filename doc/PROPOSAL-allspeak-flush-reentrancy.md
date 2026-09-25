# Feature request: reentrancy-safe runtime handlers (blocking handlers corrupt program state)

**Status:** PROPOSED — for upstream discussion in the AllSpeak project **Author:** RBR project (Graham) **Date:** 2026-08-31 **Related:** `allspeak/as_program.py` (`Program.flush`), `allspeak/as_keyboard.py` (virtual keyboard — the first real user of a blocking handler), `desktop/rbr_ui.py` (RBR desktop app that surfaced this)

## Summary

A runtime handler that **blocks in a nested event loop** (e.g. the virtual keyboard's modal `dialog.exec()`) lets reentrant `flush()` calls corrupt the shared program state, crashing the suspended caller and — worse — risking a silent continuation from a corrupted program counter.

## Problem

`Program.flush` (as_program.py) drives the program with shared instance state:

```python
def flush(self, pc):
    global queue
    self.pc = pc
    while self.running:
        command = self.code[self.pc]
        ...
        self.pc = handler(command)     # a blocking handler suspends here
```

The virtual keyboard (`Keyboard.__init__` in as_keyboard.py) blocks the caller inside `dialog.exec()` — a nested Qt event loop. While that loop runs, the app's own Qt timers keep firing (graphics flush timer, `wait` continuations, MQTT callbacks), each draining the shared queue via a **reentrant** `Program.flush()` on the same instance. Every reentrant flush overwrites `self.pc`, and its natural-end path can also clear the shared `self.running`:

```python
elif self.pc == None or self.pc == 0 or self.pc >= len(self.code):
    if len(queue) == 0:
        self.running = False
    break
```

When the modal loop finally returns, the suspended outer flush resumes with `self.pc` clobbered. Any handler that reads it — `nextPC()` does `self.program.pc + 1` — either crashes or, if the corrupted value happens to look valid, silently continues from the wrong program counter.

## Observed impact

RBR desktop app (Python runtime, version 2608311041): tapping an input sheet (System name / Request relay / Add Room) pops the virtual keyboard; clicking the tick to accept crashed the caller:

```
File ".../rbr_ui.py", line 489, in r_show
    return self.nextPC()
File ".../as_handler.py", line 64, in nextPC
    return self.program.pc + 1
TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'
```

The app currently works around it by capturing `self.program.pc` before the blocking call and restoring it afterwards — but the underlying hazard remains for any handler that blocks (dialogs, pickers, file dialogs, future modal widgets), and the silent-corruption path is undiagnosed.

## Requested change

Make `Program.flush` reentrancy-safe. Two options, in increasing scope:

### Option A (minimal, recommended): save/restore flush state around handlers

Nested flushes must not be able to clobber an outer flush's `pc`/`running`. Preserve and restore the loop state around each handler invocation (or keep a per-flush stack):

```python
while self.running:
    command = self.code[self.pc]
    ...
    saved_pc, saved_running = self.pc, self.running
    self.pc = handler(command)
    # a nested flush may have run inside a blocking handler; restore ours
    self.pc, self.running = saved_pc, saved_running
```

The natural-end branch should likewise only clear `running` when the flush that reached the end is the *outermost* one.

### Option B (cleaner long-term): non-blocking handlers

Support handlers that suspend the program without a nested event loop — e.g. a `wait until <widget closes>` / completion-callback pattern for the keyboard (show non-modally, resume the program when the dialog closes). This removes the reentrancy entirely, but is a larger API design change.

## Scope / non-goals

- Fixing the crash and the silent-corruption hazard only; no change to the keyboard's look or behaviour.
- The keyboard-width/legend proposal (PROPOSAL-allspeak-keyboard-sizing.md) is independent.

## Verification (suggested)

- Open a sheet with an input, type, accept and cancel the keyboard repeatedly while the app is live-updating (MQTT map pushes, refresh timers firing underneath) — no errors, no skipped statements.
- A stress repro: a handler that blocks while a rapid timer queues continuations; confirm the outer flush resumes at the correct pc every time.
