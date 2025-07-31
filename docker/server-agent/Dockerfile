FROM python:3.11-slim

RUN pip install --no-cache-dir paho-mqtt paramiko

WORKDIR /app

# server-agent/ is mounted read-only at runtime; copy to a writable dir so the
# agent can import its own modules and write its plan state file.
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
