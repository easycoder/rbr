# Setting up a new RBR system

Here are the steps to be taken to set up a new RBR system.

> **Zigbee only:** every new build is Zigbee-only — all thermometers and
> relays are Zigbee devices paired through Zigbee2MQTT, and the legacy
> RBR-Now protocol is retired. Existing RBR-Now systems keep their current
> setup until they are rebuilt (see the legacy note at the end).
>
> **Minimum file set:** the definitive list of files that must be present on the
> controller computer is in [CONTROLLER-FILES.md](CONTROLLER-FILES.md).
>
> **Updates:** automatic code updates are handled by the standalone updater
> (`rbr-updater.py` + hourly systemd timer, installed by `rbr-setup.sh`) pulling
> a versioned tarball from rbrheating.com — see [UPDATE-MECHANISM.md](UPDATE-MECHANISM.md).
>
> **Data safety:** `rbr-mapbackup.py` (2-minute timer, also installed by
> `rbr-setup.sh`) keeps the last 10 valid `map.json` revisions in `map-history/`
> and restores the newest good one if the live file is ever left unreadable — a
> power cut mid-save can truncate it, because AllSpeak's `save` is not atomic.

1. Install Linux on the system controller. Any variety will do. If your device has its own display, a desktop distribution is more appropriate, otherwise a server distribution will do fine. In either case you can control the system from an SSH connection.
2. Log in with the default user account name and password.
3. Get a copy of the controller files onto the machine — either clone/copy the repo, or use the bootstrap pack (this is what a customer system uses):
```
mkdir rbr && cd rbr
wget https://rbrheating.com/get-controller.sh
sh get-controller.sh        # fetches and unpacks rbr-controller.zip over this dir
```
4. Install AllSpeak (the controller runtime) — this is deliberately not done by the setup script, because pip usually needs `--break-system-packages` on modern distros:
```
pip install allspeak-ai         # add --break-system-packages if pip refuses
```
5. Run the setup script as root. It prompts for the MQTT password and MAC address, then installs and configures everything: mosquitto (local broker + websocket + cloud bridge), Zigbee2MQTT (dongle auto-detected; web frontend on port 8080), the zigbee bridge service, the automatic updater and the component watchdog (both hourly), the map history keeper (every 2 minutes), and optionally the local UI and a controller service.
```
sudo ./rbr-setup.sh
```

   > **Plug the Zigbee dongle in before running this, and keep it clear of
   > metal.** The script detects the dongle as it starts and derives both the
   > udev symlink rule and Zigbee2MQTT's `port:` from what it finds, so
   > attaching it afterwards leaves you with a placeholder port and no stable
   > symlink. Fit it on a USB extension cable: a dongle pressed against the case
   > or against metalwork (a bracket, a shelf) can degrade every link in the mesh
   > at once, which shows up as relays that intermittently fail to switch. On a
   > real install, moving the dongle off a steel bracket doubled the
   > coordinator's link quality to every device and took failed relay commands
   > from thousands a day to virtually none.

6. Make a note of the system MAC address and password (and save them somewhere safe, such as in the address book on your phone, as you may need them again in the future). They can be found at the command prompt by typing

```
cat .mac_override
cat credentials
```
7. In your mobile phone user interface (https://rbrheating.com/ui), tap the hamburger icon in the top right and select System Manager from the menu. If you're a new user you will have to register; just follow the instructions.
8. Click the Add button to add your new system and use the MAC and password you obtained in step 6. Select the system by its name and tap OK to return to the main user interface.
9. Commission the Zigbee devices. The setup script (step 5) installed and enabled Zigbee2MQTT with the coordinator dongle auto-detected; make sure it is running, then pair the devices one by one:
```
sudo systemctl start zigbee2mqtt      # already enabled — start it if not running
sudo systemctl status zigbee2mqtt     # should show active (running)
```
   Open the Zigbee2MQTT frontend at `http://<this machine's address>:8080`.
   Click **Permit join**, power on one device at a time, and as each device
   joins give it a friendly name — one name per relay and one per
   thermometer, e.g. `Kitchen-radiator`, `Kitchen-plinth`,
   `Kitchen-thermometer`.

   > **Names must match exactly.** The zigbee bridge calls devices by their
   > friendly name, so the names you type here must match — character for
   > character, case included — what you enter in the RBR UI in step 10. A
   > mismatch shows up as a relay that never switches or a thermometer that
   > reads unknown, so name carefully and consistently (the convention above,
   > `<room>-<device>`, keeps everything self-describing).
   >
   > **The demand relay needs its expected name too.** Whichever device switches
   > the boiler must be named exactly as the map's `request` field says —
   > conventionally `Demand` — or nothing will drive the boiler.
   >
   > **If a relay stops acknowledging, power-cycle it.** Mains relays can wedge:
   > the device stays on the network and reports its state, but ignores
   > commands, so it looks healthy in the frontend while never switching. A
   > re-power has cleared it every time so far. `allspeak diagnose.as` (step 11)
   > reports it per device as `undelivered commands`, and
   > `curl -s localhost:8889/health` carries the same figures as `setFailures`.
   > Those counts are diagnostic: the controller's own relay-failure handling is
   > separate, and counts only commanded *transitions* that go unconfirmed.

10. In the RBR UI, add the rooms and wire them to the devices from step 9.
    The remote web UI is usually the most convenient. With the system
    selected (steps 7–8), go to **Devices** (hamburger menu → Devices):

    - In the room list, add each room (or rename one of the placeholders)
      and select it.
    - Set its **Thermometer** to the friendly name of the room's
      temperature sensor (e.g. `Kitchen-thermometer`).
    - Set **Relay type** to Zigbee and switch on **Sensor controls relay**
      when the room's thermometer should drive its relays directly (the
      normal case for a room thermostat).
    - List the room's **relays one per line** using the friendly names from
      step 9 (e.g. `Kitchen-radiator` and `Kitchen-plinth`).
    - If the boiler needs an external demand relay, set **Demand relay
      (Zigbee)** to it. Save when the room is complete.

    Repeat for every room, then add schedules and profiles as required.

    > **Replacing an existing controller?** You can copy `map.json` from the old
    > machine instead of re-entering everything — it carries the rooms, profiles
    > and schedules, and binds to devices purely by name, so pair the devices
    > (step 9) using the names the old map already contains. Its `request` field
    > names the demand relay. The map keeper takes a revision as soon as the file
    > changes, so the previous state stays available in `map-history/`.

11. Check it works — all read-only:

    - `cd ~/rbr && allspeak diagnose.as` is the quickest answer to "what does
      the system think is wrong": bridge health, every device that zigbee2mqtt
      knows with its type, model, cached state and last-seen, each room's mode,
      target, temperature, status and relay decision, plus the per-device
      undelivered-command counts. It is how you catch a name mismatch.
    - `sudo journalctl -u controller.service -f` — the controller's own log.
    - `curl -s http://127.0.0.1:8889/health` — bridge health, including
      `setFailures`. Localhost only, by design: that port can also switch relays.

    > **"No recent change" is normal.** Many thermometers report on a ~60-minute
    > heartbeat, or sooner if the temperature moves. A reading older than 45
    > minutes counts as missing, so the controller holds that room's relay off
    > until a fresh one arrives and the UI shows the last known value with a soft
    > warning. That is deliberate — a room cools gently rather than heating
    > without feedback — and it clears itself.

    > **For unattended operation, check the firmware.** Set the BIOS/UEFI
    > "Restore AC Power Loss" (also "AC Back" / "After Power Failure") to
    > **Power On**, and disable **ErP/EuP Ready**, which can block automatic
    > power-on. Nothing in the OS can read or set this, so test it by cutting
    > mains, restoring it and watching the machine come up by itself. The OS half
    > is already handled: every service is enabled, so the whole stack returns
    > without a login. After any outage, confirm `map.json` survived —
    > `allspeak diagnose.as` says whether it is present and lists the rooms; the
    > map keeper repairs a truncated one within a couple of minutes of boot.

> **Legacy:** installations still running RBR-Now hardware keep using the
> RBR-Now configurator until they are rebuilt — see [Running the
> Configurator](configurator.md). New builds ignore it.

