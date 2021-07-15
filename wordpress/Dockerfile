FROM wordpress:5.7-php7.4-apache


RUN apt-get update \
    && apt-get install -y git less  \
    && rm -rf /var/lib/apt/lists/* \
    && docker-php-ext-install pdo pdo_mysql
    
WORKDIR /var/www/html
    
ADD uploads.ini /usr/local/etc/php/conf.d/uploads.ini
ADD htaccess /var/www/html/.htaccess