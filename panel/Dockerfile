# Panel de administración de suscriptores (Laravel). SQLite: no usa MySQL ni toca otras aplicaciones.
# Estilos: Tailwind compilado con Vite (nada se descarga del navegador en producción)
FROM node:22-alpine AS assets
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY vite.config.js ./
COPY resources ./resources
RUN npm run build

FROM php:8.4-cli-alpine

RUN apk add --no-cache git unzip \
    && docker-php-ext-install bcmath pcntl
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-interaction --no-scripts --prefer-dist

COPY . .
COPY --from=assets /app/public/build public/build
RUN composer dump-autoload --no-interaction \
    && mkdir -p storage/framework/{cache,sessions,views} storage/logs bootstrap/cache /data \
    && chmod -R a+rwX storage bootstrap/cache /data

COPY docker/entrada.sh /entrada.sh
RUN chmod +x /entrada.sh

ENV DB_CONNECTION=sqlite DB_DATABASE=/data/database.sqlite
EXPOSE 8000
ENTRYPOINT ["/entrada.sh"]
CMD ["php", "artisan", "serve", "--host=0.0.0.0", "--port=8000"]
