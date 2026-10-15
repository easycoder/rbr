# What `rbr-setup.sh` does

`rbr-setup.sh` is the one-shot installer for a controller computer. Run it once on a freshly prepared Linux machine and it installs and configures the whole runtime — the local message broker, the Zigbee software and its coordinator, the bridge the controller talks to, and the timers that keep all of it updated and healthy — then tells you what it started.

It is the step between "the machine has Linux on it and the RBR files on it" and "the machine is a working system". What it prepares is described in [Preparing the controller computer](docs/preparation/04-controller-computer.md); the human-facing sequence it fits into is [Setting up a new RBR system](doc/setupRBR.md).

> **Audience:** installer, commissioning technician, operator and maintainer · **Status:** draft · **Last verified:** 2026-10-15

## Before you run it

Run it from inside the controller directory, as root:

```
cd ~/rbr
sudo ./rbr-setup.sh
```

Four things are worth settling first, because the script reads them, derives from them, or bluntly tells you about them:

- **Plug the Zigbee coordinator in first.** The script looks for the dongle as it starts and uses what it finds to write the device-name rule and Zigbee2MQTT's `port:` setting. Attaching it afterwards leaves both as placeholders that have to be corrected by hand. Keep the dongle on a USB extension lead, clear of metalwork.
- **Have the MQTT password to hand.** It is the `password` field from your RBR credentials, and you will be prompted for it.
- **Know the controller's MAC address, or accept the default.** The script offers the MAC of the interface carrying the default route; this address becomes the controller's identity on the message topics, so it is worth checking rather than accepting blindly.
- **The user that owns the directory is the user everything runs as.** The script does not create an account; it takes the owner of the controller directory (normally your login) and installs every service to run as that user.

AllSpeak, the controller runtime, is **not** installed by this script — a Python package usually needs a flag that is the operator's call to use. The script checks for it, warns early if it is missing, and tells you the command:

```
pip install allspeak-ai        # add --break-system-packages if pip refuses
```

If it is not there, everything still installs except the two optional services that need it — the controller and the desktop application — and you cannot run the controller until it is installed.

**The script must be run as root.** Run any other way it stops immediately and says so.

## What it asks you

Before it changes anything, the script collects three answers.

| Question | Default | Why it matters |
|---|---|---|
| MQTT password | — | The password the bridge and controller use for the cloud broker. |
| MQTT username | `rbr` | The matching user name. |
| Controller MAC address | MAC of the default-route interface | The controller's identity in the message topics, so the phone app and the server know which system they are talking to. |

The password is the only one with no sensible default, so it is the one you are always asked for. If the directory (or your home directory) already contains a saved password, the script uses that instead of prompting and says which file it came from.

Every answer is stored the moment it is given, before any package is installed: the password in `.mqtt_password` (readable only by its owner), the MAC in `.mac_override`. Both live in the controller directory and both are what the "make a note of the MAC and password" step of the install guide reads back.

**If you run the script with its input closed** — from a script, or with a file of answers that runs out early — it stops with a plain message rather than quietly storing an empty password. An empty password would look like success and then fail somewhere less obvious.

## What it installs, step by step

The script announces each step with a boxed heading, so a run in a terminal reads as a list of one-line reports. This is what each step is doing.

### Step 1 — System packages

Updates the package list and installs the working set the rest of the run depends on: `mosquitto` and its clients, `git`, `make`, `g++`, `gcc`, `libsystemd-dev`, `python3-pip`, `curl` and `ca-certificates`. It then installs the Python MQTT library (`paho-mqtt`) used by the bridge.

It also checks Node.js, which Zigbee2MQTT needs at version 22 or newer — 22 because the package manager used to build it requires it. On an older machine the script installs Node.js 22.x from the NodeSource repository; if that download fails, it says so plainly and stops rather than continuing into a build that cannot succeed. `pnpm`, the package manager Zigbee2MQTT is built with, is installed globally.

**This step needs working internet access**, and it is normally the longest one.

### Step 2 — The local message broker

Writes a Mosquitto configuration to `/etc/mosquitto/conf.d/rbr-local.conf` and restarts the broker. That file does three things:

- Opens plain MQTT on port 1883 for the controller, the Zigbee software and the bridge to talk to each other locally.
- Opens a WebSocket listener on port 9001, which is how the browser interface reaches the broker.
- Opens a **bridge to the RBR cloud broker** at `rbrheating.duckdns.org:8883`, authenticated with the credentials you supplied, mirroring every topic in both directions. This bridge is what lets the phone app see this controller at all.

Both local listeners are configured to accept connections without a password, because they are the machine's own private channel between its own components. The cloud bridge is TLS-encrypted, using the system certificate store.

> **The broker listens on all of the machine's network interfaces.** Ports 1883 and 9001 are open to the local network, unauthenticated, by design — the browser interface needs the WebSocket one. If the machine sits on a network you do not trust, that is a thing to firewall rather than to fix in the script.

The step finishes by reporting whether the broker came up, and the command to use if it did not.

### Step 3 — Zigbee2MQTT

Zigbee2MQTT is the software that owns the Zigbee radio: it talks to the coordinator dongle, pairs devices, and publishes their readings and states. The step:

- Creates a dedicated system account, `zigbee2mqtt`, with no login shell, and adds it to the `dialout` group so it may use the serial port.
- Clones the project to `/opt/zigbee2mqtt`, or updates an existing copy there, and builds its dependencies with `pnpm`.
- Gives the coordinator a **stable name**. For the dongle it expects — a Silicon Labs CP210x device — it writes a udev rule so the dongle always appears as `/dev/zigbee-dongle` no matter which socket it is plugged into, and configures Zigbee2MQTT against that name. Without this, a restart that renumbers the serial devices would leave the Zigbee software unable to find its radio. **A different coordinator still works, but keeps whatever serial name it is given**, which can change between reboots; giving it its own rule is a small job the script does not attempt.
- Writes `/opt/zigbee2mqtt/data/configuration.yaml`: the local broker as its message server, the serial port and the Ember adapter type, the web frontend on port 8080 of all interfaces, radio channel 15, and fresh network key and network identifier generation (`GENERATE` — a new mesh on first start).
- Installs and enables `zigbee2mqtt.service`, ordered after the broker.

If no coordinator is detected, the script asks for the device path; if you skip that too, it configures a placeholder and tells you the line to edit, and Zigbee2MQTT will not start until you do.

### Step 4 — The Zigbee bridge

The controller speaks to the Zigbee software over a small local HTTP interface rather than directly. The step writes the bridge's configuration — `zigbee-config.json` in the controller directory, pointing at the local broker and opening the bridge's own HTTP port, 8889 — and installs and enables `rbr-zigbee-bridge.service`, running as your user.

That HTTP port is deliberately local: it can switch relays, so it is not meant to be reachable from the network.

### Step 5 — Controller credentials

Writes the controller's credentials file, pointing it at the local broker rather than the cloud one, so all of the controller's traffic goes through the bridge and the broker's own cloud bridge. The file is readable by its owner and its group only.

The email settings in it are **placeholders** (`smtp.example.com`, an empty password). The script says so; fill them in only if you want the controller's email features.

### Step 5b — Where the heating records live

The controller keeps each room's heating records under a data root, and that root is configured to be the same path on every machine: `/data/rbr-heating`.

- If that path already exists — the preferred case, a partition of its own — it is used as-is.
- If it does not, the script creates a folder in your home directory and makes `/data/rbr-heating` a symlink to it. Nothing else in the system changes when you later add a real partition; you move the folder and drop the symlink.

Either way the chosen root is recorded in `heatlog-root`, and the reasoning is in [HEATING-DATA.md](doc/HEATING-DATA.md).

### Step 5c — A placeholder for the RBR-Now configuration

The device-control module reads `config.json` at start-up without checking whether the file is there, so on a machine without one the controller would fail at start-up and the service would restart it in a loop. The script therefore creates a minimal `config.json` — an empty device map, which is correct for a Zigbee-only system — **but only if the file is missing**. An existing file, on a system that still has RBR-Now hardware, is never overwritten.

### Step 6 — The updater

Installs a one-shot service, `rbr-updater.service`, and an hourly timer, `rbr-updater.timer`. Each hour it checks `rbrheating.com` for a newer controller build; if there is one, it replaces the code files and restarts the services those files belong to. It runs as root precisely so it can restart them, and it touches **only** code files: machine-specific data — the credentials, the MAC, the map, the readings, the heating records — is never replaced, because those files are not part of the release at all. See [UPDATE-MECHANISM.md](doc/UPDATE-MECHANISM.md).

If the updater is not present in the directory, the script says so and skips this step rather than failing.

### Step 6b — The watchdog

Installs `rbr-watchdog.service` and an hourly `rbr-watchdog.timer`. It checks the four core services — the broker, Zigbee2MQTT, the bridge and the controller — and restarts any that is not running, or that is running but has stopped responding to its own health probe. This is what makes an unattended machine recover from a wedged component without anyone logging in.

### Step 6c — The map keeper

Installs `rbr-mapbackup.service` and `rbr-mapbackup.timer`, which runs shortly after boot and every two minutes. The controller saves its map with a non-atomic write, so a power cut in the middle of one can leave the file truncated — and a truncated map is worse than a missing one, because the controller's fallback covers only a missing file. The keeper checks the map, keeps the last ten distinct good revisions in `map-history/` beside the live file, and restores the newest good one if the live file cannot be read. It also runs shortly after boot, so a machine coming back from an outage repairs itself within a couple of minutes.

### Step 7 — A local web server for the interface (optional)

Asked as `Install a local web server for the UI? (y/N)` and skipped unless you answer `y`. If you do, the script installs `rbr-ui.service`, serving the controller directory on port 8082 of all interfaces, and writes the browser interface's own credentials file — pointing at the WebSocket port, 9001, with the MAC you gave — both in the controller directory and in the `new-ui/` subdirectory, where the interface looks for it.

This is the interface served on the machine itself. The hosted interface at `rbrheating.com/new-ui/` needs no local server.

### Step 8 — The controller as a service (optional)

Asked as `Run the controller as a service (auto-restart after updates)? (y/N)` and skipped unless you answer `y`. If you do, the script installs `controller.service`, running the controller as your user with restart-on-failure, so it survives reboots, crashes and updates. Two details in that service are worth knowing:

- Output is unbuffered, so its log lines reach the system journal as they are written rather than in bursts.
- The terminal dashboard is switched off. A service has no terminal; run the controller by hand without that flag to see the dashboard.

**If AllSpeak is not installed, this step reports that and skips**, rather than installing a service that cannot start. Answering `n` is a valid choice: the controller then runs only when you start it yourself.

### Step 8b — The desktop application as a service (optional)

Asked as `Run the desktop UI (PySide6 app) as a service? (y/N)`, skipped unless you answer `y`, and skipped if AllSpeak is missing. It installs the graphics runtime (`PySide6`) for your user and `rbr-desktop.service`, running the desktop application from the `desktop/` directory. The desktop application is the secondary interface — see [`desktop/config.example.json`](desktop/config.example.json) to point it at a broker on the local network.

### Starting the services

The script starts Zigbee2MQTT and the bridge explicitly (the others were started or enabled as they were installed), waits a couple of seconds, and then prints a summary: the state of every service it installed, the controller's credentials path and MAC, the coordinator in use, the Zigbee frontend and bridge addresses, the command to pair devices, the commands to read the logs, and the command to run the controller.

**A service shown as failed at this point is usually the Zigbee pair**, and usually because the coordinator is absent or its port is wrong — the script says so and names the journal to read. This is the normal case if you had to skip the coordinator earlier.

## What it does not do

- **Install AllSpeak.** Deliberate; see above.
- **Pair your Zigbee devices.** That is the next step of the install, and it is interactive.
- **Fill in your email settings.** The credentials file carries placeholders.
- **Configure the machine's firmware.** Coming back after a power cut depends on the BIOS/UEFI "restore after power loss" setting, which no Linux can set. The operating-system half — every service enabled, so the stack returns without a login — is what this script provides.
- **Change the map.** Rooms, schedules and profiles are entered in the interface, not here.

## Running it again

The script is written to be re-run, and re-running it is the normal way to repair an installation or to install the same configuration on a second machine. On a second run:

- The saved password is reused rather than re-asked; you are still prompted for the username and MAC (both with the previous values as defaults).
- Zigbee2MQTT is updated in place rather than cloned again.
- The broker configuration and every service file are rewritten from scratch, so any hand-editing of those files is lost.
- An existing `config.json` and an existing `heatlog-root` are left alone.
- `credentials.json` and the desktop service are only rewritten if you answer `y` again.

## If it stops part-way

A failing command stops the script rather than letting it run on — but it says where:

```
  ✗ rbr-setup.sh aborted (exit 1) at line 412 of ./rbr-setup.sh
    Re-run with: sudo bash -x ./rbr-setup.sh
```

Re-running with `bash -x` prints every command as it runs, which shows which one is failing. Re-running the script itself is also safe: it picks up from a clean state. The two things to check first are whether the machine has internet access (Step 1 needs it) and whether the coordinator is attached (Step 3 needs it).

## Related reading

- [Setting up a new RBR system](doc/setupRBR.md) — the full install sequence this script is a step in.
- [Preparing the controller computer](docs/preparation/04-controller-computer.md) — what the machine should be before this runs.
- [Files needed on the RBR controller](doc/CONTROLLER-FILES.md) — every file, and which of them this script creates.
- [Update mechanism](doc/UPDATE-MECHANISM.md) — what the hourly updater does in detail.
- [Heating data](doc/HEATING-DATA.md) — the records and the data root from Step 5b.
