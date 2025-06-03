# Room By Room Control

This is an Open Source project to build a smart central heating system with control over the Internet. There are several "Smart Home" products available that broadly fit that description, but none have gained significant traction in the general home market. This one is different, because RBR Heating recognise that the barrier to setting up a home control system is not one of cost but of complexity. Our aim is to build a system that requires little expertise to install or run, and where all of the more complicated aspects of setup are done before delivery.

## What makes RBR special? ##
 1. RBR is designed to be a "distributed appliance"; that is, something that can be set up before delivery and just plugged in, with none of the usual messing about with IP addresses that plagues the smart home world. No technical knowledge on the part of the end user is required; just the ability (and willingness) to program a central heating controller.
 2. A key feature of the system is that it can be externally managed. The remote UI permits one of any number of systems to be selected at will, and each system can be designated as being controllable by any desired number of managers. So for example, a housing association can assign a set of installations to be managed by one or more nominated persons. All this is done by the remote UI app - a mobile web page that will run on any smartphone.
 3. The RBR system is open, so anyone can build systems that use it.
 4. RBR collect statistics on temperatures and radiator on-off times, that can be used to optimise heating profiles and reduce annual costs. The statistical data, which contains no personal information, may be used to provide insights into the relationship betwen heating use and weather or other factors, but the specific data values are not given to anyone except the owners of the systems providing them.

This project uses commercially-available BLE and WiFi-connected modules - a temperature sensor and a relay - and electrically-powered radiator valves, to automate domestic (or other) central heating on a room-by-room basis. The cost of the system is typically about a fifth of the annual running cost of a domestic heating system, and since it can save 10% or more of the annual heating cost by making better use of heating it can pay for itself in the first couple of years.

## This repository ##

The repository software is in 4 parts:

  1. A system controller. This was originally designed to run on an Orange Pi Zero 2 computer, but others will serve equally well. The OS is assumed to be Debian and all the controller code is Python.
  1. A local user interface coded in Python and using the Qt graphics toolkit. This is currently under development, so right now only the remote interface is useable.
  1. A REST server on public shared hosting. This is coded in PHP.
  1. A remote user interface, built as a browser-based mobile webapp. This is coded in JavaScript.

Third-party tools are kept to a minimum. The project relies mainly on other products in the EasyCoder repository:

  - A high level scripting language coded in Python for the system controller and local user interface
  - A similar high-level scripting language coded in JavaScript for the remote user interface
  - A Python engine for rendering graphics expressed as JSON
  - A JavaScript engine for rendering DOM structures expressed as JSON
  - An extended MarkDown processor for documentation, based on the third-party _Showdown_ markdown library

The system requires no software framework, nor any build tools beyond a text editor. This improves maintainability and offers ease of access to programmers of all levels of experience.

The remote UI is a webapp designed to work on a smartphone but it can also be viewed in a PC browser. It can be found at

[https://rbrheating.com/ui](https://rbrheating.com/ui)

## Repository structure ##

There are two items of primary interest in the repo:

 - The RBR-Now dorectory contains a set of MicroPython files for ESP32-based devices such as relays and thermometers, that uses the ESP-Now comms protocol to accept commands and requests from the system controller.
 - The roombyroom directory contains files for the local system controller and the remote web-based user interface:
   - The system controller files are for either an Orange Pi based controller or a Linaro (IXHUB) industrial PC, both running Debian Linux. The Orange Pi version is current code in daily use and the Linarian is under development with the aim of becoming the standard product.
   - The server files are held on the rbrheating.com website. They run the remote user interface and the database.
 - Other files are for a configuration program to set up ESP32-based devices and a local user interface for the Linaro controller that is under development

## Call for collaborators ##

This project has been developed by one person - me. It controls my central heating and that of a friend, but we'd like to spread the knowledge. I'm getting on in years so I won't be able to support it for very much longer. Anyone who is interested in joining will be most welcome. No strings are attached and I'll give as much help as I can to get you up the learning curve. The project uses some unusual programming techniques designed to help casual programmers get familiar with the product, but underneath it's all pure JavaScript, Python and PHP.
