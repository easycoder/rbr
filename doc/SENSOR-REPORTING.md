# Sensor reporting intervals

A thermometer that reports only when the temperature moves goes quiet in steady weather, and RBR reads a reading older than 45 minutes as missing. The fix is to give the device a maximum reporting interval, so it sends a heartbeat even when nothing changes. That setting belongs to the device, not to RBR: Zigbee attribute reporting is stored by the sensor itself, and Zigbee2MQTT is the tool that writes it.

> **Audience:** maintainer · **Status:** draft · **Last verified:** 2026-11-15

## Why RBR cares

`controller.allspeak` warns at 45 minutes without a reading (2,700,000 ms) and fails at 60 (3,600,000 ms). While a reading is missing the room's relay is held off — a room cools gently rather than heating without feedback — and the interface shows the last known value with a soft warning. A report every ten or fifteen minutes keeps every room inside that gate even when the weather does nothing.

The trade-off is battery. A shorter maximum means more radio time, so set the longest interval that still sits inside the gate: ten minutes leaves a wide margin, and fifteen is still comfortable. `reportable_change` matters as much as the interval — it is what turns a temperature move into an early report, and leaving it coarse means the room reacts slowly to a door being opened.

The reason the defaults are not enough is in Zigbee2MQTT's own converter. A temperature sensor described with the standard `temperature` and `humidity` extensions is configured for a minimum of 10 seconds, a **maximum of one hour** and a change of 1.0 °C — an hour is longer than the 45-minute gate, and a whole degree is a slow trigger for a room that has just had a door opened. Shortening the maximum and tightening the change is the whole of this procedure.

## Which devices accept it

Zigbee reporting is configured per cluster and attribute, and support is per device. Most mains and battery sensors accept it; some Xiaomi models refuse, and the response then says so. This procedure was written for a SONOFF SNZB-02DR2 in the Sunroom, whose device page confirms it is a sleepy battery sensor with the usual temperature, humidity and battery clusters — but the commands below have not yet been run against that device from this controller, so treat the first attempt as the test: a `"status":"ok"` reply, and a report on the device's own topic inside the chosen interval, is what proves it took.

A battery sensor is a sleepy end device: it is asleep most of the time, so the command is queued and delivered at its next check-in. Press the button on the back of the sensor to wake it, then send within a few seconds. A request sent to a sleeping device simply times out.

## Read the current configuration

```bash
mosquitto_sub -h 127.0.0.1 -t 'zigbee2mqtt/bridge/response/#' -v &
mosquitto_pub -h 127.0.0.1 -t zigbee2mqtt/bridge/request/device/reporting/read \
  -m '{"id":"Sunroom-thermometer","endpoint":1,"cluster":"msTemperatureMeasurement","configs":[{"attribute":"measuredValue"}]}'
```

`id` is the device's **friendly name** in Zigbee2MQTT, which under the RBR naming convention is the room name with `-thermometer` or `-radiator` after it — the same name the app's Devices sheet shows. `mosquitto_sub -h 127.0.0.1 -t 'zigbee2mqtt/bridge/devices' -C 1` lists them all if you are unsure of the spelling. `endpoint` 1 is the sensor's single endpoint and `measuredValue` is the attribute behind both temperature and humidity; if a request is refused, the reply names the cluster or attribute it could not configure.

## Set it

```bash
# Temperature: report at least every 10 minutes, and on any 0.2 °C move.
mosquitto_pub -h 127.0.0.1 -t zigbee2mqtt/bridge/request/device/reporting/configure \
  -m '{"id":"Sunroom-thermometer","endpoint":1,"cluster":"msTemperatureMeasurement","attribute":"measuredValue","minimum_report_interval":60,"maximum_report_interval":600,"reportable_change":20}'

# Humidity: the same, with a 1 %RH change.
mosquitto_pub -h 127.0.0.1 -t zigbee2mqtt/bridge/request/device/reporting/configure \
  -m '{"id":"Sunroom-thermometer","endpoint":1,"cluster":"msRelativeHumidity","attribute":"measuredValue","minimum_report_interval":60,"maximum_report_interval":600,"reportable_change":100}'
```

`minimum_report_interval` and `maximum_report_interval` are in seconds; `reportable_change` is in the attribute's own hundredths, so 20 is 0.2 °C and 100 is 1 %RH. A maximum of 65535 switches reporting off entirely, which is not what a heating system wants. Watch `zigbee2mqtt/bridge/response/#` for `"status":"ok"`; anything else names the reason.

The generator in `rbr-setup.sh` writes `allow_anonymous true` for the controller's local listener in `/etc/mosquitto/conf.d/rbr-local.conf`, which is why these need no credentials when run on the controller. If a box has been locked down, add `-u`/`-P` for one of the accounts in that file, or for the credentials in the `mqtt:` block of `/opt/zigbee2mqtt/data/configuration.yaml`. The client tools come with the broker on most images; if `mosquitto_pub` is missing, `sudo apt-get install mosquitto-clients`.

On an older Zigbee2MQTT the topic is `zigbee2mqtt/bridge/request/device/configure_reporting`; the newer `…/device/reporting/configure` is the current name and the old one remains an alias.

## When the Zigbee2MQTT frontend refuses

The frontend's Devices page has the same settings under a Reporting tab, and it can fail with:

```
bridge/device/request/reporting/configure: Cannot send, WebSocket not open
```

That message is about the **page's own WebSocket to Zigbee2MQTT**, not about the device: the HTML loaded but the socket is down, so nothing was sent. It is not a reason to touch the sensor. Reload the page first — a tab left open across a Zigbee2MQTT restart keeps the dead socket and every action fails this way. Then check that the address reaches the frontend directly (`http://<controller>:8080`); a proxy or tunnel has to pass the `Upgrade` header, and one that strips it gives exactly this symptom. A page served over HTTPS cannot open a `ws://` socket at all. The MQTT commands above work regardless, which is why they are the procedure of record here.

## Verify, and what persists

```bash
mosquitto_sub -h 127.0.0.1 -t 'zigbee2mqtt/Sunroom-thermometer' -v
```

With a ten-minute maximum the topic should publish at least every ten minutes with nothing changing, and the room's Info sheet in the app should show a matching "N min ago".

The configuration lives in the device's own memory, so a Zigbee2MQTT restart, a controller reboot or a firmware update that does not reset the NVRAM leaves it in place. Two things do overwrite it: re-pairing the sensor (or factory-resetting it), and asking Zigbee2MQTT to reconfigure the device — the frontend's **Reconfigure** button, or `zigbee2mqtt/bridge/request/device/configure` — which re-applies the converter's one-hour default. So a room that goes quiet again months later, or after a device has been re-interviewed, is not a mystery: read the configuration back, and set the interval again if it has gone. A replaced device needs it as part of commissioning.

## What RBR does not do

RBR deliberately has no interface for this. Intervals are per device, per cluster and per vendor, the values that suit one sensor are wrong for the next, and a wrong one shows up as a room that reports too seldom or a battery that dies early — so it stays a maintenance procedure rather than a setting in the app. The controller only cares that a reading arrives inside its gate; how the sensor was told to send it is not its business.
