Read the following primer prompts:

https://easycoder.github.io/agent-primer-python.md
https://easycoder.github.io/agent-primer-js.md

The project is a heating control system. It's a client-server arrangement using MQTT as the comms mechanism.

The server is in the Controller folder and the main script is newController.ecs. This is written in the Python dialect of EasyCoder. The code runs on a dedicated machine in the premises being controlled.

The client is in the UI folder. It's a web application written in the JS dialect of EasyCoder and uses Webson for all DOM rendering. It runs on any smartphone. The entry point is index.html, which contains a loader to start up the main script.

The task is to tidy up where necessary and continue to complete the functionality required. We will do this step by step and confirm at each point.