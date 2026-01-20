<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Can ESPHome be accessed remotely over the internet, say from a web app running mobile phone to check on or activate a schedule?

Yes, ESPHome devices can be accessed remotely over the internet from a mobile web app, but it requires a secure intermediary like your IXHUB hub or a VPN/MQTT setup since direct port-forwarding is insecure and not recommended.[^1][^2]

## Recommended: Use IXHUB as secure remote gateway

Since you have the IXHUB tablet as a central Linux hub, run a web app or MQTT broker there to proxy all remote access:[^3][^4]

```yaml
# On ESP devices - enable MQTT (without native API)
mqtt:
  broker: your-ixhub-ip  # Or public MQTT like flespi.io
  username: !secret mqtt_user
  password: !secret mqtt_pass
  topic_prefix: esp/seasonal-hub
```

- **IXHUB services**: MQTT broker (Mosquitto), Node.js web app querying ESP states via MQTT/web API, served securely over HTTPS.[^5][^6]
- Mobile app connects to IXHUB's public domain/IP (via Cloudflare Tunnel or port-forward HTTPS/443), checks statuses, changes season profiles, triggers schedules.[^7]

***

## VPN for direct device access

Set up WireGuard VPN on the IXHUB or router, then connect your phone to the VPN to reach ESPHome web servers as if local:[^8][^7]

```yaml
# On ESP - enable web_server
web_server:
  port: 80
  auth:
    username: admin
    password: !secret web_pass
```

- Phone VPN client → IXHUB VPN server → local network → ESP `http://esp-ip/sensors`, `http://esp-ip/select/season_profile`.[^1][^8]
- Secure, no public ports needed beyond VPN (UDP 51820).[^7]

***

## Cloudflare Tunnel (zero port forwarding)

Install Cloudflare Tunnel on IXHUB to expose a secure dashboard without router changes:[^7]

- Tunnel forwards `yourdomain.com/esphome` → IXHUB web app → ESP devices.
- Handles auth, HTTPS, DDoS protection automatically.[^7]

***

## Direct ESPHome native API (not recommended standalone)

ESPHome's native API works over the internet if port-forwarded (UDP/TCP 6053), but exposes encryption keys and lacks built-in auth—use only behind VPN/proxy.[^9]

**Best practice for your setup:** MQTT → IXHUB web app → Cloudflare Tunnel. This lets a mobile PWA check statuses, select seasons, and trigger actions with full security.[^6][^5][^7]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16]</span>

<div align="center">⁂</div>

[^1]: https://community.home-assistant.io/t/esphome-web-server-in-access-point-mode-without-home/342296

[^2]: https://www.reddit.com/r/Esphome/comments/1332l2a/remote_access_to_esphome/

[^3]: https://www.youtube.com/watch?v=0XH61uCqMDw

[^4]: https://esphome.io/guides/getting_started_command_line/

[^5]: https://community.home-assistant.io/t/esphome-from-remote-location/143720

[^6]: https://www.reddit.com/r/homeassistant/comments/s1bh22/esphome_http_request_to_read_sensor_values_from_a/

[^7]: https://www.espboards.dev/blog/homeassistant-public-access/

[^8]: https://esphome.io/components/wireguard/

[^9]: https://esphome.io/components/api/

[^10]: https://www.reddit.com/r/Esphome/comments/1jcj897/esphome_without_home_assistant/

[^11]: https://www.facebook.com/groups/HomeAssistant/posts/2381364445468245/

[^12]: https://www.youtube.com/watch?v=WrCF9Gdstuc

[^13]: https://www.youtube.com/watch?v=BX6tDsux_X4

[^14]: https://github.com/esphome/feature-requests/issues/1688

[^15]: https://esphome.io/projects/

[^16]: https://www.youtube.com/watch?v=yzpnxgpa-w8

