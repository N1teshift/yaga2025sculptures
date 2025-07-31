# YAGA 2025 Sculptures — Interactive Audio System

A distributed audio system for interactive sculpture installations: three
Raspberry Pi "sculptures", each capturing ambient audio and streaming it to a
central server that builds personalized, real-time mixes and plays them back
through each sculpture's speaker.

Successfully deployed at the **YAGA 2025** festival.

## Architecture

| Layer | Components |
|-------|-----------|
| **Edge** (3× Raspberry Pi) | DarkIce (mic → Icecast), MPV (playback), `pi-agent` (MQTT control), ALSA/PulseAudio |
| **Server** (Linux / WSL2) | Icecast2 (streaming), Liquidsoap (mixing), Mosquitto (MQTT), Node-RED (dashboard), `server-agent` (monitoring) |

**Audio flow:** capture → DarkIce → Icecast (`s{1-3}-mic.ogg`) → Liquidsoap
mix → Icecast (`mix-for-{1-3}.ogg`) → MPV → speaker.

**Control:** MQTT topics `sculpture/{id}/cmd`, `sculpture/{id}/status`,
`system/broadcast`, `system/plan`. Plans `A1, A2, B1, B2, B3, C, D` route
different source combinations to each mix.

## Repository layout

```
sculpture-system/
├── edge/            # Pi device: ansible/, pi-agent/, scripts/, darkice/, systemd/
├── server/          # Control node: ansible/, liquidsoap/, node-red/, server-agent/, icecast/
├── samples/         # Audio content
├── audio_config.yml # Shared audio + backend settings
└── playlists.yml    # Predefined playlists
docker/              # Dev harness (simulated Pis, no hardware needed)
```

## Develop without the hardware

The Pis are not required to work on this project. A Docker Compose harness runs
the full control plane plus **three simulated sculptures** executing the real
`pi-agent` code in `SIMULATION` mode (GPIO/ALSA/`vcgencmd` stubbed).

```bash
cp docker/.env.example docker/.env   # set passwords
docker compose up --build
```

Dashboard: `http://localhost:1880/ui` · Icecast: `http://localhost:8000/status.xsl`

See [`docker/README.md`](docker/README.md) for prerequisites (WSL2 + Docker
Desktop) and validation commands.

## Deploy to real hardware

Automated with Ansible:

```bash
ansible-playbook -i sculpture-system/edge/ansible/hosts.ini \
  sculpture-system/edge/ansible/playbook.yml --vault-password-file .vault_pass

ansible-playbook -i sculpture-system/server/ansible/hosts.ini \
  sculpture-system/server/ansible/playbook.yml --vault-password-file .vault_pass
```

Full setup, configuration and troubleshooting are in [`GUIDE.md`](GUIDE.md).
Production secrets are managed with ansible-vault — see
[`sculpture-system/Vault.md`](sculpture-system/Vault.md).

## Security

The control plane is hardened:

- **MQTT** requires authentication (Mosquitto password file).
- **Icecast / Liquidsoap** source/admin passwords are templated via ansible-vault.
- **Liquidsoap telnet API** is bound to `127.0.0.1` (no built-in auth).
- **Node-RED** editor is bound to `127.0.0.1` with localhost-restricted CORS.
- **Edge power commands** (reboot/shutdown over MQTT) are gated behind
  `ALLOW_POWER_COMMANDS=1` and an authenticated channel.

> The `docker/` harness uses local `.env` secrets (gitignored) for convenience
> only — not for production. Production secrets must come from ansible-vault.

## Requirements

- **Edge:** 3× Raspberry Pi, IQaudIO Pi-CodecZero HAT, mic + speaker, Raspberry Pi OS Lite.
- **Server:** Linux or Windows + WSL2 (Ubuntu 22.04).
- **Dev:** WSL2 + Docker Desktop (see `docker/README.md`).

## License

MIT — see [LICENSE.md](LICENSE.md).
