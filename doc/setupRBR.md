# Setting up a new RBR system #

Here are the steps to be taken to set up a new RBR system.

1. Install Linux on the system controller. Any variety will do. If your device has its own display, a desktop distribution is more appropriate, otherwise a server distribution will do fine. In either case you can control the system from an SSH connection.
2. Log in with the default user account name and password.
3. Download the setup script from the RBR website:

```
wget https://rbrheating.com/ui/setup
```

4. Run the setup script. This will first ask for a new password, then update the system, download all the files needed, set up cron tasks and reboot the computer.

```
sh setup
```

5. Log in again.
6. Make a note of the system MAC address and password (and save them somewhere safe, such as in the address book on your phone, as you may need them again in the future). They can be found at the command prompt by typing

```
cat mac
cat /mnt/data/password
```
7. In your mobile phone user interface (https://rbrheating.com/ui), tap the hamburger icon in the top right and select System Manager from the menu. If you're a new user you will have to register; just follow the instructions.
8. Click the Add button to add your new system and use the MAC and password you obtained in step 6. Select the system by its name and tap OK to return to the main user interface.
9. Add rooms, schedules and profiles as required. You will also need to run the RBR-Now configurator to set up relays and other devices.
 For this, see [Running the Configurator](configurator.md).

