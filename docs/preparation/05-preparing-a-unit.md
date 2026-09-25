# Preparing a unit

> **Audience:** installer, commissioning technician, and whoever prepares a unit · **Status:** draft · **Last verified:** 2026-09-21 · **See also:** [Prerequisites](01-prerequisites.md) · [Naming and network conventions](03-naming-and-network.md) · [Preparing the controller computer](04-controller-computer.md) · [Glossary](../appendix/glossary.md)

## What this stage is for

Everything the system has to be *told* is done here, before the unit goes anywhere near a house. What arrives on site is then a set of parts and a working appliance: the visit is fitting, wiring and a final check, with nothing left to decide in somebody's hallway.

This works because the two halves of the system are separable. The devices are joined to the controller's radio network, and that network's key and identity are generated for the installation and live with the controller — so a device paired here stays paired when it is later fitted in the room it was named for. Moving a device does not disturb the network; only moving it to a different network would.

## What has to be settled first

None of this can start without answers from the household, which is why they are gathered at the survey (see [Prerequisites](01-prerequisites.md)):

- the room names, and how many rooms there are;
- which rooms have more than one heat emitter, and which are not heated at all;
- whether any room is to be served by a self-contained valve rather than by a relay;
- who will operate the system, and whether the household is to have a view of its own home.

## Pairing and naming the devices

Devices are joined one at a time through the Zigbee software's own web page, which the controller serves on port 8080. Put it into pairing mode, power on a single device, and give the device its name as it appears — one name per device, following [the convention](03-naming-and-network.md).

Two habits keep this reliable. Do one device at a time, because a device that joins while you are naming another is a device you will mis-name. And name it the moment it joins rather than leaving unnamed devices to be sorted out afterwards.

The name given here is the name the plan will use, and nothing checks the two against each other. That is why the convention earns its keep, and why it is worth reading the list back before the unit is packed.

## Building the plan

The plan is the controller's description of the house: a room for each room, with its temperature sensor, its heating devices and its schedule, plus the profiles that cover the week and the calendar that decides which applies when.

Wire each room to the sensor and relays by the names just created, and set the demand relay on whichever room carries it — remembering that its name has to be exactly what the plan's `request` field says. Then the schedules: the times and temperatures each room is to hold. Where the household has said when each room is used, that goes in now. Where it has not, a sensible pattern is quicker to correct later than to invent on the doorstep.

## Recording what the household will need

Two things have to leave here written down, because the household cannot use the system without them: the controller's address, and its password. Those are the pair of values entered when the house is added to the interface, and recovering them later means going back to the machine.

Worth keeping alongside them: the room names as built, and any device whose name does not follow the convention — because that is the list somebody will want when a part is replaced in three years.

## What is left for the site visit

Deliberately little.

- Fit and wire the valves, relays and temperature sensors.
- Connect the controller to the router.
- Confirm that each room reads, each relay switches, and the boiler answers.

Those steps, and the checks that go with them, are in the installation section. Where a device cannot be paired in advance — a replacement, or a device that arrives after the unit — pairing on site is covered there as well.

## A pre-delivery checklist

| Check | Why it matters |
|---|---|
| Every device paired and named | A device left unnamed is a room that will not work |
| Names match the convention, character for character | The plan refers to devices by name, and nothing verifies it |
| The demand relay named as the plan's `request` field says | Otherwise nothing drives the boiler |
| Every room wired to its sensor and its devices | A room with no sensor is a room held off |
| A schedule set for every room | A room with no schedule has nothing to follow |
| The controller's address and password recorded | The household cannot add the house without them |
| Room names, and any devices named off-convention, recorded | For whoever replaces a part in three years |

## Where next

- [Preparing the controller computer](04-controller-computer.md) — the machine this unit is built on.
- [Naming and network conventions](03-naming-and-network.md) — the names used throughout this stage.
- [Glossary](../appendix/glossary.md) — the terms used across these documents.
