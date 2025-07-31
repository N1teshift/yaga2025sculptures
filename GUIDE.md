# Deployment Guide

Operator manual for deploying the YAGA sculpture system to real hardware.
For development without the Pis, see `docker/README.md`.

## Prerequisites

| Role | Hardware |
|------|----------|
| Control node | PC/laptop, Windows 10/11 + WSL2 (Ubuntu 22.04) |
| Edge (×3) | Raspberry Pi, IQaudIO Pi-CodecZero HAT, mic + speaker, 16 GB+ SD card |

## 1. Control node (WSL2 + Ansible)

```powershell
# Admin PowerShell
wsl --install -d Ubuntu-22.04
```
Reboot, then in the Ubuntu shell:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install ansible -y
wsl -s Ubuntu-22.04          # default distro for Docker/ansible
```

## 2. Flash & prepare the Pis

1. Flash **Raspberry Pi OS Lite** to 3 SD cards (Raspberry Pi Imager).
2. Pre-set SSH + Wi-Fi in Imager's custom settings.
3. Boot each Pi and note its IP.

```bash
ssh-keygen -t rsa -b 4096
ssh-copy-id pi@PI1_IP
ssh-copy-id pi@PI2_IP
ssh-copy-id pi@PI3_IP
```

## 3. Inventory & backend

Edit `sculpture-system/edge/ansible/hosts.ini` with your IPs:
```ini
[sculptures]
sculpture1 ansible_host=PI1_IP id=1 control_host=CONTROL_NODE_IP
sculpture2 ansible_host=PI2_IP id=2 control_host=CONTROL_NODE_IP
sculpture3 ansible_host=PI3_IP id=3 control_host=CONTROL_NODE_IP

[sculptures:vars]
ansible_user=pi
ansible_ssh_private_key_file=~/.ssh/id_rsa
ansible_python_interpreter=/usr/bin/python3
```
Set the audio backend in `edge/ansible/group_vars/all.yml`: `audio_backend: alsa`
(recommended) or `pulse`.

## 4. Secrets (ansible-vault)

Production secrets live in encrypted `group_vars/vault.yml`. Set them up once:
```bash
bash docker/vault-setup.sh
```
See `sculpture-system/Vault.md` for rotating/editing. **Change the `changeme`
defaults before a real deployment.**

## 5. Deploy

```bash
# Edge devices
ansible-playbook -i sculpture-system/edge/ansible/hosts.ini \
  sculpture-system/edge/ansible/playbook.yml --vault-password-file .vault_pass

# Control node (requires sudo for systemd/icecast)
sudo ansible-playbook -i sculpture-system/server/ansible/hosts.ini \
  sculpture-system/server/ansible/playbook.yml --vault-password-file .vault_pass

# Verify reachability
ansible sculptures -i sculpture-system/edge/ansible/hosts.ini -m ping
```

The edge playbook installs packages, enables the IQaudIO HAT (I2S), converts
and copies samples, templates the agent/darkice configs, and installs the
systemd services. The server playbook installs Icecast2, Liquidsoap, Mosquitto
(with auth), Node-RED, and the `server-agent`, and templates all configs from
the vaulted secrets.

## 6. Verify

| Check | Command / URL |
|-------|--------------|
| Server services | `sudo systemctl status icecast2 liquidsoap mosquitto node-red server-agent` |
| Pi services | `sudo systemctl status darkice pi-agent player-live` (per Pi) |
| Icecast mounts | `http://CONTROL_NODE_IP:8000/admin/listmounts.xsl` — expect `s1/2/3-mic.ogg` + `mix-for-1/2/3.ogg` |
| Streams in VLC | `http://CONTROL_NODE_IP:8000/{s1-mic,mix-for-1}.ogg` |
| Dashboard | `http://CONTROL_NODE_IP:1880/ui` |
| Samples present | `ls /opt/sculpture-system/samples` (per Pi) |

No `mix-for-*` → Liquidsoap issue. No `s*-mic` → Darkice/mic issue; restart
Darkice on that Pi. Pi CPU load (via `htop`) should stay below 1.

## Known issues

**Ghost listeners on a mic mount.** A mount can accumulate fake listeners and
hit the 20-listener cap, making it unlistenable in VLC.
```bash
sudo systemctl restart darkice                 # on the affected Pi
# If unresolved:
sudo systemctl restart icecast2 liquidsoap      # on control node
sudo systemctl restart darkice                 # on each Pi
```

**Darkice buffer overruns.** Restart Darkice a few times; if persistent,
restart Icecast2 + Liquidsoap too.
