# 2026-11-08

## 11:10

For my own benefit and for that of anyone who may use RBR Studio, we need a plain English layman's guide to RBR events and how they are recorded in the journal. I would expect this to include 
Events arising in the UI - how they make their way to the controller, what happens when they arrive and what is recorded about them and the response to them.
Events from thermometers - where they arrive, how they find their way into the controller and how they are recorded in the journal.
Events arising from the controller itself - mode changes, advance, boost and period boundaries.
The description should not require any familiarity with the program code. It should avoid technical concepts, assuming the user to be intelligent and able to understand the features of the system but not to have any knowledge of how it's built. Detail is good as long as it stays at the level of understanding events and message flows. I would expect to find within it adequate coverage of what is meant by Actors, Targets, the Actions columns and Expectations.
The document will eventually find its place in the overall documentation stack.

**Assistant**

Added `docs/technical/07-events-and-the-journal.md`, a plain-English guide written for RBR Studio users and anyone trying to understand a recorded day.

It covers:

- the three streams — app, thermometers, controller — with the route each takes and what the journal keeps;
- the UI request lifecycle: the optimistic page change, the gesture fingerprint, arrival, validation, application, map push, and the `ui.request` → `room.state`/`plan.snapshot` record pair;
- thermometers: coordinator → Zigbee software → bridge cache → controller once a minute, `sensor.reading`, repeated readings and staleness;
- controller events: period boundaries, Advance (including its stored deadline), Boost, day rollover, profile change, relays, demand relay and health;
- how to read a day in sequence, with a worked example, and the limits (the controller's view, no radio, no screen, gaps, privacy);
- the Studio vocabulary: Actors, Targets, the S/M/T/H/B/P/A/R Action columns, Expectations and Result, and how a journal day becomes a scenario — including what is not replayed and why.

Also added the page to `docs/README.md`'s technical reading path and document map, and noted it in `TODO-docs.md`. `DIFF.md` is rewritten.

I put it in the technical layer as `07-events-and-the-journal.md`; if you later want it elsewhere, it is a rename plus one README line. No code changed. `git diff --check` is clean and the local links resolve.

## 15:31

There may be a mistake in 'Reading a day as a story", or it has highlighted a bug. When Advance is called for, the system moves to the start of the next period, or if the periods are not contiguous, to the end of the current period. Is that actually what the system does? In the example given, if the 7:00 period ends at 8:00 and is not immediately followed by another period, the relay should go off at 7:03, when the advance is requested.

**Assistant**

You've found a mistake in the guide, not a bug in the controller. You're right about the behaviour.

`ApplyPeriodsAdvance` shifts to the schedule's next change. From inside a running period that is normally that period's end, so the target becomes the background temperature and the relay goes off immediately; from background it moves to the next period's target; and if the next period starts exactly where the current one ends, it joins that period instead. The unit test names the cases: `advance with a gap after stays at background`, `in a back-to-back pair the deadline is the joined period's end`, and `with a gap the deadline is the running period's end`.

In the 07:00–08:00 example with a gap after 08:00, Advance at 07:03 therefore gives:

- 07:03: advance A, advanceuntil 08:00, period -1, target 15.0, relay off (and the demand relay off if this was the last room).
- 08:00: advance -, with the room already at the background state.

I've corrected the worked example and the imprecise line in the UI example, and added the back-to-back case explicitly. The Advance section now says that pressing it inside a period moves to that period's end now, rather than waiting for it.

`allspeak --test tests/unit/unit-04-periods.allspeak` passes 12/12. `git diff --check` is clean. `DIFF.md` is updated.

(The Studio's `advance-at-15-00` example is not the gap case: its Office schedule runs 14:00–18:00 and then 18:00–22:00, so Advance joins the next period rather than ending the current one.)

## 15:44

A small point: There's no need to mention the "old single, wordy Action" column
What is meant by a room being visible?

**Assistant**

Both done.

- Removed the reference to the old wordy Action column. The section now opens with the columns themselves: **S**, **M**, **T**, **H**, **B**, **P**, **A** and **R**.
- Defined **visible** where the converter first uses it: a room is visible when the page draws it as a room card on the home screen. The outdoor thermometer is normally the exception — it appears in the summary, so its readings are checked there and its state changes produce no card expectation.

`git diff --check` is clean; `DIFF.md` is updated. No code changed.
