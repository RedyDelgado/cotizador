#!/usr/bin/env bash
# Prepara deploy/vps/.env para el panel de NEOESTADO en el VPS (una sola vez; volver a correrlo pregunta antes de pisar).
# No toca ningún otro proyecto: solo escribe archivos dentro de esta carpeta y, si aceptas, agrega 3 líneas al .env del bot.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

confirmar() { read -rp "$1 [s/N] " r; [[ ${r,,} == s* ]]; }
pedir() {  # pedir VARIABLE "Pregunta" [valor por defecto] [oculto]
    local valor
    if [[ ${4:-} == oculto ]]; then read -rsp "$2: " valor; echo; else read -rp "$2${3:+ [$3]}: " valor; fi
    valor=${valor:-${3:-}}
    [[ $valor == *"'"* ]] && { echo "No uses comillas simples (')."; exit 1; }
    printf -v "$1" '%s' "$valor"
}

if [[ -f .env ]] && ! confirmar "Ya existe .env. ¿Reemplazarlo? (se guarda una copia en .env.respaldo)"; then
    echo "Sin cambios."; exit 0
fi
[[ -f .env ]] && cp .env .env.respaldo

IP_DETECTADA=$(hostname -I | awk '{print $1}')
echo "== Datos del panel =="
pedir PANEL_HOST "IP pública del VPS" "$IP_DETECTADA"
pedir ADMIN_EMAIL "Tu correo para entrar al panel"
pedir ADMIN_PASSWORD "Tu contraseña del panel (mínimo 10 caracteres)" "" oculto
(( ${#ADMIN_PASSWORD} >= 10 )) || { echo "La contraseña debe tener al menos 10 caracteres."; exit 1; }

echo "== Clave previa (la pide el navegador antes del login) =="
pedir BASIC_USER "Usuario" "neoestado"
pedir BASIC_PASS "Contraseña (distinta de la del panel, mínimo 10)" "" oculto
(( ${#BASIC_PASS} >= 10 )) || { echo "La contraseña debe tener al menos 10 caracteres."; exit 1; }
BASIC_HASH=$(docker run --rm caddy:2.10-alpine caddy hash-password --plaintext "$BASIC_PASS")

echo "== Telegram (déjalo vacío si aún no tienes el bot) =="
pedir TELEGRAM_BOT_TOKEN "Token de @BotFather" "" oculto
pedir TELEGRAM_BOT_USERNAME "Usuario del bot, sin @"

PANEL_BOT_TOKEN=$(openssl rand -hex 24)

umask 077
# Comillas simples: Docker Compose no interpreta los $ del hash de la clave.
cat > .env <<EOF
APP_NAME='NEOESTADO'
APP_URL='https://${PANEL_HOST}:8443'
PANEL_HOST='${PANEL_HOST}'
ADMIN_NAME='Administrador'
ADMIN_EMAIL='${ADMIN_EMAIL}'
ADMIN_PASSWORD='${ADMIN_PASSWORD}'
PANEL_BOT_TOKEN='${PANEL_BOT_TOKEN}'
BASIC_USER='${BASIC_USER}'
BASIC_HASH='${BASIC_HASH}'
TELEGRAM_BOT_TOKEN='${TELEGRAM_BOT_TOKEN}'
TELEGRAM_BOT_USERNAME='${TELEGRAM_BOT_USERNAME}'
TELEGRAM_API_URL='https://api.telegram.org'
EOF
echo "Listo: $(pwd)/.env (permisos 600, no se sube a GitHub)."

BOT_ENV=/opt/cotizaciones-uniq/.env
if [[ -f $BOT_ENV ]]; then
    echo
    echo "El bot necesita saber dónde está el panel. Se agregarían a $BOT_ENV (solo las que falten):"
    echo "  PANEL_URL=http://127.0.0.1:8010   PANEL_TOKEN=(el token generado)   TELEGRAM_BOT_TOKEN=(el de arriba)"
    if confirmar "¿Agregarlas? (se guarda una copia en ${BOT_ENV}.respaldo)"; then
        cp -p "$BOT_ENV" "${BOT_ENV}.respaldo"
        grep -q '^PANEL_URL=' "$BOT_ENV" || echo "PANEL_URL=http://127.0.0.1:8010" >> "$BOT_ENV"
        grep -q '^PANEL_TOKEN=' "$BOT_ENV" || echo "PANEL_TOKEN=${PANEL_BOT_TOKEN}" >> "$BOT_ENV"
        if [[ -n $TELEGRAM_BOT_TOKEN ]] && ! grep -q '^TELEGRAM_BOT_TOKEN=' "$BOT_ENV"; then
            echo "TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}" >> "$BOT_ENV"
        fi
        echo "Agregadas. Si PANEL_TOKEN ya existía, cámbialo a mano por el nuevo: está en $(pwd)/.env"
    fi
fi

cat <<EOF

Siguiente:
  docker compose up -d --build                 # levanta el panel (la primera vez tarda unos minutos)
  bash /root/cotizador/install.sh              # agrega al bot el envío inmediato tras cada pago
Luego entra a  https://${PANEL_HOST}:8443  (el navegador avisará del certificado: Avanzado → Continuar).
EOF
