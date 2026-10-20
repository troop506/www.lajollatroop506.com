#!/usr/bin/env bash
# Build a clean standalone site from a raw export of blog 8 on the old
# multisite, load it into this stack, and write a canonical clean dump.
#
#   scripts/import-from-multisite.sh [RAW_DIR]
#
# RAW_DIR (default ../../_export/blog8) must contain:
#   sql/blog8-tables.sql.gz   mysqldump of every wp_8_* table
#   sql/global-tables.sql.gz  mysqldump of wp_users wp_usermeta wp_site wp_sitemeta wp_blogs
#   uploads-raw/              copy of wp-content/uploads/sites/8/
#
# Outputs:
#   data/uploads/                  uploads with planted .htaccess, PHP and logs removed
#   data/troop506-clean.sql.gz     cleaned DB using https://www.lajollatroop506.com
# and, if SITE_URL in .env differs, rewrites the running DB's URLs to SITE_URL.

set -euo pipefail
cd "$(dirname "$0")/.."

RAW=${1:-../../_export/blog8}
CANONICAL=https://www.lajollatroop506.com
set -a; source .env; set +a
SITE_URL=${SITE_URL:-$CANONICAL}

wp()  { docker compose exec -T -u www-data wordpress wp --skip-plugins --skip-themes "$@"; }
sql() { docker compose exec -T db mariadb -uwordpress -p"$DB_PASSWORD" wordpress; }

echo "==> Copying uploads (dropping .htaccess, scripts, logs)"
mkdir -p data/uploads
rsync -a --delete \
    --exclude='.htaccess' --exclude='*.php*' --exclude='*.phtml' --exclude='*.phar' \
    --exclude='wc-logs/' \
    "$RAW/uploads-raw/" data/uploads/

echo "==> Starting stack"
docker compose up -d --build --wait

echo "==> Loading raw multisite tables"
wp db reset --yes
gunzip -c "$RAW/sql/global-tables.sql.gz" | sql
gunzip -c "$RAW/sql/blog8-tables.sql.gz" | sql

echo "==> Converting to standalone and cleaning"
sql < scripts/convert-multisite.sql

wp search-replace 'wp-content/uploads/sites/8/' 'wp-content/uploads/' --all-tables --precise --report-changed-only
wp search-replace 'http://www.lajollatroop506.com' "$CANONICAL" --all-tables --precise --report-changed-only
# Plain SQL: WP_HOME/WP_SITEURL constants make wp-cli refuse these options.
echo "UPDATE wp_options SET option_value='$CANONICAL' WHERE option_name IN ('siteurl','home');" | sql
wp option update active_plugins --format=json '[
  "flexible-product-fields/flexible-product-fields.php",
  "google-sitemap-generator/sitemap.php",
  "hide-title/dojo-digital-hide-title.php",
  "kadence-blocks/kadence-blocks.php",
  "redirection/redirection.php",
  "ultimate-addons-for-gutenberg/ultimate-addons-for-gutenberg.php",
  "woocommerce/woocommerce.php",
  "wp-mail-smtp/wp_mail_smtp.php",
  "wpforms-lite/wpforms.php"
]'
docker compose exec -T -u www-data wordpress wp core update-db

echo "==> Writing data/troop506-clean.sql.gz"
docker compose exec -T db mariadb-dump -uwordpress -p"$DB_PASSWORD" --single-transaction wordpress \
    | gzip > data/troop506-clean.sql.gz

if [ "$SITE_URL" != "$CANONICAL" ]; then
    echo "==> Pointing running site at $SITE_URL"
    wp search-replace "$CANONICAL" "$SITE_URL" --all-tables --precise --report-changed-only
fi

docker compose exec -T -u www-data wordpress wp rewrite flush
docker compose exec -T -u www-data wordpress wp cache flush
echo "==> Done: $SITE_URL"
