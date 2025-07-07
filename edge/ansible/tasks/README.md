# Edge Node Ansible Playbooks

This directory contains modular Ansible playbooks for configuring Raspberry Pi sculpture edge nodes. The playbooks have been broken down into logical, focused components that can be run independently or together.

## Playbook Structure

### Core Playbooks

1. **`system-setup.yml`** - System Dependencies & Hardware Configuration
   - Package management (update, upgrade, install)
   - WiFi power saving configuration
   - Audio hardware setup (boot config, overlays, I2S)
   - Base directory creation
   - **Tags**: `packages`, `network`, `hardware`, `directories`

2. **`audio-backend.yml`** - Audio Backend Specific Configuration
   - Conditional PulseAudio installation and configuration
   - Conditional ALSA configuration
   - Audio card detection and mixer setup
   - Darkice configuration templating
   - **Tags**: `packages`, `config`, `pulse`, `alsa`, `hardware`, `mixer`, `monitoring`

3. **`content-sync.yml`** - Media Content Management
   - Media directory creation
   - Audio file conversion and synchronization
   - File permissions management
   - **Tags**: `directories`, `validation`, `conversion`, `sync`, `permissions`, `cleanup`

4. **`ssh-access.yml`** - SSH Key Deployment
   - Server SSH key management
   - Pi user SSH directory setup
   - Key deployment for server-agent access
   - **Tags**: `ssh_keys`, `ssh_setup`

5. **`app-deploy.yml`** - Application & Service Deployment
   - Pi-agent application files installation
   - System modules and scripts deployment
   - Systemd service installation and management
   - Audio optimization and permissions
   - **Tags**: `app_files`, `app_modules`, `app_scripts`, `services`, `optimization`, `permissions`

### Orchestration

- **`deploy-all.sh`** - Shell script to run all playbooks in sequence
- **`playbook.yml`** - Original monolithic playbook (preserved)

## Usage Examples

### Complete Deployment (Same as Original)
```bash
# Run all components in sequence using the deployment script
chmod +x edge/ansible/deploy-all.sh
./edge/ansible/deploy-all.sh

# Or use the original monolithic playbook
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/playbook.yml
```

### Selective Deployment

Run individual components:

```bash
# Only system setup and hardware configuration
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/system-setup.yml

# Only audio backend configuration (conditional based on audio_config.yml)
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/audio-backend.yml

# Only content synchronization
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/content-sync.yml

# Only SSH access setup
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/ssh-access.yml

# Only application deployment
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/app-deploy.yml
```

### Tag-Based Execution

Use tags for even more granular control:

```bash
# Only install packages
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/system-setup.yml --tags packages

# Only PulseAudio configuration
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/audio-backend.yml --tags pulse

# Only audio file conversion and sync
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/content-sync.yml --tags conversion,sync

# Only systemd services
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/app-deploy.yml --tags services
```

### Development Workflow

During development, you can focus on specific areas:

```bash
# Development cycle: content changes
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/content-sync.yml

# Development cycle: application code changes
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/app-deploy.yml --tags app_files,app_modules

# Development cycle: service configuration changes
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/app-deploy.yml --tags services

# Development cycle: audio backend changes
ansible-playbook -i edge/ansible/hosts.ini edge/ansible/audio-backend.yml
```

## Configuration Dependencies

All playbooks use the same configuration files:
- `../../audio_config.yml` - Audio and system configuration
- `../../playlists.yml` - Playlist configuration

The audio backend configuration in `audio_config.yml` determines:
- Whether PulseAudio is installed and configured (`audio_backend: pulse`)
- Whether ALSA-only configuration is used (`audio_backend: alsa`)

## Benefits of Modular Structure

1. **Faster Development Cycles**: Only run the parts you're changing
2. **Easier Debugging**: Isolate issues to specific functional areas
3. **Selective Updates**: Update content without touching system configuration
4. **Better Organization**: Logical grouping of related tasks
5. **Maintainability**: Smaller, focused files are easier to understand and modify
6. **Conditional Logic**: Audio backend selection is clearly separated 