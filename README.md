# Room By Room Control

An Open Source project to build a smart central heating system with control over the Internet.

This project uses commercially-available WiFi-connected modules - a temperature sensor and a relay module - and electrically-powered radiator valves, to automate domestic (or other) central heating on a room-by-room basis. The cost of the system is typically one tenth of the annual running cost of a domestic heating system, and since it can save 10% or more of the annual heating cost by making better use of heating it can pay for itself in the first year.

The repository software is in 3 parts:

  1. A system controller running on a Raspberry Pi (or similar) computer. This is coded in Python.
  1. A REST server on public shared hosting. This is coded in PHP.
  1. A user interface, built as a browser-based mobile webapp. This is coded in JavaScript.

Third-party tools are kept to a minimum. The project relies mainly on other products in the EasyCoder repository:

  - A high level scripting language coded in Python for the system controller
  - A similar high-level scripting language coded in JavaScript for the user interface
  - A JavaScript engine for rendering DOM structures expressed as JSON
  - An extended MarkDown processor for documentation, based on the third-party _Showdown_ markdown library

The system requires no software framework, nor any build tools beyond a text editor. This improves maintainability and offers ease of access to programmers of all levels of experience.

This ReadMe does not attempt to fully describe the system. Instead, all documentation is online and accessed from the webapp. The best way to get an introduction to RBR is to visit the webapp at

[https://rbrcontrol.com](https://rbrcontrol.com)

The webapp is designed to work on a smartphone but can also be viewed in any PC browser.