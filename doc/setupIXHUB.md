# Setting up an IXHUB controller #

The IXHUB is an industrial computer with a touchscreen, that comes with Android installed. The first job is to convert this to Linux. The manufacturer supplies instructions that should be followed carefully; these can be found at https://docs.google.com/document/d/16iSiGHH2VvuXWdOkp5VizXUO-V9MsP6H/view and will require a Windows computer.

Once this job is done, the computer will boot up in Linux. However, there are two problems, the first of which is that the system is all in Chinese. So here is what to do.

First connect a keyboard and a mouse to the computer.

Click the internet icon on the right of the task bar at the top of the screen. Select your router from the list and supply the password. Now click the application selector at the left hand end of the taskbar and look for the console application, which has an icon showing a black window. In this, type

```
ip a
```

which will give you all the network settings. Look for the IP address of the machine; you can log into this from another computer on the network, giving the user name 'linaro' and the password, also 'linaro'. Or alternatively you can continue on the IXHUB itself.

Now update the software on the computer, using these commands:

```
sudo apt update
sudo apt upgrade
````

You now need to edit a couple of files and for this you need the `nano` editor, which isn't installed. So fetch it:

```
sudo apt install nano
```

Let's change the system language from Chinese to UK English. Open the following file for editing:

```
sudo nano /etc/default/locale
```

As supplied, this specifies the Chinese language, so change it by replacing all the content with

```
LANG=en_GB.UTF-8
LANGUAGE=en_GB:en
LC_ALL=en_GB.UTF-8
```

The next time you reboot the computer it will come up in English.

The other problem is the computer is in landscape orientation, but for our purposes we want portrait. So we need to rotate the screen. We do this by adding an `xrandr `command to the startup applications:

### Open Startup Applications: ###

Go to the XFCE menu and navigate to Settings > Session and Startup.
Click on the Application Autostart tab.

### Add a New Startup Program: ###

Click on the "Add" button.
In the "Name" field, enter a descriptive name like "Rotate Screen".
In the "Command" field, enter the `xrandr` command for the desired rotation:

```
`xrandr --output DSI-1 --rotate left`
```

Click "OK" to save the new startup program. The next time you restart, the screen will be rotated 90 degrees to the left.

Now you can set up for the RBR applications; go to [Setting up RBR](setupRBR.md).
