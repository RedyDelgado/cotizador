# Monitor de Contrataciones Públicas

Todos los días a las 07:00 (hora de Lima) envía **un informe** por correo, con este orden:

1. **Resumen ejecutivo**: coincidencias, nuevas, por cerrar (2 días o menos) y cotizaciones UNIQ
   activas, más una frase que lo resume.
2. **Coincidencias por palabra clave**: una tabla por cada palabra clave con los procesos de todas
   las fuentes, ordenados por fecha de cierre, con etiquetas NUEVO / CIERRA PRONTO / fuente y el
   enlace a la ficha oficial. Los procedimientos ya informados otros días se resumen en una línea.
3. **Cotizaciones UNIQ activas**: todas, por fecha límite, marcando las que coinciden con tus
   palabras clave.
4. **Fichas técnicas** de las cotizaciones UNIQ nuevas: datos del sistema y el extracto del
   **TDR/EETT** para decidir si cotizar (ítems y cantidades, objetivo, **requisitos del proveedor**,
   plazo y lugar, pago, adelantos, garantías, penalidades y características técnicas).
5. **Fuentes y método**: estado de cada fuente y cómo se calculan las coincidencias.

Fuentes, todas públicas y sin login:

| Fuente | Qué trae | Actualización |
|---|---|---|
| UNIQ · [Cotizaciones en línea](https://cotizaciones.uniq.edu.pe/cotizaciones/ver_cotizaciones) | todas las cotizaciones activas y su TDR/EETT | tiempo real |
| SEACE · [Contrataciones menores](https://prod6.seace.gob.pe/buscador-publico/contrataciones) | hasta 8 UIT, cotización abierta o por abrir | tiempo real |
| OECE · [Contrataciones Abiertas](https://contratacionesabiertas.oece.gob.pe) | licitaciones, subastas, concursos y adjudicaciones de los últimos 30 días | ~2 días de desfase |

El buscador clásico de SEACE 3.0 tiene reCAPTCHA, así que no se usa.

Si una fuente no responde, el informe sale igual con un aviso de "informe incompleto". Si no
responde ninguna, llega un correo de **alerta**. Si un día no hay nada, igual llega el informe.

Diseño: informe institucional (encabezado, secciones numeradas, tablas de datos, etiquetas de
estado) con la paleta de Tailwind (navy, blue y gray, contraste AA) e iconos Lucide, los mismos de
`lucide-react`. Sin emojis. Un correo no ejecuta React ni Tailwind y Gmail descarta clases y SVG,
así que los estilos van en línea y los iconos se adjuntan como PNG.

## Palabras clave

Van en `PALABRAS_CLAVE` del `.env`, separadas por coma:

```
PALABRAS_CLAVE=software,"sistema académico",sistema de seguridad ciudadana
```

| Escribes | Encuentra |
|---|---|
| `software` | la palabra y sus variantes (softwares) |
| `sistema de seguridad ciudadana` | procesos con **todas** esas palabras, en cualquier parte de la descripción |
| `"sistema académico"` | entre comillas, las palabras tienen que ir **juntas**: "sistema de gestión académica" sí, "sistema de aire acondicionado para servicios académicos" no |

No distingue tildes ni mayúsculas, pero escríbelas con tilde: los buscadores oficiales sí las
distinguen y el bot busca las dos versiones ("maíz" y "maiz"). Si una palabra clave trae resultados
que no sirven, ponla entre comillas o hazla más específica. Un proceso que calza con dos palabras
clave sale solo en la primera.

## Archivos

| | |
|---|---|
| `bot.py` | orquesta: lee las fuentes, arma el informe y lo envía |
| `uniq.py` | cotizaciones UNIQ y lectura del TDR/EETT |
| `seace.py` | búsquedas en SEACE y OECE, y la regla de coincidencia |
| `informe.py` | diseño del correo (HTML y texto) |
| `test_bot.py` | autoprueba sin red: `python test_bot.py` |
| `.env` | credenciales y palabras clave (a partir de `.env.example`); permisos 600, **no se versiona** |
| `data/estado.json` | lo que salió en el informe anterior, para marcar lo nuevo |
| `logs/bot.log` | log con rotación (1 MB × 3); `logs/cron.err` solo si Python se cae |

Opciones: `--dry-run` imprime el informe en consola sin enviar y `--html-preview` lo guarda en
`preview.html`. Ninguna de las dos actualiza el estado.

## Gmail: contraseña de aplicación

1. Activa la verificación en 2 pasos en la cuenta que va a enviar.
2. Crea una contraseña de aplicación en <https://myaccount.google.com/apppasswords>.
3. Ponla en `SMTP_PASS` (con o sin espacios). **No** es tu contraseña normal.

## Instalación en el VPS

Copia la carpeta al servidor (sin `.env` si no quieres que viaje) y ejecuta el instalador:

```bash
scp -r Cotizador usuario@vps:/tmp/cotizador
ssh usuario@vps
sudo bash /tmp/cotizador/install.sh
sudo nano /opt/cotizaciones-uniq/.env      # si avisó que falta completarlo
```

El instalador muestra lo que va a hacer y pide confirmación. Crea el usuario de sistema
`cotizbot` (sin sudo, sin login), copia todo a `/opt/cotizaciones-uniq`, crea un `venv` propio,
instala el cron **solo en el crontab de `cotizbot`** y hace una prueba `--dry-run`.
No toca `/var/www`, Nginx/Apache, PHP, MySQL, el Python del sistema ni otros crontabs, y no abre puertos.

Para **actualizar** el código: copia la versión nueva y vuelve a correr `install.sh`
(no pisa `.env` ni `data/`).

## Uso diario

```bash
# ejecutar a mano (envía el correo de verdad)
sudo -u cotizbot /opt/cotizaciones-uniq/venv/bin/python /opt/cotizaciones-uniq/bot.py

# probar sin enviar
sudo -u cotizbot /opt/cotizaciones-uniq/venv/bin/python /opt/cotizaciones-uniq/bot.py --dry-run

# ver logs (al final de cada ejecución registra la memoria máxima usada)
sudo tail -n 50 /opt/cotizaciones-uniq/logs/bot.log
sudo cat /opt/cotizaciones-uniq/logs/cron.err

# ver el cron
sudo crontab -l -u cotizbot
```

**Cambiar destinatarios o palabras clave:** edita `MAIL_TO` o `PALABRAS_CLAVE` (separados por
coma) con `sudo nano /opt/cotizaciones-uniq/.env`. Vale desde la siguiente ejecución. La sintaxis
de las palabras clave está en la sección [Palabras clave](#palabras-clave).

**Cambiar la hora:** cambia `HORA_LIMA` al inicio de `install.sh` y vuelve a correrlo.
El cron de Ubuntu ignora `CRON_TZ`, así que el instalador traduce la hora de Lima a la hora del
servidor (en un VPS en UTC, 07:00 Lima = 12:00). Si el servidor usa una zona con horario de verano,
vuelve a correr `install.sh` después de cada cambio de hora.

## Desinstalar todo

```bash
sudo crontab -r -u cotizbot
sudo rm -rf /opt/cotizaciones-uniq
sudo userdel cotizbot
```

## En Windows (desarrollo)

```bash
pip install -r requirements.txt
python bot.py --dry-run --html-preview
```
