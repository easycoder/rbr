# Room By Room Control

An Open Source project to build a smart central heating system with control over the Internet.

This project uses commercially-available WiFi-connected modules - a temperature sensor and a relay module - and electrically-powered radiator valves, to automate domestic (or other) central heating on a room-by-room basis. The cost of the system is typically one fifth of the annual running cost of a domestic heating system, and since it can save 10% or more of the annual heating cost by making better use of heating it can pay for itself in the first couple of years.

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

