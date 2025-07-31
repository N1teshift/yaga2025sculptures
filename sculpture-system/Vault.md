# Ansible Vault — Production Secrets

The hardened deploy (mosquitto auth, Icecast/Liquidsoap passwords) reads its
secrets from **ansible-vault**-encrypted files. This keeps the production path
consistent with the `docker/` dev harness, which uses a local `.env` instead.

## Layout

```
sculpture-system/{edge,server}/ansible/
├── group_vars/
│   ├── all.yml            # non-secret shared vars (sculpture_count, etc.)
│   ├── vault.yml          # ENCRYPTED secrets (gitignored)
│   └── vault_example.yml  # plaintext template — edit, then encrypt
```

Secret variable names (defined in `vault.yml`, consumed by the playbooks):

| Variable | Used by | Purpose |
|----------|---------|---------|
| `vault_icecast_admin_password` | server | Icecast admin + source auth |
| `vault_icecast_source_password` | server + edge | Darkice→Icecast source password |
| `vault_mqtt_password` | server | Mosquitto `sculpture` user password |

The playbooks map these to `icecast_admin_password`, `icecast_source_password`
and `mqtt_password` (with a `changeme` fallback so a dry render still works
without the vault).

## Setup (one-time, in WSL)

```bash
bash docker/vault-setup.sh
```

This installs ansible-core if needed, copies each `vault_example.yml` to
`vault.yml`, encrypts it, and writes a gitignored `.vault_pass`.

## Change a secret later

```bash
ansible-vault edit --vault-password-file .vault_pass \
  sculpture-system/server/ansible/group_vars/vault.yml
```

## Deploy with the vault

```bash
ansible-playbook -i sculpture-system/edge/ansible/hosts.ini \
  sculpture-system/edge/ansible/playbook.yml \
  --vault-password-file .vault_pass

ansible-playbook -i sculpture-system/server/ansible/hosts.ini \
  sculpture-system/server/ansible/playbook.yml \
  --vault-password-file .vault_pass
```

> The `.vault_pass` file is gitignored. For CI, inject it as a secret and never
> commit it. Rotate it with `ansible-vault rekey`.
