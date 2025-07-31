FROM debian:bookworm-slim

# Stub update-rc.d so the icecast2 postinst doesn't abort in a container
# that has no runlevel symlinks (ponytail: container-only, never on the Pi).
RUN echo '#!/bin/sh' > /usr/sbin/update-rc.d \
    && chmod +x /usr/sbin/update-rc.d \
    && apt-get update && apt-get install -y --no-install-recommends \
        icecast2 \
        python3 \
        python3-pip \
        jq \
        wget \
    && rm -f /usr/sbin/update-rc.d \
    && pip3 install --no-cache-dir --break-system-packages jinja2 pyyaml \
    && rm -rf /var/lib/apt/lists/* \
    && getent group icecast2 >/dev/null || groupadd -r icecast2 \
    && getent passwd icecast2 >/dev/null || useradd -r -g icecast2 -d /var/log/icecast2 -s /usr/sbin/nologin icecast2 \
    && mkdir -p /etc/icecast2 /var/log/icecast2 /icecast \
    && chown -R icecast2:icecast2 /etc/icecast2 /var/log/icecast2 /icecast

# Run as the icecast2 system user (icecast2 refuses to run as root).
USER icecast2

WORKDIR /icecast
COPY render.py /icecast/render.py
COPY icecast.xml.j2 /icecast/icecast.xml.j2

# Render the icecast config from the template (passwords from env, changeme
# fallback) and launch icecast2 with the rendered file.
ENTRYPOINT ["sh", "-c", "python3 /icecast/render.py && exec icecast2 -c /etc/icecast2/icecast.xml"]
