# Setting up RBR-Now hardware #

Every RBR-Now device has the same Python code driving it. The behaviour of the device is determined by the contents of a small JSON configuration file, which is set up and managed by the [configurator](configurator.md).

The devices themselves are all powered by some variant of the ESP32 microcontroller. At the time of writing, these will be mainly ESP32-C3. Each variant has a different Micropython binary; they are all held  at the [MicroPython download site](https://micropython.org/download/).

The steps required are as follows:

1. First build your device. The steps that follow assume an ESP01-C3 module or something similar, with an output pin driving a relay and potentially another pin connected to a DHT22 sensor.

1. Download the Micropython binary from the download site above.

1. Download the RBR-Now files from [the repository](https://github.com/easycoder/rbr). It's probably simplest to clone the entire repository; the RBR-Now files are in the directory of that name at the top level.

1. Connect the ESP32 module to a USB port on your computer. These instructions assume Linux.

1. Type `ls /dev` to establish which port the ESP32 is on. The most common is `ttyUSB0`, but some appear as `ttyACM0`.

1. Erase the ESP32 by running this command, substituting (PORT) with the port name above:
`esptool.py --chip esp32c3 --port (PORT) erase_flash`
(This naturally assumes you have the `esptool` Python module installed.)

1. Flash Micropython onto the ESP32 using this command, adjusting (PORT) as before, and substituting (PATH) with the full path to your downloaded binary file:
`esptool.py --chip esp32c3 --port (PORT) --baud 460800 write_flash -z 0x0 (PATH)`

1. Run Thonny on your computer. In Run | Interpreter, select MicroPython (ESP32) and give the port number for the ESP32.

1. In the Files panel, navigate to where you downloaded the RBR-Now files. Select all the files
 and upload them to the ESP32, overwriting anything that was already there.
 
At this point you can install the ESP32 into your device and power it up. From here on, everything is done using the configurator.
 
[Return to the configurator](configurator.md)

