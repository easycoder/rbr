# Documentation — where the programme stands

A working note, not product documentation. **Where each document stands is in [docs/README.md](docs/README.md)**: its document map carries a status for every page, its role paths give the reading order, and its Status section names what is written. This file holds what that map cannot — the order of work, the two items waiting on the world rather than on us, and the conventions the work has settled on.

> **Audience:** maintainer · **Status:** working note · **Last verified:** 2026-10-16

## State

The sprint's whole output landed in **one commit on 25 September** (`2fe0416`): thirteen documents — `docs/README.md`, the [glossary](docs/appendix/glossary.md), concept 00–05 and preparation 01–05. Every one reads `Status: draft`, `Last verified:` 20–21 September, and the README's "Nothing here has been reviewed yet" is still true: nothing in the tree has been reviewed by anyone.

A one-line change to `docs/README.md` on 27 September was the tree's last touch. **One commit has happened since** — `f59906e` on 15 October — and it carried two unrelated things: the Advance fix (controller, new-ui, unit tests, version bump) and 188 lines of new audience-facing documentation about the setup script, which was written at the repository root as `RBR-SETUP.md` and linked from nothing. It now lives in the tree, at [docs/installation/06-what-the-setup-script-does.md](docs/installation/06-what-the-setup-script-does.md), and the map lists it.

**The reader is live.** <https://rbrheating.com/docs> serves `docs-reader/index.html`, `docs-reader/docs.json` and `docs-reader/docs.allspeak` byte-identical to the working tree. **Nothing is committed**: `docs-reader/`, `tests/docs-reader-check.js` and `conversation/conversation-011.md` are untracked, and nine files are modified. The site is running from a working tree that a `git clean` would empty. That is the first thing to do, and it is not a documentation decision.

## What is left

**1. Commit the reader.** `git add docs-reader tests/docs-reader-check.js` and the nine modified files (`AGENT.md`, `ALLSPEAK.md`, `DIFF.md`, `deploy.sh`, `.github/workflows/deploy.yml`, `package.json`, `doc/CONTROLLER-FILES.md`, `doc/UPDATE-MECHANISM.md`, `server.allspeak`). `DIFF.md` says what each of them was for.

**2. Installation — four documents left, sources ready.** `01-installing-the-controller` is the re-cut of `doc/setupRBR.md` (11 KB, unchanged since 27 September); `02-pairing-devices`, `03-commissioning`, `04-verification` and `05-unattended-operation` are re-cuts too. This is the layer a customer actually walks, and [06](docs/installation/06-what-the-setup-script-does.md) is already written — it is the script's own reference and sits beside `01`, which is the sequence. If it reads better as the second half of `01`, or as `02` with the rest renumbered, that is a one-line change to the map and the file name; nothing links to the installation pages except the map and two preparation documents, and those point only at `01`.

**3. Technical — eight documents, harvest only.** Every source the map names still exists and has not moved since 27 September: `AI/ARCHITECTURE.md`, `AI/MAP_FORMAT.md`, `deviceControl.allspeak` + `zigbee-bridge.py`, `doc/UPDATE-MECHANISM.md`, `doc/HEATING-DATA.md`, `doc/CONTROLLER-FILES.md`, `doc/setupHardware.md` + `doc/configurator.md`, `doc/current-measurement.md`. Nothing in this layer has to be invented: read a source, change the voice, cross-link.

**4. Operation — four documents, and the only layer with no source.** `01-the-interface`, `02-modes-schedules-profiles`, `03-managing-many-systems` and `04-troubleshooting` have to be written from the product's behaviour, not harvested. This is also the layer most readers need — residents, property managers, housing providers — so it is worth doing properly rather than last in a rush.

**5. Appendix — `faq.md`.** "The questions the trade asks first." Small, no source, and best written after installation and operation exist, because that is where the questions will come from.

The order is deliberate: sources first, from the outside in, and authoring last.

## Waiting on the world

**The battery TRV trial — expected in the next few days.** Two things the documents state as intent are not yet proven on a live installation: the self-contained valve that senses and switches with no cabling at the radiator, and pre-pairing before delivery. The claim about the valve sits in five written places — [concept 00](docs/concept/00-the-experience-is-the-product.md) (*A common platform, and the competition it invites*), [concept 02](docs/concept/02-what-rbr-is.md) (*The room devices*, and the *hardware is not fixed* bullet), [concept 03](docs/concept/03-a-fitted-house.md) (the valve bullet under *Where the equipment goes*), the [glossary](docs/appendix/glossary.md) (Thermometer, Relay, Radiator valve actuator) and [preparation 01](docs/preparation/01-prerequisites.md) (*Power where it is needed*, which carries the tree's only explicit marker — "That second route has not yet been fitted in a live installation" — written to be struck rather than left to age).

**The questions the trial answers, and what each one changes.** These are the reason to write anything down on the day: every one lands in a document, and two of them may land in code as well.

- **Who sets the temperature — the valve, or RBR?** If RBR commands the valve's setpoint, the room behaves like any other and the mode-and-schedule logic applies unchanged. If the valve runs its own schedule and RBR only reads it, then "a choice of hardware, not of system" ([concept 02](docs/concept/02-what-rbr-is.md)) needs qualifying wherever it appears, and [concept 00](docs/concept/00-the-experience-is-the-product.md)'s "the system supplies the layer above the parts" needs the same care. → `concept/00`, `concept/02`, and all of `operation/02`.
- **Is a thermometer still needed in the room?** [concept 03](docs/concept/03-a-fitted-house.md) and the [glossary](docs/appendix/glossary.md) both allow the sensor to be built into the valve, which would make it one device per room rather than two. → `concept/03`, the glossary's Thermometer entry, and `preparation/02`, whose bill of materials lists devices by class and would list one fewer per room.
- **What has to be entered to commission the room?** `doc/setupRBR.md` step 10 sets *Relay type* and switches on *Sensor controls relay*, and lists the room's relays one per line — none of which applies to a valve that has no relay. → a second route through commissioning in `installation/03`, and `doc/setupRBR.md` itself, which is the engineering source.
- **What is it called?** The naming convention is `<room>-<device>` (`Kitchen-radiator`, `Kitchen-thermometer`), and a self-contained valve is neither. → `preparation/03`.
- **Does the survey row for the mains supply change?** [preparation 01](docs/preparation/01-prerequisites.md) says a room served this way needs no cabling at all, which is what the marker is standing in for. → strike the marker, correct the survey row, and settle the buying criteria for both arrangements in `preparation/02`.
- **Does anything in the code or the app assume a relay per room?** A room with no relay already exists in the map — the outside thermometer lives in that slot — which suggests the shape is supported; the device editor and the controller's per-room logic are what the trial actually tests. → possibly `deviceControl.allspeak` and the new UI, and then whatever documents describe them.

**Standing instruction from the sprint:** if the trial throws up problems, fix the code and the documentation in the same pass.

**The current-measurement phase.** The design and this installation's own facts are settled and recorded: four CT clamps as two two-channel bidirectional meters (grid, solar, heat pump, store), 80 A, a 10-second cadence, a `meters.json` the feature is off without, a `meters.as` module with a four-line controller footprint, a staleness rule that reads `unknown` rather than 0 W, the `zigbee-bridge.py` whitelist gap, and the shipping lists to update. It wants `technical/08-roadmap-current-measurement.md` when that layer is written, and `doc/current-measurement.md` is the source.

## Conventions settled

- **A link that leaves the docs tree is named, not linked.** `docs/installation/06` refers to `doc/setupRBR.md`, `doc/UPDATE-MECHANISM.md` and so on in backticks rather than as links. The reader on the site refuses to render a link that climbs out of the tree — it says so rather than fetching something that is not product documentation — and a reader who does not live in repositories should not be sent to one. This applies most to the technical layer, where every document harvests from `doc/` or `AI/`.
- **The map is the only place a page's status is recorded.** Adding a document means adding it to `docs/README.md`; that is what puts it on the site, because the reader builds its page list from the README's own lists and tables. Nothing in this file repeats a status.
- **The map's numbers are promises.** A written document links to `installation/01-installing-the-controller.md` by that name, so renumbering a layer is a deliberate change, not a tidy-up.

## Checked, and no action needed

- **The Advance change of 11 October did not invalidate anything written.** The glossary's line — "Brings the room's *next* scheduled period forward to now; it cancels itself when that period would have ended anyway" — survives the settled semantics. The settled rule (shift to the schedule's *next change*, joining a back-to-back period rather than dropping to background) still has to be *stated* in `operation/02`, which is unwritten: a note for that work, not a defect.
- **The map is accurate.** The eighteen documents it lists as missing are exactly the eighteen that do not exist, and no source it names has gone away.
