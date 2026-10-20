#!/usr/bin/env bash
# Write a .env with a fresh DB password and WordPress salts.
#   scripts/new-env.sh [SITE_URL]
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -e .env ]; then echo ".env already exists; remove it first" >&2; exit 1; fi

rnd() { openssl rand -base64 48 | tr -d '\n/+='; }
SITE_URL=${1:-https://www.lajollatroop506.com}

{
    echo "SITE_URL=$SITE_URL"
    echo "WP_BIND=127.0.0.1"
    echo "WP_PORT=8080"
    echo "DB_PASSWORD=$(rnd)"
    for k in AUTH_KEY SECURE_AUTH_KEY LOGGED_IN_KEY NONCE_KEY AUTH_SALT SECURE_AUTH_SALT LOGGED_IN_SALT NONCE_SALT; do
        echo "WP_$k=$(rnd)"
    done
} > .env
chmod 600 .env
echo "Wrote .env for $SITE_URL"
