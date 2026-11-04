# Architecture

> **Audience:** developer, maintainer — and anyone who wants the outline · **Status:** draft · **Last verified:** 2026-10-25 · **See also:** [Glossary](../appendix/glossary.md) · [What RBR is](../concept/02-what-rbr-is.md) · [A fitted house](../concept/03-a-fitted-house.md) · [What the setup script does](../installation/06-what-the-setup-script-does.md)

## What this is

This is the system in outline: the parts, where each one runs, and the path a temperature reading and a tap on a phone take through them. It is written to be read straight through, and it assumes no knowledge of the code; the engineering detail is in the repository notes named at the end.

The detail most often asked about is the number of message brokers, so that is stated first: **one installation uses two brokers, one in the house and one shared in the cloud**. The section **How many brokers?** below explains what each one is for, and why a second installation does not double the count.

## The parts

| Part | Where it runs | What it does |
|---|---|---|
| **Room devices** | In each room | A thermometer reads the temperature. A relay switches a powered radiator valve or a plinth heater; a self-contained valve senses and switches by itself and needs no relay. One further relay, the demand relay, switches the boiler or heat pump's demand input. |
| **Coordinator** | A USB dongle on the controller computer | The hub of the Zigbee radio network. Every room device talks to it, and it is the one part whose position matters — clear of metalwork, ideally on a short extension lead. |
| **Zigbee2MQTT** | The controller computer | Owns the radio: it pairs devices, receives their readings, and publishes each device's state on the local message bus. It also accepts commands. Its own web page, on port 8080, is used for pairing only. |
| **Local broker** | The controller computer (Mosquitto) | The message hub in the house, on port 1883. Zigbee2MQTT, the Zigbee bridge and the controller all connect to it. It deliberately has no WebSocket listener. |
| **Zigbee bridge** | The controller computer (`zigbee-bridge.py`) | Subscribes to the Zigbee topics on the local broker, keeps the latest reading for each device, and offers the controller a small HTTP interface on `127.0.0.1:8889`. It turns the controller's relay and valve commands into messages for Zigbee2MQTT. |
| **Controller** | The controller computer (`controller.allspeak`, with `deviceControl.allspeak`) | The decision-maker. It holds the map (rooms, devices, profiles and schedules) and re-examines every room every few seconds: which mode it is in, what temperature it should reach, and whether its heating should be on. It also answers the app and publishes the map. |
| **Cloud broker** | RBR's server | One broker, at one address, that every installation and every app is pointed at. It is what lets a phone reach a system that sits behind an ordinary home router. |
| **The app** | Any phone browser | A static web page served from `rbrheating.com/heat/`. It shows the map and sends actions; the copy it holds is a working copy, not the record. |

The two brokers are connected, and the connection is what makes the whole arrangement work without opening anything in the household's router. It is described next.

## Two things called a bridge

The word is used for two different parts, and they are worth keeping apart.

- **The cloud bridge** is part of the local broker. It is a connection configured in Mosquitto, from the local broker to the cloud broker, and it mirrors messages between them.
- **The Zigbee bridge** is a separate program (`zigbee-bridge.py`) that translates between the controller's HTTP requests and the Zigbee topics on the local broker.

In this document, *cloud bridge* and *Zigbee bridge* mean those two, and a bare *bridge* is avoided.

## How many brokers?

One installation uses **two brokers**.

| Broker | Where it runs | Ports | Who connects to it |
|---|---|---|---|
| **Local** | The controller computer, as Mosquitto | 1883, plain MQTT, open on the local network without authentication by design | Zigbee2MQTT, the Zigbee bridge and the controller |
| **Cloud** | RBR's server, at `rbrheating.duckdns.org` | 8883 for MQTT over TLS, used by each installation's cloud bridge; 443 for the app's WebSocket | Every installation's cloud bridge, and every phone running the app |

The local broker is **per installation**. The cloud broker is **shared**: it is one address that every system is pointed at, and the systems are kept apart by their topics rather than by having a broker each. The app's credentials are not public: `credentials.php` hands them out only to a device that presents the system's address and the token issued when it was paired.

So a second installation adds a second local broker and no second cloud broker: two houses use three brokers between them, not four. In a standard installation the controller does not talk to the cloud broker directly: it publishes and subscribes on the local broker, and the cloud bridge carries its topics outward.

> **The local broker is open on the local network.** Port 1883 accepts unauthenticated connections from the house's network by design, because nothing on the other side of the router needs to reach it directly. That is worth firewalling on a network you do not trust; [What the setup script does](../installation/06-what-the-setup-script-does.md) says the same and explains why there is no local WebSocket listener.

## Identity, topics and messages

A system is identified by the controller's MAC address. `rbr-setup.sh` records it in `.mac_override`, and that is the value the app asks for when a system is added. The same value is the system's namespace on the message bus, so one shared broker can carry every installation's traffic without the systems colliding.

The conversation is small and has only a few moves:

- The controller subscribes to the topic named by its MAC address, such as `00:e0:27:5b:31:40`.
- Each app instance makes its own reply topic, `00:e0:27:5b:31:40/reply-<random>`, subscribes to it, and puts it in the `sender` field of everything it sends to the controller.
- The controller replies to the sender's own topic, so several phones can watch one system and each gets its own copy of the answer.
- Messages are JSON with an `action` and a `message`. The actions that matter here are `first` (the app has just connected and wants the whole map), `refresh` (a ten-second heartbeat), `uirequest` (a user action), and `reply` (the controller's answer). Any message is also the proof that the round trip is alive.

Messages are carried at QoS 1, so a lost message is retried rather than silently dropping part of a map or a command.

## Following a reading

1. A thermometer wakes on its heartbeat — roughly hourly, or sooner if the temperature moves — and sends its reading over Zigbee to the coordinator.
2. Zigbee2MQTT publishes it on the local broker under the device's friendly name, for example `zigbee2mqtt/Kitchen-thermometer`.
3. The Zigbee bridge sees it, updates its cached reading for that device, and writes the readings it holds to `zigbee-temperatures.json` in its runtime directory.
4. Once a minute the controller reads that file, merges the readings into its own temperature record, and writes `thermometers.json` for the simulator and the terminal dashboard.
5. On each pass through its loop — every few seconds, not every minute — the controller compares each room's reading with the room's mode and schedule. A reading older than about three quarters of an hour is treated as missing, and the room is held off until a fresh one arrives. The reasoning is in [What RBR is](../concept/02-what-rbr-is.md).

## Following a command

1. When the controller decides that a room wants heat, it hands a small room record to `deviceControl.allspeak`, its own in-process module. This step is messaging inside the controller, not MQTT.
2. The module calls the Zigbee bridge over HTTP: `http://127.0.0.1:8889/device/<friendly name>?state=on` (or `off`). For a self-contained valve it calls `/trv/<friendly name>` with a setpoint and a mode instead.
3. The Zigbee bridge publishes the corresponding message on the local broker, under `zigbee2mqtt/<friendly name>/set`.
4. Zigbee2MQTT sends it over Zigbee through the coordinator, and the device switches. The bridge waits briefly for the device to report the commanded state, and returns that report to the controller as the HTTP reply, so a relay that did not answer is counted as a failure rather than assumed to have worked.
5. The demand relay takes the same path. It is switched on while at least one room wants heat and off when none does, which is how the boiler is asked to fire only when there is demand.

Two details of this path are worth holding on to. The controller does not subscribe to the `zigbee2mqtt/...` topics; only the Zigbee bridge does. And a battery-powered valve may be asleep when its command arrives: Zigbee2MQTT queues it, and the valve applies it at its next wake.

## Following a tap

1. The app is a static page. It needs a broker address, a user name and a password, and it gets them from `credentials.php` using the system's address and the token stored from pairing. With no credentials or no address it opens a baked demonstration map instead, and connects to nothing.
2. It connects to the cloud broker over a WebSocket on port 443 and subscribes to its own reply topic.
3. It sends `first` to the system's topic. The controller registers that sender and pushes the whole map. Every ten seconds thereafter the app sends `refresh`; the controller answers with a fresh map when something has changed, or with an empty message when nothing has, which still proves the connection is alive.
4. When someone taps a control, the app changes its local copy at once and publishes a `uirequest` to the system's topic.
5. The controller applies the change to the map, saves it if the plan changed, and pushes the full map to every connected app. If the app's optimistic guess and the controller's answer disagree, the next push corrects the app.

That is the whole of the app's relationship with the system: it reads a map and sends actions. It holds no authoritative state, which is what lets a second phone — or a provider looking at an estate — see the same system without any coordination between devices.

## When something is missing

- **The internet or the cloud broker is unreachable.** The heating carries on. The controller, the local broker, Zigbee2MQTT and the Zigbee bridge are all in the house, and the map and the schedules are on the controller. What stops is remote sight and remote control: the app cannot reach a system it cannot reach the cloud broker for. This is deliberate — the cloud is for reach, not for the control loop.
- **A local service stops.** `rbr-watchdog` checks the four core services — the local broker, Zigbee2MQTT, the Zigbee bridge and the controller — and restarts any that is down or has stopped answering its own health probe. It also checks that the heat is arriving: a scheduled room that has not warmed by 0.2 °C in an hour while its target is at least 0.5 °C above it causes all four services to be restarted, which recovers a component that is up but no longer driving the valves.
- **A thermometer goes quiet.** After about 45 minutes without a reading the room is treated as having no current temperature and its heating is held off. The app shows the last known value as stale rather than showing nothing. A scheduled period's first 30 minutes are the exception: they start the heat from the last known value, and turn it off if the thermometer still has not reported when the window closes.
- **The app loses its socket.** A backgrounded phone can have its WebSocket closed without the app being told. The ten-second refresh exposes the silence, a tab that has been away for more than five minutes reloads, and a 30-second first-map watchdog rebuilds a connection that never delivered its first map. That watchdog keeps retrying for as long as the app is open — quicker at first, then every few minutes — so a phone that slept through the network coming and going still reconnects by itself rather than waiting to be closed and reopened.
- **The controller restarts**, after an update or a service restart. It reloads the map from disk and rebuilds the readings from the Zigbee bridge within a few minutes. The plan is not lost; the readings are re-derived.

## Where the detail is

The engineering notes are the source of truth for everything above, and they are named here rather than linked because they are written for people working in the repository: `AI/ARCHITECTURE.md` for the running architecture, `AI/MAP_FORMAT.md` for the map, `doc/CONTROLLER-FILES.md` for what lives where, `doc/UPDATE-MECHANISM.md` for how code reaches a controller, and `doc/HEATING-DATA.md` for the heating log.

The other documents in this layer cover the map format, device control and the Zigbee bridge, updates and deployment, heating data and the controller files in their own right. The [glossary](../appendix/glossary.md) defines the terms used here; [What the setup script does](../installation/06-what-the-setup-script-does.md) describes the machine and the services that run on it.
