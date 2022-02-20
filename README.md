# Room By Room Control

An Open Source project to build a smart central heating system with control over the Internet.

This project uses commercially-available WiFi-connected modules - a temperature sensor and a relay module - and electrically-powered radiator valves, to automate domestic (or other) central heating on a room-by-room basis.

The repository software is in 3 parts:

  1. A system controller running on a Raspberry Pi (or similar) computer. This is coded in Python.
  1. A REST server on public shared hosting. This is coded in PHP.
  1. A user interface, built as a browser-based mobile webapp. This is coded in JavaScript.

Third-party tools are kept to a minimum. The project mainly relies on other products in the EasyCoder repository:

  - A high level scripting language coded in Python for the system controller
  - A similar high-level scripting language coded in JavaScript for the user interface
  - A JavaScript engine for rendering DOM structures expressed as JSON
  - An extended MarkDown processor for documentation, based on the third-party _Showdown_ markdown library

The aim is for the system not to require any framework, nor any build tools beyond a text editor. This improves maintainability and offers ease of access to programmers of all levels of experience.

This ReadMe does not attempt to fully describe the system. Instead, all documentation in online and accessed from the webapp. The best way to get an introduction to RBR is to visit the webapp at

[https://rbrcontrol.com](https://rbrcontrol.com)

The webapp is designed to work on a smartphone but can also be viewed in any PC browser.