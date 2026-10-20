#!/bin/sh
# The base image declares VOLUME /var/www/html, so code would otherwise
# survive container restarts and recreates. Wipe everything except uploads
# on every start; the stock entrypoint then copies fresh core, plugins and
# theme from /usr/src/wordpress and regenerates wp-config.php from the env.
set -e
find /var/www/html -mindepth 1 -maxdepth 1 ! -name wp-content -exec rm -rf {} +
if [ -d /var/www/html/wp-content ]; then
    find /var/www/html/wp-content -mindepth 1 -maxdepth 1 ! -name uploads -exec rm -rf {} +
fi
exec docker-entrypoint.sh "$@"
