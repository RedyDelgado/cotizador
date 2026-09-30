# Monitor de Contrataciones Públicas

Todos los días a las 07:00 (hora de Lima) envía **un informe** por correo, con este orden:

1. **Resumen ejecutivo**: coincidencias, nuevas, por cerrar (2 días o menos) y cotizaciones UNIQ
   activas, más una frase que lo resume.
2. **Cotizaciones UNIQ activas**: todas, por fecha límite, marcando las que coinciden con tus
   palabras clave.
3. **Entidades que sigues** (si defines `ENTIDADES`): todo lo que tienen abierto, sin filtrar por
   palabra clave.
4. **Coincidencias por palabra clave**: una tabla por cada palabra clave con los procesos de todas
   las fuentes, ordenados por fecha de cierre, con etiquetas NUEVO / CIERRA PRONTO / fuente, el
   enlace a la ficha oficial y a las bases. Si una palabra clave trae 60 resultados o más, el
   informe te sugiere afinarla.
5. **Regiones que sigues** (si defines `REGIONES`): todo lo abierto en esas regiones o provincias.
6. **Fichas técnicas** de las cotizaciones UNIQ: datos del sistema y el extracto del **TDR/EETT**
   para decidir si cotizar (ítems y cantidades, objetivo, **requisitos del proveedor**, plazo y
   lugar, pago, adelantos, garantías, penalidades y características técnicas).
7. **Fuentes**: estado de cada fuente.

Por defecto (`INFORME_COMPLETO=si`) todo sale en detalle cada día, aunque el correo sea largo:
Gmail muestra la primera parte y el resto con "Ver mensaje completo", y por eso lo buscado
específicamente (UNIQ, entidades, palabras clave) va arriba y las regiones, que son lo más largo,
después. Con `INFORME_COMPLETO=no` el informe se mantiene bajo el límite de Gmail: lo ya informado
sale en una línea y solo las cotizaciones UNIQ nuevas llevan ficha.

Fuentes, todas públicas, oficiales y sin login ni captcha:

| Fuente | Qué trae | Actualización |
|---|---|---|
| UNIQ · [Cotizaciones en línea](https://cotizaciones.uniq.edu.pe/cotizaciones/ver_cotizaciones) | todas las cotizaciones activas y su TDR/EETT | tiempo real |
| SEACE · [Contrataciones menores](https://prod6.seace.gob.pe/buscador-publico/contrataciones) | hasta 8 UIT, cotización abierta o por abrir | tiempo real |
| SEACE · [Oportunidades de Negocio](https://prod4.seace.gob.pe/openegocio/) | licitaciones, concursos, subastas y comparación de precios con el **registro de participantes abierto**, con cronograma y bases | lo que está abierto hoy |

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

## Entidades que sigues

Para ver todo lo que publica una entidad, sin depender de palabras clave:

```
ENTIDADES=MUNICIPALIDAD PROVINCIAL DE LA CONVENCION
```

Basta una parte del nombre, tal como aparece en el SEACE; no importan tildes ni mayúsculas. Varias
entidades van separadas por coma. Las contrataciones menores de una entidad salen si su región
está en `REGIONES`.

## Regiones que sigues

Para ver todo lo abierto en una zona (gobierno regional, municipalidades provinciales y
distritales, redes de salud, UGEL, universidades, empresas públicas…):

```
REGIONES=CUSCO,MADRE DE DIOS,APURIMAC/ABANCAY,APURIMAC/COTABAMBAS
```

`CUSCO` trae todo el departamento; `APURIMAC/ABANCAY` solo esa provincia. Los nombres van como en
el SEACE (sin importar tildes ni mayúsculas); si uno no existe, la tabla de fuentes lo dice. Lo que
ya salió en "Entidades que sigues" no se repite aquí.

## Archivos

| | |
|---|---|
| `bot.py` | orquesta: lee las fuentes, arma el informe y lo envía |
| `uniq.py` | cotizaciones UNIQ y lectura del TDR/EETT |
| `seace.py` | búsquedas en SEACE (contrataciones menores y Oportunidades de Negocio) y la regla de coincidencia |
| `informe.py` | diseño del correo (HTML y texto) |
| `test_bot.py` | autoprueba sin red: `python test_bot.py` |
| `.env` | credenciales, palabras clave, entidades y regiones (a partir de `.env.example`); permisos 600, **no se versiona** |
| `data/estado.json` | lo que salió en el informe anterior (para marcar lo nuevo) y la provincia de cada distrito ya consultado |
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
