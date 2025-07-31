#!/usr/bin/env python3
"""Render the pi-agent .j2 templates into runnable .py files for the sim harness.

Reads audio_config.yml + playlists.yml for the Ansible vars the templates expect,
and renders every *.j2 under /app/pi-agent into /app/run. Templates with no Jinja
vars are copied verbatim.
"""
import os
import sys
import shutil

try:
    import yaml
except ImportError:
    # pyyaml may be absent in slim image; fall back to a tiny loader.
    yaml = None

from jinja2 import Environment, FileSystemLoader, select_autoescape

PI_AGENT_SRC = "/app/pi-agent"
RUN_DIR = "/app/run"


def load_yaml_vars():
    """Build the Jinja variable context from audio_config.yml + playlists.yml."""
    ctx = {}
    for fname in ("audio_config.yml", "playlists.yml"):
        path = f"/app/{fname}"
        if not os.path.exists(path):
            continue
        with open(path) as f:
            if yaml is not None:
                data = yaml.safe_load(f) or {}
            else:
                data = {}
            ctx.update(data)
    return ctx


def main():
    os.makedirs(RUN_DIR, exist_ok=True)
    ctx = load_yaml_vars()
    env = Environment(
        loader=FileSystemLoader(PI_AGENT_SRC),
        autoescape=select_autoescape(enabled_extensions=()),
        keep_trailing_newline=True,
    )
    rendered_any = False
    for name in os.listdir(PI_AGENT_SRC):
        src = os.path.join(PI_AGENT_SRC, name)
        if not os.path.isfile(src):
            continue
        dest = os.path.join(RUN_DIR, name[:-3] if name.endswith(".j2") else name)
        if name.endswith(".j2"):
            template = env.get_template(name)
            with open(dest, "w") as f:
                f.write(template.render(**ctx))
            rendered_any = True
            print(f"rendered {name} -> {os.path.basename(dest)}")
        else:
            shutil.copy(src, dest)
    if not rendered_any:
        print("WARNING: no .j2 templates found in /app/pi-agent", file=sys.stderr)
    # Ensure status_collector.py (plain .py) is present
    for needed in ("pi-agent.py", "audio_manager.py", "system_manager.py",
                   "status_collector.py", "gpio_utils.py", "mqtt_client.py",
                   "playlist_manager.py", "service_manager.py", "file_utils.py"):
        if not os.path.exists(os.path.join(RUN_DIR, needed)):
            print(f"WARNING: expected {needed} not produced", file=sys.stderr)


if __name__ == "__main__":
    main()
