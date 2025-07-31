#!/usr/bin/env bash
# One-time vault setup for the YAGA sculpture Ansible deployment.
#
# Run this from the WSL Ubuntu shell (after `wsl --install` + reboot):
#   bash docker/vault-setup.sh
#
# It:
#   1. installs ansible/ansible-vault if missing
#   2. copies group_vars/vault_example.yml -> group_vars/vault.yml
#      (for both edge and server playbooks)
#   3. encrypts those vault files with a password you type
#   4. writes a .vault_pass file (gitignored) so `ansible-playbook
#      --vault-password-file .vault_pass` works without retyping
#
# Change the placeholder passwords in vault_example.yml BEFORE running this for
# a real deployment.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Ensuring ansible is installed"
if ! command -v ansible-vault >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y ansible-core
fi

# Read or create the vault password file
VAULT_PASS_FILE="$REPO_ROOT/.vault_pass"
if [ ! -f "$VAULT_PASS_FILE" ]; then
  echo "==> No .vault_pass found — generating a random one (gitignored)"
  # ponytail: random 32-byte secret; edit it if you want a memorable passphrase
  openssl rand -base64 32 > "$VAULT_PASS_FILE"
  chmod 600 "$VAULT_PASS_FILE"
fi

for playbook_dir in edge/ansible server/ansible; do
  gv_dir="$REPO_ROOT/sculpture-system/$playbook_dir/group_vars"
  example="$gv_dir/vault_example.yml"
  target="$gv_dir/vault.yml"
  if [ -f "$example" ]; then
    cp "$example" "$target"
    ansible-vault encrypt --vault-password-file "$VAULT_PASS_FILE" "$target"
    echo "==> Encrypted $target"
  fi
done

echo
echo "Done. Deploy with, e.g.:"
echo "  ansible-playbook -i sculpture-system/edge/ansible/hosts.ini \\"
echo "    sculpture-system/edge/ansible/playbook.yml \\"
echo "    --vault-password-file .vault_pass"
