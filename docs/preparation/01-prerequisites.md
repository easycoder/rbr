# Prerequisites

> **Audience:** installer and commissioning technician — and anyone specifying a system · **Status:** draft · **Last verified:** 2026-09-21 · **See also:** [Bill of materials](02-bill-of-materials.md) · [Naming and network conventions](03-naming-and-network.md) · [Glossary](../appendix/glossary.md)

## Before anything is ordered

Four things have to be true of a house before a system can be specified for it.

**A heating system to control.** RBR controls the emitters and asks the boiler for heat; it replaces neither. The house needs its radiators — or plinth heaters, or whatever warms its rooms — and a boiler or heat pump that can be told that heat is wanted. Where the existing controls already provide a demand or interlock input, that is where the demand relay connects; where there is no such input, that is a question to settle before the system is specified rather than during the visit.

**Power where it is needed.** The controller is a mains device, and so is a relay that switches an emitter — but what a room needs depends on the hardware chosen for it. Served the split way, with a wireless thermometer and a relay switching a powered valve, a room needs a supply at the radiator; served by a valve that senses and switches by itself, it needs no cabling at all, which is the arrangement for a household unwilling to have cables run. That second route has not yet been fitted in a live installation. Which rooms use which is a question for the survey; the provision each device requires is set out in the [bill of materials](02-bill-of-materials.md).

**A router, and a way to reach it.** The controller is normally connected to the household router by cable, so the survey is looking for a spare port and a route for the cable. That connection is also why the household's Wi-Fi credentials are never needed and nothing about the router's configuration has to change.

**A place for the controller, and radio reach from it.** The controller sits near the router, on mains, and its radio lead should be kept clear of metalwork. A dongle pressed against a case, a bracket or a shelf can degrade every link in the network at once, and it shows up as relays that intermittently fail to switch rather than as anything obviously wrong with the radio. On one installation, moving the dongle off a steel bracket doubled the coordinator's link quality to every device and took failed relay commands from thousands a day to virtually none. The survey is looking for a spot that is both convenient and clear.

## What has to be decided before the unit is prepared

A unit is paired, named and configured before it is delivered, so these have to be settled in advance rather than on the day.

- **The room names, and how many rooms there are.** A room-by-room system needs the count in any case, so naming the rooms is the natural next step; the names are what the devices are called and what the plan is built from. This is the only thing the household has to supply.
- **Which rooms have more than one heat emitter**, so that each is switched in its own right.
- **Which rooms are not heated** — a cupboard, a landing — so that they stay out of the plan.
- **Where the controller will live**, and whether a display is wanted rather than a bare board.
- **Who will operate it**: the household, or a provider's staff, and whether the household should have a view of their own home at all.

## What is not needed

- No new boiler, no new radiators and no re-piping of the circuit. The controls change; the plant does not.
- No smart-home hub, no account per device, and nothing added to the household's Wi-Fi.
- No change to the broadband service, and no change to the router's settings.
- No technical knowledge from the household. They supply the room names, and nothing else.

## The survey list

| Check | Why it matters |
|---|---|
| The heating works, and the boiler or heat pump can be told that heat is wanted | RBR asks for heat; it cannot make the plant answer |
| A mains supply where the controller will sit | The controller is a mains device |
| A mains supply at each point where a relay is to be fitted | Relays are mains devices; a room served by a self-contained valve needs no supply |
| A spare router port, and a cable route to the controller's position | The controller is normally cabled to the router |
| A spot for the controller that is clear of metalwork | Radio reach to every room |
| Access to each radiator that is to be controlled | The valve there is driven by the system |
| The room names, and the number of rooms | The devices are named after them, and the plan is built from them |

## Where next

- [Bill of materials](02-bill-of-materials.md) — the parts the survey implies.
- [Naming and network conventions](03-naming-and-network.md) — the names that must not be got wrong.
- [Glossary](../appendix/glossary.md) — the terms used across these documents.
