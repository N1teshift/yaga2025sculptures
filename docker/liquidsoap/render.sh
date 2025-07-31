#!/bin/sh
# Render liquidsoap .liq templates for the sim harness.
# Vars come from audio_config.yml (mounted) + ICECAST_SOURCE_PASSWORD env.
set -e

CONFIG=/app/audio_config.yml
[ -f "$CONFIG" ] || CONFIG=/app/server/audio_config.yml

# Build a flat var file for envsubst-style rendering using python (jinja2-free,
# the .liq templates only use {{ audio_... }} and {{ darkice_quality }}).
python3 - <<'PY'
import os, re, yaml

cfg_path = "/app/audio_config.yml"
ctx = {}
if os.path.exists(cfg_path):
    with open(cfg_path) as f:
        ctx = yaml.safe_load(f) or {}

ice_pass = os.environ.get("ICECAST_SOURCE_PASSWORD", "changeme")

for name in ("main.liq", "presets.liq"):
    src = f"/app/liquidsoap/{name}"
    if not os.path.exists(src):
        src = f"/etc/liquidsoap/{name}"
    if not os.path.exists(src):
        continue
    with open(src) as f:
        text = f.read()
    # Substitute {{ var }} and {{ var | default("val") }}
    def repl(m):
        expr = m.group(1).strip()
        parts = [p.strip() for p in expr.split("|")]
        var = parts[0]
        default = None
        for p in parts[1:]:
            m2 = re.match(r'default\((["\'])(.*?)\1\s*\)', p.strip())
            if m2:
                default = m2.group(2)
        if var in ctx:
            return str(ctx[var])
        if "." in var:
            base, sub = var.split(".", 1)
            if base in ctx and isinstance(ctx[base], dict) and sub in ctx[base]:
                return str(ctx[base][sub])
        if var == "control_host":
            return os.environ.get("CONTROL_HOST", "localhost")
        if default is not None:
            return default
        return m.group(0)
    text = re.sub(r"{{\s*([\w.\s|()\'\"]+)\s*}}", repl, text)
    # Inject icecast password into main.liq output.icecast blocks
    text = text.replace('password="hackme"', f'password="{ice_pass}"')
    # In the harness, expose telnet on all interfaces (server-agent is a separate container)
    text = text.replace('settings.server.telnet.bind_addr.set("127.0.0.1")',
                        'settings.server.telnet.bind_addr.set("0.0.0.0")')
    with open(f"/etc/liquidsoap/{name}", "w") as f:
        f.write(text)
    print(f"rendered {name}")
PY
