# Room By Room — product documentation

RBR turns the radiators already in a house into a system that heats each room to its own schedule. It uses off-the-shelf hardware and the home network that is already there.

These pages describe RBR as a **product**, for the people who might specify it, fit it, run it or maintain it. For how the software works inside, see the engineering documents in `doc/` and `AI/` — this tree links to them rather than repeating them.

> **Audience:** all · **Status:** draft · **Last verified:** 2026-09-20

## Where to start

Find your role and follow that path. The [glossary](appendix/glossary.md) runs across all of them, and whatever your role, [The experience is the product](concept/00-the-experience-is-the-product.md) is the shortest statement of what RBR is trying to be. These paths are the *intended* reading order — the map further down marks which documents exist so far.

**In the heating trade, or specifying heating** — heating engineer, contractor, specifier, developer, housing provider:

1. [The experience is the product](concept/00-the-experience-is-the-product.md) — what actually decides whether a system is taken up.
2. [Why room by room](concept/01-why-room-by-room.md) — the case, in plain terms.
3. [What RBR is](concept/02-what-rbr-is.md) — the product.
4. [A fitted house](concept/03-a-fitted-house.md) — what it looks like in a property.
5. [Deployment and roles](concept/04-deployment-and-roles.md) — who fits, who owns, who supports.
6. [Costs and payback](concept/05-costs-and-payback.md).
7. [Prerequisites](preparation/01-prerequisites.md) — what a house has to have before a system can be specified.

**Going to fit one** — installer, commissioning technician:

1. [Prerequisites](preparation/01-prerequisites.md)
2. [Bill of materials](preparation/02-bill-of-materials.md)
3. [Naming and network conventions](preparation/03-naming-and-network.md)
4. [Preparing the controller computer](preparation/04-controller-computer.md)
5. [Preparing a unit](preparation/05-preparing-a-unit.md)
6. [Installing the controller](installation/01-installing-the-controller.md)
7. [Pairing devices](installation/02-pairing-devices.md)
8. [Commissioning](installation/03-commissioning.md)
9. [Verification](installation/04-verification.md)
10. [Unattended operation](installation/05-unattended-operation.md)

**Going to run one** — resident, property manager, housing provider:

1. [The interface](operation/01-the-interface.md)
2. [Modes, schedules and profiles](operation/02-modes-schedules-profiles.md)
3. [Managing many systems](operation/03-managing-many-systems.md)
4. [Troubleshooting](operation/04-troubleshooting.md)

**Going to work on it** — developer, maintainer:

1. [Architecture](technical/01-architecture.md)
2. [The map format](technical/02-map-format.md)
3. [Device control and the bridge](technical/03-device-control-and-bridge.md)
4. [Updates and deployment](technical/04-updates-and-deployment.md)
5. [Heating data](technical/05-heating-data.md)
6. [Controller files](technical/06-controller-files.md)
7. [Legacy RBR-Now hardware](technical/07-legacy-rbr-now.md)
8. [Roadmap: current measurement](technical/08-roadmap-current-measurement.md)

## The document map

**Concept — why it exists, and what it is**

| Document | Purpose | Status |
|---|---|---|
| [00-the-experience-is-the-product.md](concept/00-the-experience-is-the-product.md) | Why the experience, not the hardware, is what decides | **Draft** |
| [01-why-room-by-room.md](concept/01-why-room-by-room.md) | The industry case for per-room control | **Draft** |
| [02-what-rbr-is.md](concept/02-what-rbr-is.md) | The product in plain terms | **Draft** |
| [03-a-fitted-house.md](concept/03-a-fitted-house.md) | What it looks like in a property | **Draft** |
| [04-deployment-and-roles.md](concept/04-deployment-and-roles.md) | Who fits it, who owns it, who supports it | **Draft** |
| [05-costs-and-payback.md](concept/05-costs-and-payback.md) | What it costs, and why the saving cannot yet be sized | **Draft** |

**Preparation — before anything is fitted**

| Document | Purpose | Status |
|---|---|---|
| [01-prerequisites.md](preparation/01-prerequisites.md) | The site survey: what the house must already have, and what to settle before ordering | **Draft** |
| [02-bill-of-materials.md](preparation/02-bill-of-materials.md) | Every part by class, with what to check when buying it — and the two routes | **Draft** |
| [03-naming-and-network.md](preparation/03-naming-and-network.md) | The names that are the link to the hardware, and the radio the rooms run on | **Draft** |
| [04-controller-computer.md](preparation/04-controller-computer.md) | The machine: Linux, the runtime, the coordinator, storage and unattended restart | **Draft** |
| [05-preparing-a-unit.md](preparation/05-preparing-a-unit.md) | The pre-delivery build: pairing, naming, the plan, and what to record | **Draft** |

**Installation — fitting and commissioning**

| Document | Purpose | Status |
|---|---|---|
| 01-installing-the-controller.md | Base install on the controller computer | To write (re-cut of `doc/setupRBR.md`) |
| 02-pairing-devices.md | Pairing on site, for devices that arrive unpaired | To write (re-cut) |
| 03-commissioning.md | Wiring rooms to devices in the UI | To write (re-cut) |
| 04-verification.md | Health checks and what "normal" looks like | To write (re-cut) |
| 05-unattended-operation.md | Power-on, services, map backups | To write (re-cut) |

**Operation — living with it**

| Document | Purpose | Status |
|---|---|---|
| 01-the-interface.md | The phone app, adding a system, the home screen | To write |
| 02-modes-schedules-profiles.md | Timed, boost, advance, on, off; profiles and the calendar | To write |
| 03-managing-many-systems.md | Estate administration for a housing provider | To write |
| 04-troubleshooting.md | What to try when something looks wrong | To write |

**Technical — how it works underneath**

| Document | Purpose | Source to harvest |
|---|---|---|
| 01-architecture.md | Components and message flow | `AI/ARCHITECTURE.md` |
| 02-map-format.md | The map file | `AI/MAP_FORMAT.md` |
| 03-device-control-and-bridge.md | Relays, thermometers, the Zigbee bridge | `deviceControl.as`, `zigbee-bridge.py` |
| 04-updates-and-deployment.md | How code reaches a controller | `doc/UPDATE-MECHANISM.md` |
| 05-heating-data.md | The heating log format | `doc/HEATING-DATA.md` |
| 06-controller-files.md | The file manifest | `doc/CONTROLLER-FILES.md` |
| 07-legacy-rbr-now.md | Retired ESP32 hardware | `doc/setupHardware.md`, `doc/configurator.md` |
| 08-roadmap-current-measurement.md | Power-flow monitoring, the next phase | `doc/current-measurement.md` |

**Appendix**

| Document | Purpose | Status |
|---|---|---|
| [glossary.md](appendix/glossary.md) | Every term the reader meets, defined once | **Draft** |
| faq.md | The questions the trade asks first | To write |

## How these documents are written

- **Metadata line.** Every document opens with `> **Audience:** … · **Status:** … · **Last verified:** …`. Status is `draft`, `review` or `stable`.
- **One paragraph, one line.** A prose paragraph is a single unbroken line, however long — never hard-wrapped at a fixed width, and each list item is a single line too. These files are copied into a Doclet structure for viewing, which turns each source line into an HTML paragraph, so a hard-wrapped paragraph would arrive as a column of one-line paragraphs. Headings, tables, blockquotes and code fences keep their own line structure.
- **Four audiences.** Concept (industry), preparation and installation (installer), operation (operator), technical (developer). Keep a document inside one layer and cross-link, rather than blending.
- **Plain words in the concept layer.** The concept documents avoid implementation names — no AllSpeak, no MQTT, no Zigbee2MQTT, no Webson — and define a term once in the [glossary](appendix/glossary.md) rather than assuming it. The preparation and installation documents are for the people doing the work, so they name the tools and commands they ask the reader to use; the rule there is that each tool is explained in a clause when it first appears, so no document depends on the reader already knowing it.
- **One document, one job.** Cross-link; do not duplicate. Where a fact already lives elsewhere in the repository, link to it as the source of truth rather than copying it.
- **Callouts.** Warnings and traps use blockquotes in bold, as in the existing install guide — the naming rule and the dongle-siting note are hard-won and should survive the move intact.
- **British English**, as the rest of the project.

## Relationship to the rest of the repository

| Where | What | Reader |
|---|---|---|
| `docs/` (this tree) | The product, reader-facing | Customers, installers, operators |
| `doc/` | Engineering notes and procedures | Developer |
| `AI/` | Architecture and conventions for AI contributors | AI agents |
| `design/` | UI design language and screenshots | Designer |

This tree links into `doc/` and `AI/` for detail. Those two remain the source of truth for anything they already cover; these pages change the voice, not the facts.

## Status

The concept and preparation layers are complete: [The experience is the product](concept/00-the-experience-is-the-product.md), [Why room by room](concept/01-why-room-by-room.md), [What RBR is](concept/02-what-rbr-is.md), [A fitted house](concept/03-a-fitted-house.md), [Deployment and roles](concept/04-deployment-and-roles.md), [Costs and payback](concept/05-costs-and-payback.md), [Prerequisites](preparation/01-prerequisites.md), [Bill of materials](preparation/02-bill-of-materials.md), [Naming and network conventions](preparation/03-naming-and-network.md), [Preparing the controller computer](preparation/04-controller-computer.md), [Preparing a unit](preparation/05-preparing-a-unit.md) and the [glossary](appendix/glossary.md). The installation, operation and technical layers have agreed titles and a stated source to harvest from. Nothing here has been reviewed yet.
