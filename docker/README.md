# Docker Dev Harness

Simulates the whole YAGA sculpture system **without the real Raspberry Pis**,
so the control plane, mixing engine, dashboard and monitoring can be developed
and validated on a normal machine.

```
mosquitto ─┬─ edge-1 (sim pi-agent, SCULPTURE_ID=1)
           ├─ edge-2 (sim pi-agent, SCULPTURE_ID=2)
           ├─ edge-3 (sim pi-agent, SCULPTURE_ID=3)
           ├─ liquidsoap ── icecast2
           ├─ node-red (dashboard)
           └─ server-agent (monitoring/reconciliation)
```

The edge agents run the **real** `sculpture-system/edge/pi-agent/*.j2`
templates, rendered at container start, in `SIMULATION=1` mode. In simulation,
`gpio_utils` / `audio_manager` / `status_collector` stub out all hardware
(GPIO, ALSA/PulseAudio, `vcgencmd`) so the agents exercise the MQTT command
flow, mode switching, plan handling and status publishing without sound cards.

## Prerequisites (one-time, machine setup)

These are NOT in this repo — install them on the host:

1. **WSL 2** (admin PowerShell):
   ```powershell
   wsl --install -d Ubuntu-22.04
   ```
   Reboot when prompted.
2. **Docker Desktop** (Windows): install, enable the **WSL2 backend**, and set
   the default distro to Ubuntu-22.04 (`wsl -s Ubuntu-22.04`).
3. Verify from a WSL terminal:
   ```bash
   wsl -e docker info
   ```

## Run

```bash
# from this directory (sculpture-system/../docker)
cp .env.example .env        # then edit passwords
docker compose up --build
```

- Dashboard: http://localhost:1880/ui  (Node-RED is bound to localhost inside
  the container; map the port as needed)
- Icecast status: http://localhost:8000/status.xsl
- MQTT (authenticated): localhost:1883, user `sculpture`, password from `.env`

## Validate the control flow

```bash
# Watch a simulated sculpture's status
docker compose logs -f edge-1

# Switch plan to B1 and confirm liquidsoap updates
docker compose exec mosquitto mosquitto_pub -h localhost -p 1883 \
  -u sculpture -P "$MQTT_PASSWORD" -t system/plan -m '{"plan":"B1"}'

# Publish a volume command to sculpture 1
docker compose exec mosquitto mosquitto_pub -h localhost -p 1883 \
  -u sculpture -P "$MQTT_PASSWORD" -t sculpture/1/cmd -m '{"volume":0.7}'
```

## What is stubbed vs real

| Component | In harness |
|-----------|-----------|
| MQTT broker (mosquitto) | real, with auth |
| Icecast2 | real |
| Liquidsoap mixing + telnet API | real (telnet bound to 127.0.0.1) |
| Node-RED dashboard | real |
| server-agent monitoring | runs; SSH log-tailing disabled via `SSH_SIMULATION=1` |
| Edge pi-agent logic | real (rendered templates) |
| GPIO / ALSA / PulseAudio / mic hardware | **stubbed** (SIMULATION) |

For a real deployment, use the Ansible playbooks under
`sculpture-system/{edge,server}/ansible` — they template the same source files
and supply secrets via ansible-vault.
