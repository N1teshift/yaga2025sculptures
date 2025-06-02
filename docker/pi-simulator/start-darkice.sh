#!/bin/bash
set -e

# Default to SCULPTURE_ID 0 if not set, though it should be set by docker-compose
SCULPTURE_ID=${SCULPTURE_ID:-0}

CONFIG_TEMPLATE="/opt/sculpture-system/darkice.cfg.template"
GENERATED_CONFIG="/tmp/darkice_s${SCULPTURE_ID}.cfg"

# Replace placeholders in the template and create the instance-specific config
sed "s/{{SCULPTURE_ID}}/${SCULPTURE_ID}/g" "${CONFIG_TEMPLATE}" > "${GENERATED_CONFIG}"

echo "Starting DarkIce for Sculpture ${SCULPTURE_ID} with config ${GENERATED_CONFIG}..."

# Log the generated configuration to the service journal for debugging
echo "--- Generated DarkIce Config (${GENERATED_CONFIG}) ---"
cat "${GENERATED_CONFIG}"
echo "--- End of DarkIce Config ---"

# Start DarkIce
exec /usr/bin/darkice -c "${GENERATED_CONFIG}" 