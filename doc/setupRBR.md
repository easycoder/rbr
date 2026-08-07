# Setting up a new RBR system #

Here are the steps to be taken to set up a new RBR system.

> **Minimum file set:** the definitive list of files that must be present on the
> controller computer is in [CONTROLLER-FILES.md](CONTROLLER-FILES.md).
>
> **Updates:** automatic code updates are handled by the standalone updater
> (`rbr-updater.py` + hourly systemd timer, installed by `rbr-setup.sh`) pulling
> a versioned tarball from rbrheating.com — see [UPDATE-MECHANISM.md](UPDATE-MECHANISM.md).

1. Install Linux on the system controller. Any variety will do. If your device has its own display, a desktop distribution is more appropriate, otherwise a server distribution will do fine. In either case you can control the system from an SSH connection.
2. Log in with the default user account name and password.
3. Get a copy of the RBR repo onto the machine (the repo directory *is* the controller directory):
```
git clone <repo-url> rbr        # or copy the rbr folder from another machine
cd rbr
```
4. Install AllSpeak (the controller runtime) — this is deliberately not done by the setup script, because pip usually needs `--break-system-packages` on modern distros:
```
pip install allspeak            # add --break-system-packages if pip refuses
```
5. Run the setup script as root. It prompts for the MQTT password and MAC address, then installs and configures everything: mosquitto (local broker + websocket + cloud bridge), Zigbee2MQTT (dongle auto-detected), the zigbee bridge service, the automatic updater (hourly), and optionally the local UI and a controller service.
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
9. Add rooms, schedules and profiles as required. You will also need to run the RBR-Now configurator to set up relays and other devices.
 For this, see [Running the Configurator](configurator.md).

