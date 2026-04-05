# chat

To add chat to a project you need the chat server to be running somewhere, subscribing to its own MQTT topic.

The UI is handled by index.html, which uses MQTT to request files from the server and creates the browser screen. All interaction goes through MQTT too.

Various credentials are required. These are expected to reside in a JSON file above the root of the UI server. They comprise the following:

```json
{
    "broker":"**********",
    "username":"***********",
    "password":"***********"
}
```

A JSON configuration file is also required by the server:
```json
{
    "id": "<Server ID>",
    "title": "<Title of the UI screen>"
}
```
