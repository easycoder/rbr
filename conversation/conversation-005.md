# 2026-08-23

## 09:40

I'm looking at diagnose.as. I was aware the Z2M console is at localhost:8080, but what is at port 8889?

**Assistant**

Port 8889 is the RBR zigbee bridge (zigbee-bridge.py, service rbr-zigbee-bridge.service) — a small local HTTP→MQTT translation layer between the controller and zigbee2mqtt. 8080 = z2m's own web UI (talks to the MQTT broker on 1883); 8889 = the controller's device API. deviceControl.as speaks plain HTTP, not MQTT, so the bridge translates HTTP requests into zigbee2mqtt/{name}/set publishes and keeps a state cache from its zigbee2mqtt/# subscription, plus the dead-device detection tiers. Endpoints: /health, /devices, /device/{name}, /device/{name}?state=on|off. Binds to 127.0.0.1 only (zigbee-config.json: broker localhost:1883, http_port 8889) — that's why diagnose.as uses http://127.0.0.1:8889. So 8080 = manage the zigbee network; 8889 = the API the controller actually uses to command relays and read device states.
