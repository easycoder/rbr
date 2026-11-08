# Events and the journal

> **Audience:** anyone using RBR Studio, and anyone who wants to understand what the controller records · **Status:** draft · **Last verified:** 2026-11-08 · **See also:** [Architecture](01-architecture.md) · [Glossary](../appendix/glossary.md)

## What this guide is for

Room By Room does not only make decisions; it remembers making them. When someone touches the app, when a thermometer reports, and when a schedule reaches a boundary, the controller writes a short record of what happened to a diary it keeps on its own disk. That diary is the **event journal**.

The journal exists for three reasons. It lets a day be replayed and questioned rather than guessed at; it gives RBR Studio real behaviour to build a test from; and it keeps a clear line between what was **asked for** and what the system **did**, which is the difference that matters when a room is cold and nobody agrees why.

The heating log is a different record. It samples each room's target, actual temperature and mode whenever they change. The journal keeps the requests, readings and decisions that produced those samples, which is why a day can be replayed from it rather than reconstructed from its outcomes.

This guide describes the three streams of events, how each reaches the controller, what is written down, and how those records become the rows of an RBR Studio scenario. It assumes you know what the app does and what the rooms, schedules and modes are for. It does not assume any knowledge of the code, the file format or programming.

## The words used here

Most of the vocabulary is already the app's. A few words are used in a particular way in this guide.

| Word | What it means here |
|---|---|
| **Event** | Something the controller noticed or did that is worth keeping: a request, a reading, a change in a room, a restart. |
| **Journal** | The controller's own record of events, kept as one file per local day. |
| **App**, **interface**, **UI** | The phone page. It shows the plan and sends actions. It is a view, not the record. |
| **Controller** | The computer in the house that holds the plan and decides, room by room, whether heat is wanted. |
| **Plan** | The whole stored arrangement: the rooms and their devices, the profiles and schedules, the calendar, the system name and the demand relay. The software and RBR Studio also call it the **map**; this guide says plan, and means the same thing. |
| **Snapshot** | A copy of the whole plan at one moment. |
| **Period** | One start-and-stop stretch in a room's schedule, with a target temperature. |
| **Profile** | A named set of schedules for the whole house, such as Weekday or Weekend. |
| **Mode** | What a room is doing now: Off, On, Timed or Boost. Advance is a separate control that shifts a Timed room to its schedule's next change. |
| **Demand relay** | The relay that tells the boiler or heat pump that at least one room wants heat. |
| **Room state** | The part of a room that the app shows and the controller continuously updates: its mode, target, period, advance, relay, health and status words. |

## The shape of the diary

The journal is deliberately simple. Each event is one line, and all the events for one local day share one file. A line records:

- **what kind of event it was** — a request from the app, a thermometer reading, a change in a room, a restart, and so on;
- **when it happened**, by the controller's clock, in local time;
- **where it belongs** — the room and, where relevant, the device or the person's session;
- **what changed**, in the terms the app itself uses;
- **its place in the order**, so two events that share a timestamp can still be told apart.

The order is carried by two things: a counter that rises through the session, and a marker for the controller's start-up. The counter says which event came first; the start-up marker says when the controller was restarted. A deliberate restart is marked by a closing and an opening line; a crash or a kill is not, so a gap in the record is a real gap rather than a quiet period.

The plan itself is not copied into every line. When an event refers to the plan, the journal stores a snapshot once and points at it from the line. Identical snapshots share one copy, so a day in which nothing structural changed does not carry a hundred copies of the same plan.

The journal is written in small batches. The controller holds a few events in memory and appends them together, at least once a minute and immediately after a request from the app. If the controller is killed before a batch is written, those events are lost: the journal does not replay a half-written batch. That is a deliberate trade for keeping the order of lines exact and the cost of writing low. A silence in the journal is therefore worth treating as a real silence.

On a normal installation the journal is on. If the helper that writes it is missing, the controller says so at start-up and carries on without it rather than failing.

### The kinds of event

These are the kinds currently written. The names are the software's own; the right-hand column is what they mean in plain terms.

| Kind | Written when | What it means |
|---|---|---|
| `session.start` | The controller has started and completed its first control pass. | The session began. It carries the version, the system name, the active profile, where the journal lives, and a snapshot of the plan. |
| `session.stop` | The controller is about to restart for an update. | The session ended on purpose. It says why. |
| `day.rollover` | The local date changes. | The controller has moved from one heating day to the next. |
| `profile.change` | The active profile changes, whether the calendar chose it or someone selected it in the app. | The house is now running a different set of schedules. |
| `ui.first` | An app asks for its first copy of the plan. | Someone opened the app, or a page reconnected. It names the client. |
| `ui.request` | A request from the app reaches the controller. | Someone asked for something. The line keeps the whole request and the gesture that produced it. |
| `sensor.reading` | A thermometer's reading changes, or the same value arrives with a new device timestamp. | A room's thermometer reported. |
| `room.state` | Any part of a room's control or status state changes. | The workhorse: a mode, target, period, advance, relay or health change. |
| `plan.snapshot` | A request that changed the plan has been applied. | The plan has been edited, and here is the new copy. |
| `request.relay` | The demand relay's own state changes. | The boiler or heat pump has been asked for heat, or told it is no longer needed. |

`room.state` is the one to understand first. It is not a separate event for every concept. A period starting, an advance ending, a boost expiring, a relay switching and a sensor going stale are all `room.state` lines. What distinguishes them is **which fields changed**, which is exactly what the Action columns in RBR Studio are designed to show.

The ten-second heartbeat that the app sends to prove it is still connected is deliberately **not** recorded. Nor is every pass through the controller's five-second loop. The journal records changes and requests, not the passage of time.

## The three streams

There are three directions from which an event can reach the journal, and they take different routes.

| Stream | Starts at | Reaches the controller through | Main record |
|---|---|---|---|
| **A person using the app** | A phone or browser | The cloud message hub, then the house message hub | `ui.request`, followed by `room.state` or `plan.snapshot` |
| **A thermometer** | A room | Radio to the coordinator, then the Zigbee software, then the Zigbee bridge | `sensor.reading` |
| **The controller itself** | Its own clock and logic | Nothing external; it compares what it finds with what it found last time | `room.state`, `profile.change`, `day.rollover`, `request.relay` |

The message hubs are the post offices. The app and the controller do not speak directly; each leaves a message at a hub and the other collects it. The house has its own hub so the heating keeps working when the internet does not; the cloud hub exists so a phone outside the house can reach in. [Architecture](01-architecture.md) describes the arrangement in full.

## When a person touches the app

### How the request leaves the phone

When the app opens, it asks the controller for the plan and receives a full copy. It then sends a quiet refresh every ten seconds. That refresh is a heartbeat as much as a request for news: any answer proves the round trip is alive. Neither the opening nor the heartbeat changes anything, and only the opening is recorded, as `ui.first`.

When someone taps a control, the app does two things in a deliberate order. It changes its **own copy** of the plan immediately, so the screen responds at once, and it sends a request to the controller. The app is therefore showing an optimistic guess until the controller's next full copy arrives. If the guess and the controller disagree, the controller's copy wins and the screen corrects itself.

Because the page moves first, an RBR Studio scenario often checks twice around one tap: that the card changed at once, and that it still says the same thing after the controller's full copy arrives. The first check follows the UI row; the second follows a controller row that represents the controller's acknowledgement.

The request carries more than the action. It carries the room and the values involved, and a small **gesture fingerprint** describing where the request came from:

- the **screen** it was made on — the home screen, a sheet, the profiles list, the devices list and so on;
- the **control** that was used — an advance button, a mode pill, a target stepper, a schedule save;
- the **gesture** — usually a tap, sometimes a selection or a typed value;
- the **room**, where one is involved.

The fingerprint matters because the same action can come from several places. An `Operating Mode` request may be an Advance button, a mode pill, a boost duration or a target change; an `Update Profiles` request may be a schedule save, a profile rename, a calendar change or a device edit. The action alone does not say which, and the gesture does. If an older page does not supply a fingerprint, the controller records the request without one.

### What happens when it arrives

The controller receives the request, notes which client sent it, and writes `ui.request` **before** it applies anything. It then checks that it recognises the action and the room. If it does, it applies the change to its working copy of the plan, saves the plan if the change belongs in the plan, and pushes a complete copy to every connected app.

A request that cannot be understood or cannot find its room is refused. The request is still in the journal, because it arrived; what is missing is any change after it. The reason for the refusal goes to the controller's terminal log, not to the journal, so the journal can tell you **that** nothing happened but not always **why**.

Some requests are deliberately repeatable. Advance, for example, is sent as a desired state — "I want Advance on" or "I want Advance off" — rather than "flip it". A retried or duplicated request therefore cannot flip the wrong way. The journal may show the same request twice; that is a retry, not a second intention.

### What is written about the request and the response

| Record | What it proves |
|---|---|
| `ui.request` | The controller received a request. It keeps the whole message — including the action the page asked for, the room, the values, the gesture fingerprint and the client. |
| `room.state`, with fields that differ from the previous line | The controller applied the request and now reports a different state for the room. |
| `plan.snapshot` | The request changed the stored plan, and this is the plan as it stood immediately afterwards. |
| `request.relay` | The boiler demand changed as a consequence. |
| Nothing after the `ui.request` | The request was refused, changed nothing visible, or did something the journal does not record, such as starting an export. |

There is no separate "reply sent" record. The controller's answer to the app is a fresh copy of the plan; the journal records the **state that copy was built from**, not the act of sending it. For a request that changes a room or the plan, a `room.state` or `plan.snapshot` line is the evidence that it took effect; an isolated `ui.request` with nothing after it is evidence that it changed nothing the journal records.

A request is a question. A `room.state` line is the controller's answer, or its own decision. When you see a state change and want to know whether a person caused it, look immediately before it for a request from the same client, for the same room, with a fingerprint that matches the change.

### An example

A person presses **Advance** on the Kitchen card. The journal would show, in order:

1. `ui.request` — action `Operating Mode`, room Kitchen, advance `A`, fingerprint `screen: home`, `control: advance`, `gesture: tap`.
2. `room.state` — room Kitchen, advance `A`, with an end time, and the target and relay moved to the schedule's next change. Inside a period with a gap after it, that means the heating stops now, because the next change is the end of the current period.
3. Later, at the deadline or when the natural period rolls, `room.state` — advance `-`, with the room at its natural state.

The first line is the question. The second is the answer. The third is the controller acting on its own, with no request before it.

## When a thermometer reports

### How a reading reaches the controller

A battery thermometer spends most of its time asleep. It wakes on a heartbeat — roughly hourly, and sooner if the temperature moves enough to be worth reporting — and sends its reading over the Zigbee radio to the coordinator, the small radio dongle plugged into the controller computer.

The Zigbee software on the controller — the program that runs the radio — receives the reading and publishes it on the house message hub under the device's friendly name, the name it was given when it was paired. The Zigbee bridge, a separate small program, is listening there. It keeps the latest reading for every device it has seen and writes the set of them to a small file in the controller's fast, in-memory working area. Once a minute the controller reads that file and merges the readings into its own record. The room logic itself runs more often, roughly every five seconds, but it decides against the most recent merged reading.

The distinction matters when a reading is late. The controller does not poll the thermometer; it waits for the bridge's cache to change. A reading that never reached the bridge is invisible to the controller and to the journal, however loudly the thermometer may have shouted.

### What is recorded

A `sensor.reading` line records the room, the sensor's friendly name, the temperature, the device's own timestamp, and — when the device supplies them — humidity and battery. The temperature is stored in hundredths of a degree; the app displays it to one decimal place.

A repeated temperature is kept when it arrives with a new device timestamp. That is not noise: it is the evidence that the thermometer is alive and reporting on its heartbeat, which is what lets a stale-reading problem be told apart from a thermometer that has failed. An identical line with the same timestamp, humidity and battery is dropped, so the journal does not fill with copies of one report.

The reading is an **input**. What the controller decided to do about it is recorded separately, as a `room.state` change: the relay going on or off, the status moving to `warn` or `fail`, and the status message that explains why.

### What happens when a reading is missing

A reading older than about forty-five minutes is treated as missing. The room keeps its last known temperature so the app can show it, marked as stale, but the controller stops treating it as current and holds the relay off rather than heating without feedback. After about an hour the room's status becomes `fail`.

There is one deliberate exception. In the first thirty minutes of a scheduled period, the controller may use the last known reading to start the heat, because a period that begins between two hourly reports would otherwise be lost. The reading is still reported as stale and the status still changes; only the heating decision uses the older value, and only until the thirty minutes are up.

All of this appears in the journal as ordinary `room.state` changes. There is no special "sensor went stale" event. The status field moving to `warn`, and the status message saying how long it has been, are the record.

## When the controller acts on its own

### The rhythm

Roughly every five seconds the controller examines every room. It asks four questions. What mode is this room in? What temperature is it aiming for? Is the current reading fresh enough to decide on? And should the relay be on? A change in the control or status part of a room is written as a `room.state` line; a change in the reading itself is a `sensor.reading`. A steady room writes nothing, which is why a quiet room produces a quiet journal.

### Schedule periods and boundaries

A room in Timed mode follows its schedule. The controller works out which period contains the current time, and sets the target from that period. When the clock crosses a boundary, the period and target change, and one `room.state` line records the new period and target. A period ending and the room falling back to the background temperature looks the same: a change of period, target and often relay.

There is no separate "period started" event. The transition **is** the event. If you want to know why a room began heating at 07:00, the line to find is the `room.state` at 07:00 with a new period and target.

### Mode changes

A mode change made in the app arrives as a request and leaves as a `room.state` line, as described above. A change the controller makes by itself — a boost expiring, an advance reaching its deadline — has the request line missing and only the state line present. That absence is the simplest way to tell a person's action from the controller's own.

The journal distinguishes Timed, On, Off and Boost as modes. The app offers Advance as an extra control rather than a separate schedule; in the journal it is a flag on a Timed room, which stays in Timed mode while its target is shifted to the schedule's next change.

### Advance

Advance moves a room to the schedule's next change. From outside a period, that change is the next period starting, so the room moves to that period's target now. From inside a period, the next change is normally the end of that period, so the target becomes the background temperature now and the heating stops; the room does not wait for the end to arrive. If another period begins exactly where the current one ends — back-to-back periods — the next change is that period starting, so the room moves into it now, at its target.

In plain terms, Advance makes the next thing that was going to happen happen now, whether that is a period starting or a period ending.

When Advance is engaged, the `room.state` line carries the advance flag and an **end time**: the instant of the schedule change it is aiming at. That end time is stored with the plan, not only in memory, so a controller that restarts still has a deadline to cancel on. At the deadline, or when the natural schedule rolls first, the controller clears the flag and sets the room to the natural state for that moment. A second `room.state` line records that. In the gap case the room has been at the background target since the tap, so the second line may change nothing except the advance flag; in the back-to-back case the room has been heating to the joined period's target and stays there.

### Boost

Boost runs a room at a fixed target for a set length of time, then returns it to whatever it was doing before. The `room.state` line records the boost target, the end time, and the previous mode, so the return is not a guess. Boost ends at its time, or when the natural schedule period rolls over, whichever comes first. The line that follows records the return.

### The day and the profile

At local midnight the controller writes `day.rollover`, naming the day that ended and the day that began. If the calendar selects a different profile for the new day, a `profile.change` line follows, naming the profile it came from and the one it moved to. A person selecting a profile in the app produces the same `profile.change` line, preceded by the `ui.request` that asked for it.

These are two different facts and are kept as two lines. The date changing is not the same as the schedule changing, even when one causes the other.

### Relays, demand and health

Each room's relay decision appears in its `room.state` line as `on` or `off`. The demand relay — the one that asks the boiler or heat pump for heat — is recorded separately as `request.relay`, with its name and state, and only when its state changes. That separation is useful: a room's own relay can be off while the demand relay is on because another room is calling for heat, and the two facts are recorded in different places.

Health is recorded in the same `room.state` line. `status` moves between good, warn, fail and partial; `statusMessage` explains a stale sensor or a relay that has stopped answering; `relayMessage` names a failed relay when one of several has stopped answering. These are the fields that turn "the room was cold" into "the room was cold because its thermometer had not reported for an hour".

### Telling one kind of change from another

Because `room.state` covers so much, it helps to know which field to look for.

| What you want to know | Look for |
|---|---|
| Did the schedule move the room? | A change of `period` and `target`, usually at a round time. |
| Did a person change the mode? | A `ui.request` immediately before a `room.state` whose `mode` changed. |
| Is Advance on? | `advance` is `A`, with an `advanceuntil` end time. |
| Did Advance end? | `advance` returns to `-`; `target` is the natural schedule's target for that moment, which may be the same value it held during the advance. |
| Is Boost running? | `mode` is `boost`, with an `until` end time and a `prevmode`. |
| Did the room call for heat? | `relay` is `on`. |
| Did the boiler get asked? | A `request.relay` line, separately. |
| Is a sensor stale? | `status` is `warn` or `fail`, and `statusMessage` says how long. |
| Did a relay fail? | `relaysFailed` is above zero, `relayMessage` names it, and `status` may be `partial`. |

## Reading a day as a story

The journal is read in order, not by timestamp alone. Two events can share a timestamp; the sequence number says which came first. A deliberate restart is visible as a `session.stop`, a new `session.start`, and a new start-up marker; a crash has the new start-up marker and the new session, but no closing line.

A short worked example, with the plan already running:

| Time | Record | What it tells you |
|---|---|---|
| 06:59 | `session.start` | The controller has started. The plan and active profile are in the snapshot attached to this line. |
| 07:00 | `sensor.reading` — Kitchen 18.9 | The thermometer reported. Its own timestamp is a little before the controller's, which is normal. |
| 07:00 | `room.state` — Kitchen, period 0, target 21.0, relay on | The morning period has begun and the room is calling for heat. |
| 07:03 | `ui.request` — Operating Mode, Kitchen, advance A, home/advance/tap | Someone pressed Advance on the Kitchen card. |
| 07:03 | `room.state` — Kitchen, advance A, advanceuntil 08:00, period -1, target 15.0, relay off | The next change is the end of the 07:00 period, so the heating stops now. `period -1` means no period is active; 15.0 is the background temperature. |
| 07:03 | `request.relay` — Demand, off | If Kitchen was the last room calling for heat, the boiler demand goes off with it. |
| 08:00 | `room.state` — Kitchen, advance -, period -1, target 15.0, relay off | The deadline passed and the advance cleared. Nothing else changed, because the room was already at the background state. |
| 17:30 | `room.state` — Kitchen, period 1, target 21.0, relay on | The evening period begins naturally, and the room returns to its scheduled target. |

The 07:03 line is the one that matters for Advance. If a period had begun at 08:00 exactly where the 07:00 period ended, the same line would have shown that period's number and target, and the relay would have stayed on. The advance would still have cleared at 08:00, when the new period became the natural one.

The story reads as a conversation. The request is a question. The state line after it is the answer. The state lines without a request are the controller thinking for itself. The demand relay line is a consequence that belongs to the house rather than to one room.

Two cautions are worth keeping.

The first is that **near in time is not the same as caused by**. A `room.state` change a second after a request may be the request taking effect, or it may be the schedule boundary that happened to arrive at the same moment. The fingerprint and the changed fields usually settle it; when they do not, the honest answer is that the journal does not prove causation, only sequence.

The second is that the journal records the controller's **belief**, not the world. A relay reported as on may be stuck; a thermometer reported as alive may be in a warm cupboard. The journal is the best account of what the system thought, and that is exactly what is needed to explain a decision, but it is not a physical measurement of the radiator.

## From journal to RBR Studio

RBR Studio turns a day of the journal into a **scenario**: a list of things the controller did, things a person did, and things the page must show. The scenario runs against the real page in a browser, with a virtual clock, so an eight-hour day costs seconds and needs no broker or controller.

A scenario is laid out as rows. The columns are `#`, `Mark`, `Time`, `Actor`, `Target`, the short Action columns, `Expectation` and `Result`.

### Actors

The **Actor** column says what kind of row this is: who or what is doing something, or what is being checked.

| Actor | What the row does |
|---|---|
| **Controller** | Changes the plan or a room's state and pushes a full copy to the page, as the real controller would. |
| **UI** | Drives the page: taps, selects, fills or scrolls a named target. |
| **Expect** | Checks what the page shows. |
| **Wire** | Checks what the page sent, without needing the controller to answer. |
| **Delay** | Holds the current picture for a moment in a paced demonstration; it does not advance the scenario's clock. |
| **Connection** | Drops, restores or reports an error on the page's connection. |

A controller row is the Studio's stand-in for a `room.state`, a `sensor.reading` or a plan change. A UI row is the Studio's stand-in for a person, and is the one thing the journal cannot supply.

### Targets

A **Target** is a stable name for the thing being acted on or checked. It is not a screen coordinate and not a button identifier. `room.Office.advance` means the Advance control on the Office card; `room.Office.temp` means the temperature shown there; `summary.outside` means the outdoor temperature in the summary. Names are resolved against the plan the run is using, so reordering the rooms cannot silently point a scenario at the wrong card.

A scenario also keeps a short alias for each room, so a room can be renamed in one place rather than in every row. The Target uses the alias; the plan supplies the real name at run time.

Some common targets:

| Target | The thing it names |
|---|---|
| `room.Office.temp` | The temperature on the Office card. |
| `room.Office.subline` | The secondary line on the card, where an active advance is shown. |
| `room.Office.advance` | The Advance control. |
| `room.Office.rest` | The collapsed part of the card, used to open it. |
| `summary.outside` | The outdoor temperature in the summary. |
| `schedule.period.0.temp` | The target temperature of the first period in the schedule sheet. |

The exact catalogue is larger, and includes sheets, profiles, devices and the menu. A raw screen selector is available as a last resort, but it is marked as fragile because it ties the scenario to the page's current structure.

### The Action columns

The Action columns are short: **S**, **M**, **T**, **H**, **B**, **P**, **A** and **R**. They show the state a controller row carries. They can be switched on and off with the **Columns…** chooser; the default shows **S, M, T** and **R**.

| Column | Meaning | Values you will see |
|---|---|---|
| **S** | Status | A coloured dot for the room's status — green for good, amber for warn, red for fail. Blank when the row does not mention it. |
| **M** | Mode | `T` Timed, `A` Advance, `B` Boost, `O` On, `X` Off. |
| **T** | Temperature | The room's reported temperature, not its target. |
| **H** | Humidity | A percentage, where the thermometer supplies it. |
| **B** | Battery | The thermometer's battery level. |
| **P** | Period | The number of the scheduled period that is running; `-1` means none. |
| **A** | Advance | `A` when engaged, `-` when not. |
| **R** | Relay | A filled circle for on, an open circle for off. |

A blank cell means **this row does not say anything about that field**, not that the value is zero or off. A controller row shows the fields it is changing; the rest of the room's state is carried by the plan and by earlier rows. The full names appear in the column chooser and in each cell's tooltip.

On a journal-generated scenario, a room in Advance usually shows `T` in the Mode column and `A` in the Advance column, because the controller keeps the mode Timed and records Advance as a flag. The `A` value in the Mode column is for maps that name Advance as a mode.

For a UI row, the short columns are empty and the action is carried by the Target: tapping `room.Office.advance` is the action. The Inspector repeats it in words. For an expectation row, the check is in the Expectation column and the short columns are empty.

### Expectations

The **Expectation** column says what a check requires, and **Result** says whether it passed. An expectation is always an explicit row. A controller event does not silently imply one, because a check that is invisible is a check nobody can correct.

The common checks are:

| Expectation | What it requires |
|---|---|
| `contains` | The target's text contains the given words or value. |
| `text` | The target's text is exactly the given value. |
| `notContains` | The target's text does not contain the given value. |
| `visible` / `hidden` | The target is, or is not, on the screen. |
| `value` | A form field holds the given value. |
| `count` | The expected number of matching elements is present. |
| `match` (on a Wire row) | The page sent a request whose named fields match. |
| `any` (on a Wire row) | The page sent the named request, with any contents. |

A Wire row checks the message the page sent, so it can confirm a gesture before the controller has answered. An Expect row checks what a person would see. Both are useful, and they answer different questions. The gesture fingerprint in the journal and the message a Wire row checks are the same outbound request, so a scenario can assert the request independently of the answer it receives.

The **Mark** column is a single marker in the scenario. In a paced demonstration, everything before the marker runs at full speed and everything from the marker onwards runs at the chosen pace, so the interesting part is the part you watch.

### How a journal day becomes a scenario

The converter that turns a day into a scenario does not invent controller behaviour. It reads the recorded events and writes rows.

In the table below, a room is **visible** when the page draws it as a room card on the home screen. The outdoor thermometer is normally the exception: it appears in the summary rather than as a card, so its readings are checked there rather than on a room card, and its state changes produce no card expectation.

| Journal record | What becomes of it |
|---|---|
| `sensor.reading` | A controller row carrying the temperature, humidity and battery. Where the room is visible, an expectation that the card shows the new value. |
| `room.state` | A controller row carrying the fields that changed. When the advance flag changes, an expectation about the card's secondary line, where the room is visible and not already showing a warning. |
| `ui.request` | Not replayed as a tap. The converter counts these and says so in the scenario's description; their effects are already visible in the `room.state` and `plan.snapshot` records. |
| `plan.snapshot` inside the window | Warned about, not replayed. A structural edit needs a plan from that moment, and the generated scenario uses the plan at the window's start. |
| `profile.change` | Warned about, not replayed as an active-profile change. |
| `session.start`, `session.stop`, `day.rollover`, `request.relay` | Context. They are not turned into rows. |
| The state immediately before the window | Seeded as a set of controller rows at the window's start, so the page begins where the journal's story began. |

Repeated sensor readings with unchanged values are dropped, and duplicate room states are dropped, because the page does not need to be told the same thing twice. Two converter options change that: one keeps every sensor reading, and one keeps status-message-only changes.

The generated description records what the converter did and what it could not replay. That text is part of the scenario, not decoration: it is the difference between a test that reproduces a day and a test that only looks as if it does.

A generated scenario is good for seeing what the real page did with a real day's plan and transitions. If the controller recorded a state and the page did not show it, the failure is real and worth investigating. It is not a way to prove that a person pressed a button, because the controller saw the request, not the thumb. And it is not a controller simulator: the runner changes the plan as a row tells it to, rather than deciding for itself when a period should begin.

## The limits, honestly

- **It is the controller's view.** Every line describes what the controller believed or decided. It cannot tell you that a valve was stuck, only that the controller believed it was open.
- **It does not record the radio.** A thermometer's raw messages, a relay's acknowledgement and the Zigbee network's own troubles are outside the journal. A missing reading is evidence that nothing arrived; it is not by itself evidence that the thermometer is at fault.
- **It does not record the screen.** The request's fingerprint says which control and gesture produced it, not what the page looked like or what the person saw.
- **Absence is meaningful, but ambiguous.** A request with no state change after it was refused or had no effect. The reason is in the controller's terminal log, not the journal.
- **Time is the controller's clock.** Each line carries a local timestamp and the offset in force at that moment. A daylight-saving change is visible as a change of offset, not as a gap in the schedule.
- **A gap can be a real gap.** A killed controller loses the batch it had not yet written. The journal does not reconstruct it.
- **It is private.** It contains room names, device identifiers, schedules, occupancy patterns and the exact requests people sent. It should stay on the installation unless there is a reason to move it, and the daily email export is opt-in for that reason.
- **It is finite.** The journal keeps itself under a size cap and a share of free disk space, deleting the oldest complete days first. If a longer history matters, archive the daily exports rather than expecting the live journal to keep everything.

## Where to look next

The engineering detail — the exact fields, the file layout, the retention rules, the export and import tools — is in `doc/EVENT-JOURNAL.md`. The parts and the message flows are in [Architecture](01-architecture.md). RBR Studio's own README and specification describe the scenario format, the target catalogue and the runner; they live with the Studio, under `tools/rbr-studio/`. The outcomes that the journal produced — the heating log — are described in `doc/HEATING-DATA.md`.

The [glossary](../appendix/glossary.md) defines the product's terms once. This page defines only the words that the journal and the Studio use in their own way.
