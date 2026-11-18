# Taking on Room By Room

> **Audience:** a prospective successor or co-maintainer · **Status:** draft · **Last verified:** 2026-11-18 · **See also:** [Continuity and support](concept/06-continuity-and-support.md) · [Architecture](technical/01-architecture.md)

This is the brief written for Relay, a registry of open-source projects that need a next maintainer, and it is published here so the listing can point at it rather than carry it in full. It gathers what a successor would otherwise have to assemble from `CONTINUITY.md`, `AGENTS.md` and the engineering notes: what the system is, who uses it, what the estate consists of, what it costs, what the obligations are, what state it is in, and what the first month looks like.

## What it is

Room By Room is a control system for a house's central heating that decides room by room when each radiator should be on. A small Linux computer in the house holds the plan and switches the heating; Zigbee thermometers and radiator valves or relays sit in the rooms; and the household sets it from a web app in a phone browser, so there is nothing to install on the phone and no subscription. If the website or the internet is unavailable the heating carries on, because the plan lives on the controller in the house.

## Who uses it

Two installations run it in homes today. Neither was sold — the running costs are the maintainer's — so there are no paying customers, no installers under contract and no support agreements. The documentation is written for four audiences (the heating trade, installers, residents and developers) because the project is meant to be fitted by a heating engineer rather than by its owner, but no trade installer has taken one on commercially yet. The people who actually use it are the two households living with it.

## Why it exists

The problem is the one every central heating system has: a conventional programmer and room thermostat heat zones, or the whole house, and rooms that are not being used are heated anyway. Per-room control exists commercially, but it usually arrives as a closed cloud product with a monthly charge, an installer-only app and a dependency on one supplier staying in business.

Work on the repository began in January 2022. The original framing in `package.json` is still the clearest statement of the intent: a "distributed appliance", set up before delivery and simply plugged in, with none of the usual messing about with IP addresses, and no technical knowledge needed by the person living in the house — just the willingness to program a heating controller, which in practice means an installer.

The result is a system built from ordinary parts: a mini-PC, a Zigbee coordinator, thermometers and radiator valves, and plain files. There are no build tools and very few dependencies. What would be lost if it stopped is a working heating system in two homes, a documentation set written for the trade as well as for developers, a tested handover mechanism for pointing controllers at a replacement site, and the design reasoning recorded across the repository's history and its engineering notes.

## How it works

Three parts, plus the hardware between them.

**The controller** is `controller.allspeak`, running on the mini-PC under the AllSpeak Python runtime as `controller.service`. It holds the map, re-examines every room every few seconds, answers the app, and calls `deviceControl.allspeak` to switch relays. It writes the heating log (`heatlog.py`), the event journal (`eventlog.py`), and `thermometers.json`; `rbr-doctor.py` reports on a machine's health and `rbr-watchdog.sh` restarts a controller that has connected but never loaded its map. Everything a controller needs is a plain file, listed in `doc/CONTROLLER-FILES.md`.

**The plan** is `map.json`: one shared `rooms[]` list carrying each room's identity (relays, thermometer, frost protection, readings), then each profile's schedule state for that room, keyed by room name. Identity is stored once and a name is the join, so a room's wiring and its schedule cannot drift into another room. `AI/MAP_FORMAT.md` is the format of record.

**The radio** is Zigbee. Zigbee2MQTT owns the coordinator dongle, publishes each device's state on the local Mosquitto broker (port 1883, deliberately with no WebSocket listener), and accepts commands. `zigbee-bridge.py` keeps the latest reading for each device and offers the controller a small HTTP interface on 127.0.0.1:8889. The local broker is bridged to the cloud broker at `rbrheating.duckdns.org`, which is what lets a phone reach a system behind an ordinary router; the controller uses port 8883 and the app a WebSocket on 443.

**The app** is `new-ui/`: `index.html`, `sw.js`, a manifest, five AllSpeak modules under `new-ui/resources/allspeak/` (`shell.allspeak` is the large one and routes every gesture) and Webson JSON layouts under `new-ui/resources/webson/`. It is published to `/heat/` on the site and runs on a pinned AllSpeak build at `/dist/allspeak.js`, promoted by `pin-allspeak.sh` rather than taken from a rolling CDN.

**The server** is PHP on shared hosting and is not in this repository: `credentials.php` vends the MQTT account to a paired device (MAC plus token), `auth.php` handles registration and recovery, and `handover.php` with `handover-lib.php` runs the continuity channel. `rbr-users.json` — one entry per system MAC, with passwords and tokens — sits one level above the web root on purpose. `deploy.sh` publishes the site; the documentation reader at `/docs` is `docs-reader/` with the `docs/` tree copied beside it.

The controller also keeps a record of what happened: `heatlog.py` for room demand and achieved temperature, `eventlog.py` and `journal-export.py` for the event journal, and `tools/rbr-studio/` for turning a recorded day into a scenario that can be replayed without hardware.

## How to run, test and deploy it

**A new controller** starts with `get-controller.sh`, which fetches `rbr-controller.zip` from `/heat/` and unpacks it; `rbr-setup.sh` installs and configures everything and asks the questions it needs answers to; `rbr-preflight.py` reports what the machine looks like before you begin (coordinator attached, clock and timezone, storage, ports, broker reachable). The system identity is `~/.mac_override`, which is also the topic namespace and the registration key.

**By hand**, `allspeak controller.allspeak` runs the controller until it exits: an applied version update, a missing credential, an unreadable MAC or a script error. `controller.service` restarts it every five seconds, so a crash loop still shows `active` — count the session starts in the journal instead. A healthy start logs `Subscribed to topic` and then `Load the system map`.

**The checks that need no broker, browser or controller** are cheap enough to run after any edit:

- `tests/unit/controller-compile-check.sh` compiles `controller.allspeak` as a whole, which is the only check that would catch a duplicate symbol — one stopped every controller that took an update on 2026-10-26.
- `tests/unit/run-unit-tests.sh` runs that check plus the AllSpeak and Python unit tests.
- `node tests/pwa-compile-check.js` compiles all five web-app modules in the pinned browser runtime; the other `tests/pwa-*.js` checks drive the sheet editors, the valve tag, the backup sheet and the handover banner.
- `python3 -m unittest` over `tests/unit/` covers the journal, overrides, handover and doctor contracts.

**The browser suite** is separate because it needs a browser: `npx playwright install chromium` once, then `npm run test:ui`. It serves the real app from the repository root, replaces `window.mqtt` with a scripted client so a spec decides what the controller replies, and needs no broker or controller.

**The app locally** wants a static server (`python3 -m http.server 9000`, then `/new-ui/index.html`); it must not be opened as `file://`, because it fetches its scripts and layouts. It reads a `credentials.json` beside it, then `../credentials.php`, and otherwise falls into a demo mode with a baked map. Neither a deploy nor `rbr-setup.sh` puts a `credentials.json` there, so write one from `credentials.example.json` pointing at a broker that offers WebSocket — the controller's own broker does not.

**Deploying** is `./deploy.sh`, which rsyncs over SSH, or the Deploy workflow run by hand from GitHub Actions with the deploy key in `secrets.DEPLOY_SSH_KEY`. Without `--release` the version stamp does not change and controllers keep their current code; with it, the stamp is bumped and every controller applies the tarball on its next hourly check. The version file is uploaded last on purpose, so a controller mid-check never sees a version it cannot fetch.

**Gotchas worth knowing.** There are no build tools; every file runs as it stands. The pinned JavaScript runtime is deliberately behind upstream, so a command in the AllSpeak curriculum may be missing here — `loop` is, and `on failure` stops the thread rather than continuing. A handler is registered by executing its line, so an `on click` written after a `stop` never registers. All variables are global, and whether an assignment copies or aliases a JSON record depends on the form used — the shared room list broke twice on that. `AGENTS.md` lists the rest.

## The estate

| Asset | Where it is | What happens to it |
|---|---|---|
| Repository | `github.com/easycoder/rbr`, public, under the personal account `@easycoder`, MIT licence | GitHub ownership transfer, or a pre-designated successor recorded in the account settings |
| Website and app | `rbrheating.com`, shared hosting at `/home/rbrheating/rbrheating.com` | Registrar and hosting support; the domain is the critical asset |
| Documentation | `docs/` in the repository; the reader at `/docs` | Travels with the repository and the site; no separate service |
| Controller update channel | `/heat/` on the site: `rbr-controller.tar.gz`, `rbr-controller.zip`, `version` | Travels with the site |
| Account register | `/home/rbrheating/rbr-users.json`, one entry per system MAC | Hosting account; contains passwords and tokens |
| Host settings | `/home/rbrheating/rbrheating.com.txt` | Hosting account; broker and mail settings, and the handover passphrase |
| Broker | `rbrheating.duckdns.org`; the DuckDNS account and the broker host, which is a separate machine | DuckDNS account plus broker host access |
| Mail | `info@rbrheating.com`, and the SMTP settings the controller uses for emailed backups and journals | Mailbox and mail-provider account |
| Deployment key | The SSH key used by `deploy.sh` and the Deploy workflow | Hosting account and GitHub secrets; replace rather than share it |
| Data | `backup/`, `map-history/` and the event journals on each controller; the Zigbee2MQTT database | Held with the installation or the maintainer; contains customer data and secrets |

The name is used as a project name only; no trademark registration is recorded anywhere in the repository. There are no contracts to transfer: no customer agreement, no support agreement, no reseller or licence arrangement. `CONTINUITY.md` is the transfer plan and `doc/HANDOVER.md` the technical channel; neither transfers ownership by itself.

## The economics

There is no revenue and never has been. Nothing has been sold — not software, not support, not a subscription. The running costs of the estate have been the maintainer's.

The estate costs under £10 a month in total: shared hosting and the domain for `rbrheating.com`, the host that runs the cloud broker, and the mail account. DuckDNS is free. Each installation's own hardware — the controller computer, the coordinator, thermometers, valves and relays — and its broadband are costs of that house, not of the project.

Nothing is owed: no invoices, no debts, no deferred payment, no promised refund. The potential that exists is commercial rather than built: an installer could charge for fitting and for support, and the documentation is written for that reader, but the software has no price, there is no billing arrangement and no one is being asked to pay.

## The obligations

- Keep `rbrheating.com` serving `/heat/`: it is both the app and the controller update channel, and every controller checks it every hour.
- Keep the broker reachable at `rbrheating.duckdns.org`. Without it the app stops working on every phone, though the heating continues on the controller.
- Treat the data as personal: `rbr-users.json` (email addresses, passwords, tokens), controller backups (which carry the Zigbee network key), and journals (room names, occupancy patterns and the exact payloads people sent). Keep them local, do not publish them, and keep them out of AI prompts without redaction.
- Rotate the broker password and each system's token after any transfer. That unpairs every phone holding the old token, so say so first rather than after.
- Keep the code under the MIT licence and the open-source terms the continuity plan records. Changing the licence, selling the project or closing it down are decisions for the owner, taken with advice.
- Answer support mail at `info@rbrheating.com`, or replace it with an address that is answered. It is also the recovery address for registered systems.
- Keep the continuity plan current: a successor named in the addendum, emergency access somewhere reachable, and the successor recorded with GitHub while the maintainer is still active.
- Do not imply a contract. There is no support agreement, no response time, no warranty and no service level, and the project's own documentation says so plainly.
- Exercise the handover channel at least once against a prepared replacement site. It is built and tested in the repository, but no dry run has been made against a real replacement, and there is no sealed passphrase in an installer's hands yet.
- Do not tell the two households their data is unchanged or their pairing is untouched if a rotation was needed. Say what changed and what they have to do.

## The state of play

**Running and working.** The site, the app, the documentation reader and the controller update channel are live. Two installations run on it. The map, the message path and the update channel have all been exercised on real hardware.

**Known bugs and limits, recorded in `REQUESTS.md`.** The pinned JavaScript runtime is older than upstream: it has no `loop`, `on failure` stops the thread instead of continuing, a second blocking `send … and assign reply` from one program overwrites the first one's reply slot, and `set default of <select>` fails silently when no option matches. Each has a workaround in the app or the shell, and each would be better fixed upstream.

**Technical debt worth naming.** Every installation shares the single MQTT account `rbr`; separation between customers rests on each app only knowing its own MAC rather than on broker access rules, so genuine isolation would be broker work (`doc/PROVISIONING.md`). The watchdog carries a workaround for a connect event that can be lost if it arrives before the handler is registered. `package.json` still says ISC while `LICENSE` is MIT. `desktop/` is a PySide6 port kept but secondary, and is not yet on the shared-room-list format. The legacy `/resources/` UI was retired on 2026-10-17 and some documents still describe the superseded IXHUB controller.

**Bugs fixed recently, each now guarded by a test** — worth knowing because they describe the failures this system actually has: a duplicate symbol that stopped every controller taking an update (2026-10-26); Advance, On and Off reverting a second after the tap, caused by JSON aliasing in the shared room list; the room tag showing the controller's demand rather than the valve's own state, which left two rooms "heating" while every valve was idle (2026-10-26); a sheet editor losing its reply when a map push arrived mid-edit (2026-10-24); a profile rename leaving the calendar pointing at the old name (2026-10-26); and a broker bridge refusing connections because the stored password was the wrong length (2026-10-17).

**Documentation.** The concept, preparation and operation layers are written and the first technical pages exist, all marked draft — nothing in the tree has been reviewed by anyone but its author. Installation 01–05 are still re-cuts of `doc/setupRBR.md` and its neighbours, six technical pages are harvests of existing engineering notes, and the FAQ is unwritten. `TODO-docs.md` holds the order of work.

**Work waiting on the world.** A trial of self-contained battery radiator valves is outstanding; it decides whether the valve or RBR sets the temperature, whether a thermometer is still needed in the room, and what an installer has to enter to commission one. The current-measurement phase — CT clamps giving grid, solar, heat pump and store, so the system can plan around an all-electric house — is designed and documented (`doc/current-measurement.md`, `doc/PROPOSAL-current-measurement.md`) but not built. Pre-pairing devices before delivery is stated as intent and not yet proven.

**Governance.** The continuity plan is written (reviewed 2026-11-16) but its addendum has no named successor, there is no prepared replacement site, and no passphrase has been sealed for an installer. The handover mechanism itself is implemented and tested.

## The first 30 days

1. **Read the two documents that hold the design**, `CONTINUITY.md` and `AGENTS.md`, then `README.md` and `docs/README.md`. They describe the estate, the account transfer order and the conventions the code is written to.
2. **Take the accounts in the right order.** GitHub first (ownership or organization ownership), then the registrar and DNS, then the hosting account, then the DuckDNS name and the broker host, then the mailbox. Turn on two-factor authentication and change recovery addresses as each one moves, and run `./deploy.sh` from a checkout before announcing anything.
3. **Record the handover properly**: put your name in the continuity addendum, change the maintainer address, and tell GitHub who the successor is. This is the part that is currently missing.
4. **Run the code before changing it.** `tests/unit/run-unit-tests.sh`, `node tests/pwa-compile-check.js` and `npm run test:ui` on a clean checkout; then `sudo python3 rbr-doctor.py` on a live controller to see what a healthy one looks like.
5. **Deploy something small without `--release`**, confirm the site changed and the controllers did not move. That is the whole release mechanism in one step.
6. **Speak to the two households** before anything visible changes: what you are taking on, what stays the same, how to reach you, and what would make every phone pair again.
7. **Rotate the credentials** you inherited — broker, per-system tokens, deploy key, mail — and expect to unpair both phones when you rotate a token. Say so before you do it, not after.
8. **Exercise the handover once** against a staging copy of the site. A channel that has never been used is a design, not a capability.
9. **Finish the installation documentation** (01–05), which is the layer an installer actually walks, then harvest the six technical pages. Fix documentation and code in the same pass when the work turns something up.
10. **Only then plan the product work**: the battery valve trial first, because it may change commissioning and the map, and the current-measurement phase after it.
