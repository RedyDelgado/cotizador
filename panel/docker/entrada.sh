#!/bin/sh
# Prepara la base de datos y el administrador en cada arranque (idempotente), y luego lanza el servidor.
set -e
cd /app
[ -f "$DB_DATABASE" ] || touch "$DB_DATABASE"
if [ -z "$APP_KEY" ]; then
  # sin APP_KEY en el entorno: se genera una y se guarda en el volumen para que las sesiones sobrevivan
  [ -f /data/app.key ] || php -r 'echo "base64:".base64_encode(random_bytes(32));' > /data/app.key
  export APP_KEY="$(cat /data/app.key)"
fi
php artisan migrate --force
php artisan db:seed --force
exec "$@"
