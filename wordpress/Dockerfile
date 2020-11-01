FROM wordpress:latest

RUN apt-get update \
    && apt-get install -y git less  \
    && rm -rf /var/lib/apt/lists/* \
    && docker-php-ext-install pdo pdo_mysql
    
WORKDIR /var/www/html

RUN git clone -b v1.8.5 https://github.com/q2a/question2answer.git qa
  
RUN ls 
WORKDIR /var/www/html/qa

COPY qa-config.php . 
RUN ls && pwd
RUN mv .htaccess-example .htaccess
    
ADD uploads.ini /usr/local/etc/php/conf.d/uploads.ini
ADD htaccess /var/www/html/.htaccess
