# RBR-Now Configurator #

RBR-Now is a collection of local devices, all powered by ESP32, that implement the ESP-Now networking protocol to accept commands from a central controller. (For setting up hardware, [see here](setupHardware.md)). Configuration is a fairly complex procedure, so a special tool has been built to automate the process.

## Overview

Each RBR-Now device is programmed with the same set of MicroPython files, and the way it uses these files is determined by a configuration file `config.json` stored on the device.

The RBR network comprises a central hub, or “master” device, that connects to the local LAN and receives commands from the system controller. All the other devices are “slaves” that receive messages from the master device.

By default, each RBR-Now device starts up as a slave. On the first startup it creates its own `config.json` file, with the following content (subject to future revision):

```
{
    "pins": {
        "led": {
            "pin": "",
            "invert": false
        },
        "dht22": {
            "pin": ""
        },
        "relay": {
            "pin": "",
            "invert": false
        }
    },
    "master": false,
    "name": "(none)",
    "channel": 1
}
```

In the above, three pins are declared; one for the on-board LED, one for a relay and one for a DHT22 sensor. If the values are empty the system will assume the pin name is not relevant for the device. The "master" flag determines which mode the device will come in. "name" is what you decide to call the device, typically the name of the room it's in. "channel" is the wifi channel used by your home router. At present it's assumed to be channel 1, but we'll add a configuration option to choose another channel.

The device also sets up a wifi access point with the SSID `RBR-Now-xxxxxxxxxxxx`, where `xxxxxxxxxxxx` is the MAC address of the device. The password is `00000000` and the IP address of the device on its network is `192.168.9.1`. This allows a browser to contact the device to perform further configuration. The device can then be sent a reboot command to act on the configuration given.

ESP-Now requires a device to have an active wifi connection, but the access point is essentially open, which is a major security hazard. For this reason, after 2 minutes the SSID of the access point changes to a single dash (-) and the password to a random number, so although it is still active the device is virtually inaccessible, all the more so because all devices have the same SSID. The implication of this is that after 2 minutes the only way to communicate with an RBR-Now device is via the system’s master device.

The master device has a slightly more complex configuration. When the configurator first connects to it, the SSID and password of the network it is to connect to (the home router) will be added to the config file and the "master" flag will be set to `true`. After a reset it then connects to that host as a regular network client and receives an IP address that will subsequently be used for all communications between the system controller and the RBR-Now device network.

## System prerequisites ##

To run the configurator you will need EasyCoder. This should have been set up when the RBR software was installed, but if not you  can run

```
pip install -U easycoder
```

where the `-U` option makes sure that any older version you may have will be updated to the latest. EasyCoder will install in `~/.local/bin`, which may not be on your execution path. You can either adjust this (e.g. in `.profile`), or give the full path when you run EasyCoder, or set up an alias using the `ln` system command such as:

```
ln -s ~/.local/bin/easycoder ec
```

Next, create a text file `rbrconf.ecs` containing the following:

```
!   RBR-Now configuration

   script RBRConfig

   variable Script
   module RBRConfig

   get Script from url `https://raw.githubusercontent.com/easycoder/rbr/refs/heads/main/rbrconf.ecs`
   save Script to `.rbrconf.ecs`
   run `.rbrconf.ecs` as RBRConfig
   delete file `.rbrconf.ecs`
   exit
```

The line `get Script from url …` is a single line. It probably shows wrapped in the listing above.

Now issue this command:

```
easycoder rbrconf.ecs
```

When the script runs it pulls the latest configurator code from the repository and runs that. So you never need to update the configurator yourself.

## The system configurator ##

The configuration is a GUI application written in EasyCoder for Python. It runs exclusively on Linux because it requires the use of commands that are not available on Windows. Here is a screenshot of the application under development:
<br/>

<img src="img/config.png" width="100%">

When first started up, the configurator identifies the network the computer is currently connected to, and asks for the wifi password. Many of the features of the configurator require connecting to different network hosts, so the router password is needed in order to reconnect (and it cannot be obtained any other means). It also asks for the directory containing the Micropython source files for the RBR-Now devices, so that updates can be applied if needed. The requested path is relative to your home folder, not to the system root.

# Overview of the configurator #

I'll start by outlining the primary features of the configurator, before decribing in detail how to set up a network of devices using the tool.

## Finding RBR systems ##

Initially, the only button that is enabled is “System Scan”. This lets you specify the IP address of the system (if yu know it), or alternatively performs a scan of the network to discover RBR system controllers. Each of these runs an access point on an obscure port number, that responds to a specific request by returning its name and the MAC address and password for accessing the RBR web server. With this information, the configurator contacts the server and downloads the current configuration information (if any) held for that system. As can be seen above, the UI is populated with this information. A system scan takes around 5 minutes as it has to check every IP address from 1 through 254.

The configurator can handle any number of systems, even if they are not all on the same network. The Systems dropdown box holds a list of names, and when one is selected the configurator checks if the network for that system matches the one the user's computer is currently on. If not, it offers to reconnect to the system’s network (if it’s accessible). Note that this has no effect on the RBR devices themselves. There's also a Cancel option which does nothing, but this will leave you unable to access the devices on the selected system.

All configurator functions that make changes to the information held will require confirmation from the user, so it is generally quite safe to experiment with the buttons. Note also that while the configurator is running, the system controller on the selected system is prevented from running. This lets you turn relays on and off manually from the configurator without the system controller immediately overriding your actions.

## Finding RBR-Now devices ##

With the appropriate system selected, the “Scan for devices” button searches the current network for RBR-Now devices, each of which has an SSID starting with RBR-Now. A list is then presented to the user, who selects one. The first time this is done for a system, the chosen device will become the master. The configurator connects to the device’s access point and sends it a new `config.json`, which includes the SSID and password of the network router. It then requests the device to reset and waits for 10 seconds for this to happen. When the device restarts it connects to the network and gets an IP address that the system controller will need, so the configurator now sends a request to the device for this address, which is added to the system configuration and sent back to the server.

A slave device requires none of the above configuration. Once selected and confirmed as contactable it just goes into the “Slave devices” list.

## Working with devices ##

The user can select the master device or any one of the slaves by clicking its name. This causes the current configuration of the device to be copied into the “Selected device” fields. Here you set the name of the device and the pin numbers it uses for the LED, relay and thermometer (other fields may be added in future). Every time you interact with the device you will see the “Uptime” value increase, confirming that the device is active.

Once changes have been made, clicking the “Update” button writes the changed configuration back to the device.In most cases you will then click Reset so the configuration changes are picked up by the device.

If the device is driving a relay you can turn this on and off by clicking the appropriate + or - button.

## Information storage ##

The configurator creates a hidden file `.rbr.conf` in the users’ home directory, containing all the currently known information about the systems being managed and the devices they contain. Each of the systems managed has its own configuration file on the RBR webserver; this is copied over when a system is accessed in the UI, and replaces that part of the local file. This is to permit changes to be made on different computers; the UI will always use the most recent data.

# A walk-through of the setup process #

Let's imagine a system with 4 rooms; Kitchen, Lounge, Bedroom 1 and Bedroom 2. Each of these has a single radiator, which is controlled by a thermo-electric TRV powered by an RBR-Now relay box. Let's suppose the system controller is in the kitchen, so it makes sense for the Master device to be the one next to the kitchen radiator. All the other roooms are assumed to be close enough for the wireless signals to reach from the kitchen.

I assume you've already built the relay boxes, flashed them with Micropython and loaded the RBR-Now Python scripts onto them. If you need more information about doing this, see [Setting up RBR-Now hardware](setupHardware.md). You will also have installed Linux on your system controller and downloaded the RBR controller software as described in [Setting up a new RBR system](setupRBR.md).

In the configurator, scan for systems (or provide the IPaddress of the one you have).

Once the system name is showing in the Systems box, power up the Kitchen device and click the 'Scan for devices' button. After a while a popup should appear with the MAC address of that device, so select it. There will then be a back and forth dialog between the configurator and the device, with messages appearing in the bottom right corner of the display. When all this has finished you should have a green OK messsage and the device details should be showing in the 'Master device' button. When you click the button, the panel on the lower right will contain everything that is known about the device, which initially is very little. Change its name from (none) to Kitchen. Also provide the pin numbers appropriate for the device. For an ESP01-C3 this is usually pin 3 for the LED and 9 for the relay. Now click Update, wait for this to complete then click Reset. When the device powers up again it should be flashing its onboard LED, but if not then check everything and try again.

Now you can do the other rooms, one by one. These will all be slaves. Only power up one new device at a time otherwise you may get confused as to which is which.

The names you give to the devices are exactly the same as you will use to identify them in the controller UI. The controller uses the data file saved by the configurator to identify and control each device.
