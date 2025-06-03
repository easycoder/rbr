# RBR-Now #

**RBR-Now** is a networked control system based on the ESP32 microcontroller, designed for ESP32-based devices such as a radiator TRV or a DHT22 thermometer, and uses ESP-Now to implement chained networking allowing any device to run its own subnetwork to overcome range and capacity issues.

All the software in RBR-Now is MicroPython (uPython) and every device in the RBR-Now network is equipped with the same set of files. The behaviour of each device is determined by a small JSON configuration file.

The system can be deployed simply by loading devices with the core file set and a suitable configuration file, but is best managed by the RBRConf program; a Python GUI application for Linux computers. (It cannot run on Windows because it relies on networking commands that are not available on that OS.) RBRConf allows any device on the network to be interrogated, controlled and have its firmware updated remotely without any need to remove it from service.

An RBR-Now network comprises a hub (master) device and a number of slaves. A control system using RBR-Now connects solely to the hub device and controls the slaves through it. This documentation will first describe the slave functionality as this is the simpler device..

## The RBR-Now Slave device

An ESP-Now slave unit only receives; it doesn't initiate messages as it has no information about where to send any. To send a message to one we have to know its MAC address. This can be found by setting up the device as a wifi hotspot and arrange for the SSID to include the MAC address. To make things simpler, the RBR-Now system automates this process as follows.

When the device starts it looks for its configuration file, but this will not initially exist. So it drops into slave mode and creates a hotspot whose SSID is based on its MAC address but with a specific RBR prefix. When the configuration program is told to scan for slave devices it looks for this prefix and offers a list of all devices that match. The user selects one (there usually is only one, as I'll explain shortly) and the program notes the relevant MAC address. The new device is added to the list in the Slaves panel as an untitled device. When the user clicks that item, all relevant details for the device can be added in a panel on the UI screen. These details comprise the name by which the device will be known (usually the room name) and pin numbers for the onboard LED, the relay and the thermometer (if either of these are present). With this information, a JSON structure is created and sent to the device as its config file, so that next time it starts up it can configure itself appropriately.

The hotspot is basically open (otherwise the device couldn't be connected) so this is an obvious vulnerability. To overcome this, the hotspot is disabled after 2 minutes. (It cannot be removed entirely because this would prevent ESP-Now from working, so it's given an SSID comprising a single dash and a randomly generated numeric password, making it virtually impossible to get into and rendering the MAC address inaccessible.) So by the time a second device is to be configured, existing ones are unlikely to appear in a search.

Apart from initial configuration, all comms with a slave is done using ESP-Now, which only requires the MAC address to be known. The device indicates which mode it's in by flashing its onboard LED on-off with a 1-second cycle for the initial 2 minutes, then a brief flash every 5 seconds after that.

The slave code waits for messages to arrive and acts on them. Messages will only arrive from the system controller, although in some cases they may be relayed via another slave device. Each message is acknowledged and any requested data is passed back. This includes such things as the relay state, the up time (seconds from startup) and thermometer readings.

The device also runs concurrent code that monitors BLE transmissions, looking for the signature of a Mijia thermometer. Every time one is seen, its advertising packet is read and the relevant data extracted. This will be returned as part of the response to the next message from the controller. Queuing is not implemented, so if several Mijias are detected at the same time, only one of them will be captured on this occasion.

Among the commands that can be sent are some that permit any file on the device to be updated. (This does not include MicroPython itself.) The configurator has the ability to update one or all the files on a device.

## The RBR-Now Master device

The Master (or Hub) device is the gateway between the system controller and the network of RBR-Now devices. It can itself be one of those devices, or it can be a separate module placed centrally where it can easily be seen by all the others, which are all Slave devices as described above. The Master has no knowledge of the other devices, nor of the system controller; it just responds to requests. Most of the functionality of the Slave is also shared by the Master.

The Master must be the first device set up by the configurator, which treats it specially. As with the slaves, the device initially has no configuration file, so as above it publishes a hotspot and waits for a connection. The configurator creates a JSON configuration file similar to that for a slave but additionally containing the SSID and password of the home network router and identifying the device as the master, then sends the file to the device and asks it to reset itself. When it restarts, the device will connect to the router and will get an IP address. The configurator waits for 10 seconds to allow this to complete, then sends another message to the hotspot requesting the IP address. From then on, all communication is done through this IP address. As with the slave, after 2 minutes the hotspot is disabled and the LED cycle changes, this time to a double flash every 5 seconds.

## System messaging

All messages from the system controller to an RBR-Now device are sent to the Master/Hub device at its IP address on the home network. Messages are prefixed by the MAC address of the target device, as recorded by the configurator when the device was added to the system.

When the Master device receives a message it checks to see who the message is addressed to. If it's the master device itself the message is handled and a reply sent. If it's any other address the message is forwarded to that device via the ESP-Now network,and the reply from that device is returned to the system controller.

In some cases a device is too far away from the hub to receive messages reliably. In such cases the device can piggy-back off another, closer device. Here, the MAC address given has a special prefix and identifies the path to the target device, going via as many intermediates as necessary. The path is part of the configuration for a device; in most cases it is empty.

The messages understood by devices are as follows:

### on

Turns on the device relay. It returns 'OK' then the up time of the device (in seconds) and the most recent Mijia reading it has received (if any).

### off

Turns off the device relay. The reply is the same as for **on**.

### relay

Returns the current state of the relay.

### temp

Returns the current temperature, if the device is a thermometer.

### reset

Causes the device to reset itself.

### ipaddr

Returns the IP address of the device (master only).

### pause

Requests the device to pause all operations that may interfere with actions such as updating files.

### resume

Requests the device to resume operations as normal.

### part

Signals that the attached data (up to 100 characters) is part of a file to be saved by the device. The file content is sent in hex format, 100 bytes at a time, each with a part number starting with zero, and the device saves each part as it arrives. Part numbers must be in the correct sequence or an error occurs.

### save

Saves the accumulated parts into the file whose name is given. The device saves the file then reads it back to check it matches what was received by the **part** requests.

### delete

Deletes the file whose full path is given.

## mkdir

Creates a directory with the name given.