#!/bin/sh
# Seed mosquitto password file from the MQTT_PASSWORD env (dev harness only).
set -e
PASSWD_FILE=/mosquitto/config/passwd
touch "$PASSWD_FILE"
if ! mosquitto_passwd -b "$PASSWD_FILE" sculpture "${MQTT_PASSWORD:-changeme}" 2>/dev/null; then
  echo "seeding mosquitto password..."
  mosquitto_passwd -c -b "$PASSWD_FILE" sculpture "${MQTT_PASSWORD:-changeme}"
fi
exec /usr/sbin/mosquitto -c /mosquitto/config/mosquitto.conf
