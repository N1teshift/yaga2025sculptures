FROM python:3.11-slim

# paho-mqtt 2.x (CallbackAPIVersion required) — see mqtt_client.py.j2
RUN pip install --no-cache-dir paho-mqtt jinja2 pyyaml

WORKDIR /app

# Copy the renderer (renders .j2 pi-agent templates -> .py at startup)
COPY render.py /app/render.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# pi-agent/ and audio_config.yml/playlists.yml are mounted read-only at runtime
# (see docker-compose.yml volumes). Rendered output goes to /app/run (writable).

CMD ["/app/entrypoint.sh"]
