FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        liquidsoap \
        python3-yaml \
        python3-pip \
        jq \
    && pip3 install --no-cache-dir --break-system-packages jinja2 pyyaml \
    && rm -rf /var/lib/apt/lists/*

# Render .liq templates with Ansible vars (audio_config.yml) + icecast password.
WORKDIR /etc/liquidsoap
COPY render.sh /usr/local/bin/render-liquidsoap.sh
RUN chmod +x /usr/local/bin/render-liquidsoap.sh

# main.liq and presets.liq are mounted read-only; rendered output to /etc/liquidsoap
CMD ["sh", "-c", "render-liquidsoap.sh && exec liquidsoap /etc/liquidsoap/main.liq"]
