# Glossary

> **Audience:** all · **Status:** draft · **Last verified:** 2026-09-20

Terms are defined once, here. Where a term belongs to a deeper layer, the entry says so rather than expanding it — follow the link for detail. Heating terms are given only where RBR means something more specific than the trade does.

## The system

| Term | Meaning |
|---|---|
| **RBR** | "Room By Room" — the software system these documents describe. |
| **System** | One installed, RBR-controlled home, as seen in the app. You add a system to the app with its address and password, and a single account can hold several. |
| **Controller** | The small Linux computer in the home that runs the RBR software. It decides, room by room, whether heat is wanted, and switches the relays accordingly. Also called the *master controller*. |
| **Controller computer** | The physical machine the controller runs on. Any small Linux box will serve; an industrial touchscreen panel is one option, a fanless mini-PC another. |
| **The app** / **the interface** / **UI** | The RBR app: a web page that runs in any smartphone browser, reached at `rbrheating.com/ui`. Used both to commission a system and to operate it. |
| **Room** | One heated space, with its own thermometer, one or more heating devices, its own schedule and its own mode. |

## Devices and wiring

| Term | Meaning |
|---|---|
| **Thermometer** | The wireless temperature sensor for a room. Reports on a slow heartbeat (roughly hourly, or sooner if the temperature moves). It may be a separate device, or built into the room's radiator valve. |
| **Relay** | The mains switching unit that turns one heating device on and off — a radiator's valve, or a plinth heater. A room can have several. Where a room uses a self-contained valve instead, it has no relay. |
| **Radiator valve actuator** | The motorised head that opens and closes a radiator, and is what actually lets hot water into it. Either powered, driven by one of the relays, or self-contained and battery-powered with its own sensor. |
| **Demand relay** | The relay that switches the boiler or heat pump's *demand* input, telling the plant that at least one room wants heat. Exactly one name — conventionally `Demand` — must be used for it, or nothing drives the plant. |
| **Friendly name** | The human name given to a device when it is first joined to the system, such as `Kitchen-radiator`. It must match, character for character, what is entered later, or the device will never be commanded. |
| **Pairing** | The one-off act of joining a wireless device to the controller's coordinator. |
| **Commissioning** | The setup step: pairing the devices (usually done before the unit is delivered), naming them, and binding each room to its sensor and its heating devices, so the system runs as intended. |

## Radio, network and messaging

| Term | Meaning |
|---|---|
| **Zigbee** | The low-power radio standard used by the thermometers and relays. Consumer hardware, bought off the shelf. |
| **Coordinator** | The Zigbee dongle plugged into the controller computer. Every device in the home talks to it, and it is the one point that must be sited well — clear of metal, ideally on a short extension lead. |
| **Zigbee2MQTT** | The software on the controller that runs the Zigbee network and publishes each device on the internal message bus. It has its own web page, used during pairing only. *See the technical layer.* |
| **MQTT** | The lightweight messaging protocol the controller and the app use to talk to each other. *See the technical layer.* |
| **Broker** | The server that carries MQTT messages. A local one lives on the controller; it is bridged to a cloud one so the phone can reach the system from anywhere. *See the technical layer.* |
| **Router** | The home broadband router the controller plugs into. The system uses the network that is already there and needs no changes to it. |
| **MAC address** | The hardware identifier used to name a controller (and so a system) when you add it to the app. Printed on the machine and recorded at setup. |

## Operating modes and scheduling

| Term | Meaning |
|---|---|
| **Mode** | What a room is doing right now. One of **Off**, **On**, **Timed**, **Boost** or **Advance**. |
| **Off** | The room's valve is held shut; no heat is wanted there. |
| **On** | Heat to a fixed target, held until changed — for a room you want warm regardless of schedule. |
| **Timed** | Heat follows the room's schedule: the target temperature for the current time of day. The normal setting. |
| **Boost** | Ignores the schedule and aims at a fixed target for a set length of time, then reverts. For "warm this room now". |
| **Advance** | Brings the room's *next* scheduled period forward to now; it cancels itself when that period would have ended anyway. |
| **Schedule** | A room's list of times and target temperatures. |
| **Profile** | A named set of schedules for the whole house — for example Weekday and Weekend — with an optional calendar that says which profile applies to each day. |

## People and roles

| Term | Meaning |
|---|---|
| **Supplier** | Prepares and supplies a unit: pairs and names the devices, binds each to its room, builds the plan and its schedules, and records the controller's address — all before delivery. Often the same business as the installer. |
| **Installer** | Fits and wires the hardware in the home: controller, thermometers, relays, valves; connects the controller to the router. |
| **Commissioning technician** | Brings the system up and checks it does what was intended: that each room reads, the relays switch and the boiler answers. Often the same person as the installer. |
| **Operator** / **manager** | Runs the heating day to day, in the app. May be the resident, or a member of a housing provider's staff. |
| **Resident** | Lives in the home. May never touch the app at all. |
| **Developer** / **maintainer** | Works on the RBR software itself. *See the technical layer.* |

## Things that look like faults but are not

| Term | Meaning |
|---|---|
| **Stale reading** | When a thermometer has not reported for about 45 minutes, its reading counts as missing. The room's relay is deliberately held off until a fresh reading arrives — a room cools gently rather than heating without feedback — and the app shows the last known value with a soft warning until it clears. |
| **Undelivered commands** | A count of commands a device has not acknowledged. A small non-zero figure is a diagnostic, not necessarily a fault; a *relay that stops acknowledging* usually needs a power-cycle. |
