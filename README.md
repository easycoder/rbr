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

[https://rbrheating.com/home](https://rbrheating.com/home)

## Call for collaborators

This project has been developed by one person - me. It controls my central heating and that of a friend, but we'd like to spread the knowledge. I'm getting on in years so I won't be able to support it for very much longer. Anyone who is interested in joining will be most welcome. No strings are attached and I'll give as much help as I can to get you up the learning curve. The project uses some unusual programming techniques designed to help casual programmers get familiar with the product, but underneath it's all pure JavaScript, Python, PHP and C++.
