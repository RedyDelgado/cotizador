#!/bin/sh
# Primer arranque: si no hay perfiles.ini en el volumen, crea uno de demostración (correos de ejemplo, nada real).
set -e
if [ ! -f "$PERFILES_INI" ]; then
  cat > "$PERFILES_INI" <<'INI'
# Perfiles de demostración para probar en local. Se editan desde el panel (http://127.0.0.1:8787) o a mano.
[demo compras]
nota = Demostración: compras públicas en Cusco
correos = demo@example.com
palabras_clave = cemento,fierro,"sistema académico"
entidades = UNIQ
regiones = CUSCO
completo = si

[demo empleos]
nota = Demostración: ofertas de empleo
correos = empleo@example.com
empleo_palabras = ingeniero,abogado
empleo_regiones = CUSCO
empleo_sueldo_min = 3000
completo = no
INI
  echo "Creado $PERFILES_INI con dos perfiles de demostración."
fi
exec "$@"
