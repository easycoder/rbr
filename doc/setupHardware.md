# Setting up RBR-Now hardware #

Every RBR-Now device has the same Python code driving it. The behaviour of the device is determined by the contents of a small JSON configuration file, which is set up and managed by the [configurator](configurator.md).

The devices themselves are all powered by some variant of the ESP32 microcontroller. At the time of writing, these will be mainly ESP32-C3. Each variant has a different Micropython binary; they are all held  at the [MicroPython download site](https://micropython.org/download/).

The steps required are as follows:

1. First build your device. The steps that follow assume an ESP01-C3 module or something similar, with an output pin driving a relay and potentially another pin connected to a DHT22 sensor.

1. Download the Micropython binary from the download site above.

1. Download the RBR-Now files from [the repository](https://github.com/easycoder/rbr). It's probably simplest to clone the entire repository; the RBR-Now files are in the directory of that name at the top level.

1. Connect the ESP32 module to a USB port on your computer. These instructions assume Linux.

1. Erase the ESP32 by running this command:
`esptool.py erase_flash`
(This naturally assumes you have the `esptool` Python module installed. Also, it will only work if you have just one device connected to your PC.)

1. Flash Micropython onto the ESP32 using this command, replacing (PATH) with the full path to your downloaded binary file:
`esptool.py --baud 460800 write_flash 0  (PATH)`

1. Run Thonny on your computer. In Run | Interpreter, select MicroPython (ESP32) and give the port number for the ESP32.

1. In the Files panel, navigate to where you downloaded the RBR-Now files. Select all the files
 and upload them to the ESP32, overwriting anything that was already there.

To avoid most of the above, here's an EasyCoder script that will do the job for you without using Thonny at all. First you need to install `ampy` from AdaFruit:

```
pip install adafruit-ampy
```

Now create a new file, `flash.ecs` containing the following script. You may need to adjust one or more of the variables at the top of the file, under `Set things up`:

```
!   flash.ecs

!   This script sets up all the firmware/software on an RBR-Now device

    script Flash

    variable Port       ! the port used by the device, e.g. /dev/ttyUSB0 or /dev/ttyACM0
    variable URL        ! the URL of the downloadable Micropython binary
    variable Binary     ! the path and name of the file to save the Micropython binary
    variable Scripts    ! the path to the RBR-Now scripts directory (without a terminating /)
    variable Files
    variable N

    ! Set things up:
    put `/dev/ttyUSB0` into Port
    put `https://micropython.org/resources/firmware/ESP32_GENERIC_C3-20250415-v1.25.0.bin` into URL
    put `ESP32-C3.bin` into Binary
    put `RBRNow` into Scripts

    ! Erase the device and install MicroPython
    download binary URL to Binary
    system `esptool.py --port ` cat Port cat ` erase_flash`
    system `esptool.py --port ` cat Port cat ` --baud 460800 write_flash 0 ` cat Binary

    ! Create directories on the ESP32
    save `import os` cat newline
        cat `os.mkdir('lib')` cat newline
        cat `os.mkdir('lib/aioble')` cat newline
        cat `os.remove('mkdirs.py')` cat newline
        to `mkdirs.py`
    system `ampy --port ` cat Port cat ` put mkdirs.py`
    system `ampy --port ` cat Port cat ` run mkdirs.py`
    delete file `mkdirs.py`

    ! Copy the BLE library files
    load Files from Scripts cat `/lib/aioble/files.txt`
    trim Files
    split Files
    put 0 into N
    while N is less than the elements of Files
    begin
        index Files to N
        print `upload /lib/aioble/` cat Files
        system `ampy --port ` cat Port cat ` put ` cat Scripts  cat `/lib/aioble/` cat Files
        ! Move the file
        save `import os` cat newline
            cat `source_file = '` cat Files cat `'` cat newline
            cat `destination_dir = 'lib/aioble'` cat newline
            cat `os.rename(source_file, f'{destination_dir}/{source_file}')` cat newline
            cat `os.remove('move.py')` cat newline
            to `move.py`
        system `ampy --port ` cat Port cat ` put move.py`
        system `ampy --port ` cat Port cat ` run move.py`
        delete file `move.py`
        increment N
    end

    ! Copy the RBR-Now files
    load Files from Scripts cat `/files.txt`
    trim Files
    split Files
    put 0 into N
    while N is less than the elements of Files
    begin
        index Files to N
        print `upload ` cat Files
        system `ampy --port ` cat Port cat ` put ` cat Scripts cat `/` cat Files
        increment N
    end

    exit
```

And now give this command:

```
easycoder flash.ecs
```
 
At this point you can install the ESP32 into your device and power it up. From here on, everything is done using the configurator.
 
[Return to the configurator](configurator.md)

