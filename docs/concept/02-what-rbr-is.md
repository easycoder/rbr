# What RBR is

> **Audience:** industry — specifiers, heating contractors, developers, housing providers · **Status:** draft · **Last verified:** 2026-09-20 · **See also:** [The experience is the product](00-the-experience-is-the-product.md) · [Why room by room](01-why-room-by-room.md) · [A fitted house](03-a-fitted-house.md) · [Glossary](../appendix/glossary.md)

## In one sentence

RBR is a control system that heats a house one room at a time: it watches the temperature in every room, decides which rooms want heat now, and opens or closes the radiator in each one accordingly.

## What it is like to use

Mostly, nothing — and that is the intended experience. The house is warm where it should be and cool where it should not, and nobody has had to arrange it.

What a household actually does is small. Each room's times and temperatures are set once, usually with the installer or before the system is delivered. After that, the only things anyone touches are the exceptions: cold in the study this morning, so boost it for an hour; a guest in the spare room, so bring it on; the house empty for a week, so set it back. Each is confined to the room it concerns, and the rest of the house carries on around it.

Profiles cover the shape of the week — a weekday pattern and a weekend pattern, say — with a calendar deciding which applies on which day, so a change of routine is a change in one place rather than in twenty. The interface is a web page that opens in any phone browser; there is nothing to install from a store.

## What it is not

- **Not new heat.** RBR changes the controls, not the plant. The boiler or heat pump, the pipework and the radiators all stay as they are.
- **Not the wider smart home.** Its job is heating. It is not a hub for everything else, and it does not hand the household a box of generic parts and the job of assembling them.
- **Not something the household has to run.** There is no network to administer and no account to keep alive. Once it works, it keeps working.

## Why it feels that way

Four choices, each made at the experience layer rather than the hardware layer.

- **There is nothing to set up on the day.** The devices can be paired and named, and the house's rooms and schedules laid out, before the unit is delivered, so what arrives is an appliance rather than a project. The visit itself is mechanical: fit the devices, wire them, connect the controller to the router.
- **Your Wi-Fi is never involved.** The room devices talk to the controller over their own low-power radio link, so the house needs one connection to its router rather than one for every device. No password changes hands, and replacing the router does not disturb the heating.
- **The hardware is not fixed.** RBR is not tied to one maker or to one arrangement: a room can be served by a thermometer and a relay, or by a valve that senses and switches by itself, and the parts are ordinary trade items from ordinary suppliers rather than bespoke ones. Nothing becomes unobtainable, and the trade that fitted the rest of the system can fit a replacement.
- **Someone can always look at it.** The owner — or, across a housing provider's stock, the provider's own staff — can see and adjust every system from a phone. When something needs attention there is someone equipped to look at it, rather than a household left to work it out.

## When it cannot sense a room

A control system the trade will trust has to fail safely, so it is worth saying what happens when a thermometer goes quiet — a flat device, or a message that does not arrive.

After about three quarters of an hour without a reading, the temperature for that room is treated as out of date. RBR stops calling for heat there and holds the radiator off until a fresh reading arrives, and the app shows the last known temperature, marked as stale. The room cools gently; it does not run the heating without feedback. When the reading returns, so does the room, with no intervention.

## What is underneath

Underneath, RBR is three things working together: the controller and the room devices are in the house, and the app can be anywhere.

**The controller.** A small, inexpensive computer, sitting near the router, that does the thinking. It holds the plan — which rooms exist, what temperature each should reach and when — and roughly once a minute it checks each room against that plan and switches that room's heating on or off. On most installs it is a board no larger than a paperback; where a display is wanted, it can be a small panel instead.

**The room devices.** In each room, something reads the temperature and something opens and closes the radiator. Those can be two devices — a wireless thermometer, and a relay (a small mains switch) driving a powered valve — or one, a valve that senses and switches by itself. Which is used is a choice of hardware, not of system. One further relay sits at the boiler, telling it when any room wants heat, so the boiler is asked to fire only when there is a demand for it.

**The app.** The web page described above: the whole of the household's contact with the system, and the whole of a provider's view of an estate.

## Where next

- [A fitted house](03-a-fitted-house.md) — what the system looks like in a property.
- [Deployment and roles](04-deployment-and-roles.md) — who fits it, who owns it, who supports it.
- [The experience is the product](00-the-experience-is-the-product.md) — why the experience layer is where this is won.
