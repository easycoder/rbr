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
5. Run the setup script as root. It prompts for the MQTT password and MAC address, then installs and configures everything: mosquitto (local broker + websocket + cloud bridge), Zigbee2MQTT (dongle auto-detected; web frontend on port 8080), the zigbee bridge service, the automatic updater (hourly), and optionally the local UI and a controller service.
```
sudo ./rbr-setup.sh
```
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

> **Legacy:** installations still running RBR-Now hardware keep using the
> RBR-Now configurator until they are rebuilt — see [Running the
> Configurator](configurator.md). New builds ignore it.

