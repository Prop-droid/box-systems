# smart-home

Mosquitto + Zigbee2MQTT + Home Assistant in Docker on the agent box (installed 2026-11-19).

- Compose: `~/systems/smart-home/docker-compose.yml`. Run docker as `sg docker -c '...'`.
- Data (not in git, holds the Zigbee network key): `/home/tomas/smart-home/{mosquitto,z2m,ha}`.
- Home Assistant: `:8123` (host network). Zigbee2MQTT page: `:8080` (LAN + tailnet, no auth).
- MQTT broker: `127.0.0.1:1883` on the box, `mosquitto:1883` inside the compose network. Anonymous, not exposed to the LAN.
- Coordinator: Sonoff ZBDongle-P (CC2652P, adapter `zstack`), `/dev/serial/by-id/usb-ITead_Sonoff_Zigbee_3.0_USB_Dongle_Plus_44e36a...`. Zigbee channel 25.
- Agents drive devices with MQTT: publish to `zigbee2mqtt/<friendly_name>/set`, e.g. `{"state":"ON"}`.

Start / update: `cd ~/systems/smart-home && sg docker -c 'docker compose pull && docker compose up -d'`
Stop: `sg docker -c 'docker compose stop'` (same directory)
Logs: `sg docker -c 'docker logs --tail 50 zigbee2mqtt'`
