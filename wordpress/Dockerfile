# syntax=docker/dockerfile:1
#
# Troop 506 WordPress image.
#
# All code (core, theme, plugins) is baked into the image and nothing under
# /var/www/html is kept except wp-content/uploads: pristine-entrypoint.sh
# wipes the rest on every start, so any PHP dropped by an attacker is gone
# after a restart. DISALLOW_FILE_MODS
# (see docker-compose.yaml) stops anyone installing or editing PHP from
# wp-admin. To update core or a plugin, change the version here and rebuild.
#
# The theme comes from the sibling troop506-theme repo via the `theme`
# additional build context defined in docker-compose.yaml.

FROM wordpress:6.9-php8.3-apache

RUN apt-get update \
    && apt-get install -y --no-install-recommends less mariadb-client unzip \
    && rm -rf /var/lib/apt/lists/*

# wp-cli
RUN curl -fsSL -o /usr/local/bin/wp https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar \
    && chmod +x /usr/local/bin/wp

# Plugins, fetched fresh from wordpress.org (never copied from the old server).
ARG PLUGINS="\
    woocommerce.11.2.1 \
    flexible-product-fields.2.14.9 \
    kadence-blocks.3.8.0.1 \
    ultimate-addons-for-gutenberg.2.20.5 \
    wpforms-lite.2.0.2.2 \
    wp-mail-smtp.4.10.2 \
    redirection.5.10.1 \
    google-sitemap-generator.4.1.25 \
    hide-title"

RUN set -eux; \
    cd /usr/src/wordpress/wp-content/plugins; \
    rm -rf akismet hello.php; \
    for p in $PLUGINS; do \
        curl -fsSL -o /tmp/p.zip "https://downloads.wordpress.org/plugin/$p.zip"; \
        unzip -q /tmp/p.zip; \
        rm /tmp/p.zip; \
    done; \
    cd /usr/src/wordpress/wp-content/themes; \
    find . -mindepth 1 -maxdepth 1 ! -name twentytwentyfive ! -name index.php -exec rm -rf {} +

COPY --from=theme . /usr/src/wordpress/wp-content/themes/troop506-theme
RUN rm -rf /usr/src/wordpress/wp-content/themes/troop506-theme/.git \
           /usr/src/wordpress/wp-content/themes/troop506-theme/README.md \
    && chown -R www-data:www-data /usr/src/wordpress/wp-content

COPY uploads.ini /usr/local/etc/php/conf.d/uploads.ini
COPY apache-hardening.conf /etc/apache2/conf-enabled/hardening.conf

COPY --chmod=755 pristine-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["pristine-entrypoint.sh"]
CMD ["apache2-foreground"]
