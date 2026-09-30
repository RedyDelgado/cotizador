#!/usr/bin/env bash
# Instala o actualiza el bot en /opt/cotizaciones-uniq, aislado del resto del servidor.
# Uso, desde la carpeta del proyecto copiada al VPS:   sudo bash install.sh
# Idempotente: volver a correrlo actualiza el código sin tocar .env ni data/.
set -euo pipefail

APP=/opt/cotizaciones-uniq
USR=cotizbot
HORA_LIMA="07:00"   # hora de envío, en hora de Lima
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

confirmar() { read -rp "$1 [s/N] " r; [[ ${r,,} == s* ]]; }

[[ $EUID -eq 0 ]] || { echo "Ejecuta: sudo bash $0"; exit 1; }
[[ -f $SRC/bot.py ]] || { echo "No encuentro bot.py junto a install.sh"; exit 1; }

echo "== 1. Python =="
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' \
  || { echo "Se necesita Python >= 3.10; hay $(python3 -V 2>&1)"; exit 1; }
PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python $PYV OK"
PRUEBA=$(mktemp -d)
if ! python3 -m venv "$PRUEBA/v" >/dev/null 2>&1; then
  echo "Falta el módulo venv de Python. Comando necesario:"
  echo "    apt-get install -y python${PYV}-venv"
  echo "(solo agrega el módulo venv; no cambia el Python del sistema ni toca R-Uno)"
  confirmar "¿Ejecutarlo ahora?" || { rm -rf "$PRUEBA"; exit 1; }
  apt-get install -y "python${PYV}-venv"
fi
rm -rf "$PRUEBA"

cat <<EOF

Se va a hacer, y nada más:
  - crear el usuario de sistema '$USR' (sin sudo, shell nologin) si no existe
  - copiar el bot a $APP (propietario $USR, permisos 750; .env en 600)
  - crear $APP/venv e instalar requirements.txt DENTRO del venv
  - poner la tarea diaria ($HORA_LIMA hora de Lima) en el crontab de '$USR'
No se toca /var/www, Nginx/Apache, PHP, MySQL ni los crontab de root/www-data. No se abren puertos.
EOF
confirmar "¿Continuar?" || exit 1

echo "== 2. Usuario =="
if id "$USR" &>/dev/null; then
  echo "Ya existe '$USR'"
else
  useradd --system --shell /usr/sbin/nologin --home-dir "$APP" --no-create-home "$USR"
  echo "Creado '$USR'"
fi

echo "== 3. Archivos =="
install -d -o "$USR" -g "$USR" -m 750 "$APP" "$APP/data" "$APP/logs"
install -o "$USR" -g "$USR" -m 640 "$SRC"/{bot.py,uniq.py,seace.py,informe.py,test_bot.py,requirements.txt,README.md,.env.example,perfiles.ini.example} "$APP/"
if [[ ! -f $APP/.env ]]; then
  if [[ -f $SRC/.env ]]; then
    cp "$SRC/.env" "$APP/.env"
  else
    cp "$SRC/.env.example" "$APP/.env"
    echo "AVISO: completa los datos de Gmail en $APP/.env  (sudo nano $APP/.env)"
  fi
fi
chown "$USR:$USR" "$APP/.env"
chmod 600 "$APP/.env"
cd "$APP"   # el cwd de root puede no ser legible para $USR

echo "== 4. Entorno virtual =="
[[ -x $APP/venv/bin/python ]] || runuser -u "$USR" -- python3 -m venv "$APP/venv"
runuser -u "$USR" -- "$APP/venv/bin/pip" install --quiet --no-cache-dir --upgrade -r "$APP/requirements.txt"
runuser -u "$USR" -- "$APP/venv/bin/python" "$APP/test_bot.py"

echo "== 5. Cron =="
# El cron de Ubuntu/Debian ignora CRON_TZ: se traduce la hora de Lima a la hora del servidor.
echo "Zona horaria del servidor: $(timedatectl show -p Timezone --value 2>/dev/null || date +%Z)"
read -r MIN HORA < <(date -d "TZ=\"America/Lima\" $HORA_LIMA" '+%M %H')
echo "$HORA_LIMA en Lima = $HORA:$MIN en el servidor"
LINEA="$MIN $HORA * * * $APP/venv/bin/python $APP/bot.py >/dev/null 2>>$APP/logs/cron.err"
{ crontab -u "$USR" -l 2>/dev/null | grep -vF "$APP/bot.py" || true; echo "$LINEA"; } | crontab -u "$USR" -
crontab -u "$USR" -l

echo "== 6. Prueba --dry-run como $USR =="
SALIDA=$(runuser -u "$USR" -- "$APP/venv/bin/python" "$APP/bot.py" --dry-run)
head -n 40 <<<"$SALIDA"
echo "... (salida completa: sudo -u $USR $APP/venv/bin/python $APP/bot.py --dry-run)"
echo "-- últimas líneas del log --"
tail -n 5 "$APP/logs/bot.log"

cat <<EOF

Listo. Para enviar el primer correo real:
  sudo -u $USR $APP/venv/bin/python $APP/bot.py
EOF
