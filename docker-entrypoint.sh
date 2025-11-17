#!/bin/bash

set -euo pipefail

CURRENT_UID=$(id -u)
CONFIG_DIR="/home/appuser/.config/cdtui"

# Safety check: ensure not running as root
if [ "${CURRENT_UID}" -eq 0 ]; then
    echo "ERROR: Container must not run as root." >&2
    echo "Please use: docker run -u \$(id -u):\$(id -g) ..." >&2
    exit 1
fi

# Check if the directory exists but is not writable
if [ -d "${CONFIG_DIR}" ] && [ ! -w "${CONFIG_DIR}" ]; then
    echo "ERROR: Config directory ${CONFIG_DIR} exists but is not writable." >&2
    echo "This usually happens when the host directory doesn't exist and Docker creates it as root." >&2
    echo "Please create the host directory first:" >&2
    echo "  mkdir -p ~/.config/cdtui" >&2
    echo "Then run the container again." >&2
    exit 1
fi

# Create directory if it doesn't exist
mkdir -p "${CONFIG_DIR}"

# Execute the command as current user
exec "$@"
