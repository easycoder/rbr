# Naming and network conventions

> **Audience:** installer and commissioning technician · **Status:** draft · **Last verified:** 2026-09-21 · **See also:** [Prerequisites](01-prerequisites.md) · [Bill of materials](02-bill-of-materials.md) · [Preparing a unit](05-preparing-a-unit.md) · [Glossary](../appendix/glossary.md)

## Why the names matter

A device's name is not a label. It is the only link between the hardware and the plan: the room says it is served by `Kitchen-radiator`, and the bridge commands a device that calls itself `Kitchen-radiator`. Nothing checks that the name refers to something real.

So a mismatch is silent. The relay never switches, or the thermometer reads unknown, and nothing anywhere reports a naming error — it looks exactly like a fault. Names must match character for character, including case. `Kitchen-Radiator` and `Kitchen-radiator` are two different devices as far as the system is concerned, and only one of them exists.

## The convention

`<room>-<device>`, with the room spelled as it is in the plan. It is not enforced by anything; it is simply the habit that keeps a system self-describing and makes a mismatch obvious on sight.

| Device | Name | Example |
|---|---|---|
| The room's temperature sensor | `<room>-thermometer` | `Kitchen-thermometer` |
| A relay driving the radiator | `<room>-radiator` | `Kitchen-radiator` |
| A relay driving a plinth heater | `<room>-plinth` | `Kitchen-plinth` |
| A self-contained valve, where one is used | `<room>-trv` | `Kitchen-trv` |
| The relay on the boiler's demand input | Whatever the plan's `request` field says | `Demand` |

Where a room has more than one of the same kind of device, distinguish them — `Kitchen-radiator-2` — rather than by position, because nobody will remember which was which by the time it needs replacing.

## The demand relay

This is the one name that is not a matter of taste. The relay that switches the boiler must be named exactly as the plan's `request` field, or nothing drives the plant at all. The install guide's convention is `Demand`; where a plan is copied from an existing system, that plan's `request` field wins, and the devices are named to match it rather than the other way round.

## Renaming

Because the name is the link, a rename has to happen in both places or the room stops working. Two cases are worth separating:

- **Renaming a room** does not rename devices. The room's name is for people; the devices keep the names they were paired with. Changing one without the other leaves a room called `Study` being heated by a device called `Office-radiator`, which works but reads badly.
- **Renaming a device** breaks every room that refers to it. It is not a shortcut for reorganising a house: it is a re-pairing exercise, and the plan has to be updated with it.

## A device that is neither a relay nor a thermometer

A self-contained valve does two jobs — it senses the room and it closes the radiator — so it takes a single name rather than two, and `<room>-trv` extends the convention in the obvious way.

How such a device is bound to its room when the system is commissioned is not yet settled, because none has been fitted in a live installation. The convention above is safe to follow in the meantime: it names the device once, and the binding is the part that gets decided when the first one goes in.

## The network

The point of the arrangement below is that the household changes nothing.

**One connection to the router, and it is a cable.** The controller is wired to the household router. Nothing else in the house is on that network, so there is no password to hand over, no per-device connection to make, and replacing the router does not disturb the heating.

**The rooms are on their own radio.** The thermometers and relays talk to the coordinator over a low-power radio network, independent of the household's Wi-Fi. Two consequences are worth stating because they are the usual causes of trouble in a connected home: nothing needs the household's Wi-Fi credentials, and a house full of devices does not put a house full of clients on the router.

**Each installation generates its own radio keys.** The setup creates a fresh network key and network identifier per system, so two installations in neighbouring houses are not on the same network. There is nothing for the installer to invent or record here.

**The radio channel is chosen to sit between the Wi-Fi channels.** The setup puts the Zigbee network on channel 15, one of the three that fall in the gaps between the Wi-Fi channels a household router normally uses. It is the setting to change if a site turns out to share a crowded band — but only after the coordinator's position has been dealt with, which is much the commoner cause of trouble. The coordinator's siting is covered in [Prerequisites](01-prerequisites.md) and, with the reason, in [Bill of materials](02-bill-of-materials.md).

**The mains-powered relays strengthen the network.** A device with a permanent supply typically relays traffic for its neighbours as well as switching, so a house with a relay in most rooms generally needs no extra repeaters. Where links are weak, they can be measured rather than guessed at, and the tools for that are in the installation section.

**What the coordinator is for.** It is the hub of that radio network and nothing else: it does not serve the household's internet, and unplugging it does not affect anything but the heating.

## Where next

- [Preparing a unit](05-preparing-a-unit.md) — where the names are put to work.
- [Bill of materials](02-bill-of-materials.md) — choosing the coordinator this network runs on.
- [Glossary](../appendix/glossary.md) — the terms used across these documents.
