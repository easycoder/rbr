# Room By Room Control

This is an Open Source project to build a smart central heating system with control over the Internet. Although it might be considered to be just another "Smart Home" product, this one has one important difference. It's designed to be a "distributed appliance"; that is, something that can be set up before delivery and just plugged in, with none of the usual messing about with IP addresses that plagues the smart home world. No techncal knowledge on the part of the end user is required; just the ability (and willingness) to program a central heating controller.

An important feature of the system is that it can be managed externally. The UI permits one of any number of systems to be selected at will, and each system can be designated as being controllable by any desired number of managers. So  for example, a housing association can assign a set of installations to be managed by one or more nominated persons. All this is done by the UI app - a mobile web page that will run on any smartphone.

This project uses commercially-available BLE and WiFi-connected modules - a temperature sensor and a relay - and electrically-powered radiator valves, to automate domestic (or other) central heating on a room-by-room basis. The cost of the system is typically about a fifth of the annual running cost of a domestic heating system, and since it can save 10% or more of the annual heating cost by making better use of heating it can pay for itself in the first couple of years.

The repository software is in 3 parts:

  1. A system controller designed to run on an Orange Pi Zero 2 computer (but others may serve equally well). This is coded in Python.
  1. A REST server on public shared hosting. This is coded in PHP.
  1. A user interface, built as a browser-based mobile webapp. This is coded in JavaScript.

Third-party tools are kept to a minimum. The project relies mainly on other products in the EasyCoder repository:

  - A high level scripting language coded in Python for the system controller
  - A similar high-level scripting language coded in JavaScript for the user interface
  - A Python engine for rendering graphics expressed as JSON
  - A JavaScript engine for rendering DOM structures expressed as JSON
  - An extended MarkDown processor for documentation, based on the third-party _Showdown_ markdown library

The system requires no software framework, nor any build tools beyond a text editor. This improves maintainability and offers ease of access to programmers of all levels of experience.

The webapp is designed to work on a smartphone but can also be viewed in a PC browser. It can be found at

[https://rbrheating.com/ui](https://rbrheating.com/ui)

## How it works

### Configuration
The system is described by two JSON files. One is the "map", which describes the physical configuration of the system, such as:

 - the name of each room
 - the MAC address of its thermometer
 - the type of device controlling the radiator(s) in the room
 - the operating mode (times, boost, advance, on or off)
 - a list of times and temperatures for each room

Additionally there can be multiple profiles that each have their own set of room information. Such as Weekday, Weekend and so on. There is an optional calendar that informs which profile applies to each day of the week.

The second JSON file applies if radiators are controlled by RBR-Now devices. It describes the device in each room:

 - the role of the device - Master or Slave
 - its name
 - the pin number of the onboard LED
 - the pin number that drives the relay
 - flags to invert either of these.
 - other network-specific information

RBR-Now devices use the ESP-Now messaging system, with a single master and multiple slaves. The master connects to the house router and receives messages from the controller via a simple HTTP server.

### Operation
The controller is triggered once every 60 seconds by a cron task. It starts by loading the map and the RBR-Now configuration file, and runs a set of operations every 10 seconds, repeating them 6 times so it finishes before the next call by cron.

For each room, the controller uses the current operating mode to decide if a room needs to be controlled. If not, it calls an OFF function to shut the radiator valve. If the room is to be heated and its current temperature is below that desired, the valve is turned ON. This requires a number of steps, depending on he operating mode. Timed mode is the most complex; it requires an examination of the map to get the target temperature for the current time, then a check to see if the current temperature is below or above it. This determines if ON or OFF should be called. Other logic applies to Advance, which causes it to use the next timing period rather than the current one (and cancels when the current one ends) and Boost, which ignores the timing entries and just aims for a fixed target temperature for a specified length of time.

This is a very basic description; the code is somewhat more complex.

### The code
All the controller code is written in EasyCoder, a high-level programming script that is well suited to the needs of this application. EasyCoder is itself written in Python and provides general language features in a more accessible form. It is described in its own repository.

## Call for collaborators

This project has been developed by one person - me. It controls my central heating and that of a friend, but we'd like to spread the knowledge. I'm getting on in years so I won't be able to support it for very much longer. Anyone who is interested in joining will be most welcome. No strings are attached and I'll give as much help as I can to get you up the learning curve. The project uses some unusual programming techniques designed to help casual programmers get familiar with the product, but underneath it's all pure JavaScript, Python and a small amount of PHP.
