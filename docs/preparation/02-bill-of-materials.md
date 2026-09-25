# Bill of materials

> **Audience:** installer, commissioning technician, and anyone ordering a system · **Status:** draft · **Last verified:** 2026-09-21 · **See also:** [Prerequisites](01-prerequisites.md) · [Naming and network conventions](03-naming-and-network.md) · [Glossary](../appendix/glossary.md)

## What this list is

RBR is bought as a set of commodity parts rather than as a kit from one maker — as the interface itself puts it, "works with off-the-shelf relays, TRVs and thermometers; build the system exactly as you want it". So this document describes each part by what it has to do and what to check when buying it, rather than naming models. That keeps it true as suppliers change, lets an installer buy locally, and means a household can replace a single part years later without going back to the original supplier.

Everything below comes in two routes, and they are priced differently. More on that at the end.

## The controller

A small, always-on Linux computer that holds the plan and does the thinking. It has no performance requirement worth speaking of — it is a scheduler, not a solver.

A mini-PC is the straightforward choice, and now the inexpensive one: a low-end model does everything asked of it, and comes with the storage, the enclosure, the power supply and the firmware the requirements below name. Check the requirements either way.

What to check when buying:

- A wired network port, since the controller is normally cabled to the router.
- A spare USB port for the coordinator, which can be given up permanently.
- Low power and fanless, because it runs all the time.
- **Solid-state storage that is not a microSD card.** This is the one reliability choice worth being firm about. The controller writes continuously — the plan when it changes, the heating records as they are logged, the readings as they arrive — and cards wear out under that; a failure takes the whole system down and can leave the plan unreadable mid-write. An SSD, or a board with built-in storage, is materially more dependable. Where a card is unavoidable it should be a high-endurance one, the plan should be backed up regardless, and volatile data should be kept off it altogether — [Preparing the controller computer](04-controller-computer.md) covers how.
- A mains supply, and firmware that can be set to come back on after a power cut. Without that, nothing in the operating system can recover the machine on its own.
- An enclosure, if a bare board is used rather than one that comes cased.
- A display only if one is wanted. The interface runs in a browser on any device, so a screen on the controller is a convenience rather than a requirement.

## The coordinator

The radio that every room device talks to. A USB coordinator supported by the Zigbee software on the controller, on a **USB extension lead** so it can be moved clear of the case and of any metalwork. Two things narrow the choice considerably. The setup writes the Ember driver, so a coordinator from that family is the path of least resistance; anything else means changing one line of the radio configuration and checking that the device is supported. And the setup creates a stable device name only for the coordinator it expects — a Silicon Labs CP210x device at USB `10c4:ea60`. Any other coordinator still works, but is pinned to whichever serial device it happens to be given, which can change between reboots; [Preparing the controller computer](04-controller-computer.md) explains what that costs and how to fix it.

> **Keep it clear of metal.** A coordinator pressed against a case, a bracket or a shelf can degrade every link in the mesh at once, which presents as relays that intermittently fail to switch rather than as anything obviously wrong with the radio. On one installation, moving it off a steel bracket doubled the link quality to every device and took failed relay commands from thousands a day to virtually none. The extension lead is not optional in practice.

## Room temperature sensors

One per heated room, wireless and battery-powered. What to check:

- It reports when the temperature moves as well as on a slow heartbeat. Many such sensors report roughly hourly, which the system tolerates — it treats a reading older than about three quarters of an hour as missing — but only because the reading also changes when the room does. A sensor that reports only on a fixed long interval and never on change is the wrong part.
- It reports its battery level, so a flat sensor can be anticipated rather than discovered, and it takes a cell you can buy locally. The reporting interval chosen in the software is the main thing under your control that affects how long the cells last.
- It is mounted where the room's temperature is actually represented: not in a draught, not in direct sun, and not directly above a radiator.

One of these is not needed where the room's valve senses for itself; see the two routes below.

## Relays

Mains-rated wireless switching modules. One per heat emitter, plus one for the boiler's demand input. What to check:

- Rated for what it switches. That is a small load for a thermo-electric actuator, and a larger one for a plinth heater.
- It acknowledges commands and reports its state, because the diagnostics are built on that.

> **Mains relays can wedge.** The device stays on the network and reports its state, but ignores commands, so it looks healthy while never switching. A re-power has cleared it every time so far. The per-device count of undelivered commands is how it shows up.

## Radiator actuators

This is where the two routes differ, and the choice is a household's rather than a technical one.

**The split route.** A thermo-electric actuator head that a relay powers. Check that it fits the valve body, that it works at the relay's output, and that the trade fitting it is happy with the arrangement.

**The self-contained route.** A battery-powered thermostatic head that senses the room and closes the valve itself, with no relay and no cabling at the radiator. This is the arrangement for a household that will not have cables run. It has not yet been fitted in a live installation. Three things to allow for:

- **It measures at the radiator**, where the reading commonly runs a degree or two high, so a room may settle slightly cooler than the target unless an offset or a separate sensor is used.
- **The head has to fit the valve body**, which is the subject of the next section.
- **The batteries have to be serviced.** Most of these heads take replaceable cells and are quoted at about a heating season on good alkalines, with some makers claiming two years or more; an aggressive reporting interval can cut that to months. Take the specified chemistry seriously, because most makers specify 1.5 V alkaline and warn against ordinary rechargeable cells — these deliver a lower voltage, and the valve misbehaves rather than simply running down. A head with a built-in rechargeable battery charged over USB does exist, and is the neatest answer to the problem, but it is unusual: the best-known example is Wi-Fi rather than Zigbee, and the mainstream Zigbee heads are all cell-powered. So this route buys freedom from cabling at the price of a round of batteries, once a year or so.

## The valve body underneath

Both routes need a head that matches the valve body already on the radiator, and here there is genuine standardisation to rely on. **M30 × 1.5 mm** is the connection almost every smart head uses, with an 11.5 mm pin under EN 215, and most modern UK and European valve bodies take such a head directly.

The exceptions are the older and vendor-specific fittings, where an adapter is needed. The Danfoss family is the commonest and the most confusing, because the sizes differ between RA and the two flavours of RAV and RAVL; Caleffi, Giacomini, M28 fittings, Oventrop and Vaillant each have their own. Where no adapter matches, the valve body itself is replaced with a standard one. Measure the valve rather than assuming, and check window-sill clearance, because a smart head is larger than the manual one it replaces.

## What is not bought

The controller's software is not a purchase: it is a bootstrap pack fetched during installation, along with a runtime taken from the package index. It is listed here only so that nothing is missed when ordering. [Installing the controller](../installation/01-installing-the-controller.md) covers it.

## The two routes, priced differently

| Part | Split route | Self-contained route |
|---|---|---|
| Controller | One | One |
| Coordinator and extension lead | One | One |
| Room temperature sensors | One per heated room | None — each valve senses its own room |
| Relays | One per heat emitter, plus the demand relay | Only the demand relay |
| Radiator heads | A powered actuator per radiator | A battery head per radiator |
| Wiring at the radiators | A supply at each | None |
| Boiler demand relay | One | One |

So the self-contained route removes the relays, the room sensors and all the cabling at the radiators, and puts the money into the heads instead. Which is cheaper depends on the house and on what a cable to each radiator would cost to run — and for a household set against trailing cables, the question does not arise.

## Where next

- [Naming and network conventions](03-naming-and-network.md) — the names that must not be got wrong.
- [Prerequisites](01-prerequisites.md) — the survey this list is ordered against.
- [Glossary](../appendix/glossary.md) — the terms used across these documents.
