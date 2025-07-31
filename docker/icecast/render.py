#!/usr/bin/env python3
"""Render icecast.xml.j2 for the sim harness.

Passwords come from ICECAST_ADMIN_PASSWORD / ICECAST_SOURCE_PASSWORD env
(defaulting to changeme). Mount points loop over sculpture_count (default 3).
"""
import os
import re
import yaml

CONFIG = "/icecast/icecast.xml.j2"
OUT = "/etc/icecast2/icecast.xml"


def main():
    ctx = {}
    if os.path.exists("/icecast/audio_config.yml"):
        with open("/icecast/audio_config.yml") as f:
            ctx.update(yaml.safe_load(f) or {})
    ctx["ansible_default_ipv4"] = {"address": os.environ.get("ICECAST_HOST", "0.0.0.0")}
    ctx["icecast_admin_password"] = os.environ.get("ICECAST_ADMIN_PASSWORD", "changeme")
    ctx["icecast_source_password"] = os.environ.get("ICECAST_SOURCE_PASSWORD", "changeme")
    ctx["sculpture_count"] = int(os.environ.get("SCULPTURE_COUNT", "3"))

    with open(CONFIG) as f:
        text = f.read()
    # Simple {{ var }} substitution (dotted keys too)
    def repl(m):
        key = m.group(1).strip()
        if key in ctx:
            return str(ctx[key])
        if "." in key:
            base, sub = key.split(".", 1)
            if base in ctx and isinstance(ctx[base], dict) and sub in ctx[base]:
                return str(ctx[base][sub])
        return m.group(0)
    text = re.sub(r"{{\s*([\w.]+)\s*}}", repl, text)

    with open(OUT, "w") as f:
        f.write(text)
    print("rendered icecast config ->", OUT)


if __name__ == "__main__":
    main()
