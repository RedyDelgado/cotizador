# Monitor de Contrataciones Públicas

Todos los días a las 07:00 (hora de Lima) envía **un informe** por correo, con este orden:

1. **Resumen ejecutivo**: coincidencias, nuevas, por cerrar (2 días o menos) y cotizaciones UNIQ
   activas, más una frase que lo resume.
2. **Cotizaciones UNIQ activas**: todas, por fecha límite, cada una con el enlace a su TDR/EETT
   (el documento completo), marcando las que coinciden con tus palabras clave.
3. **Entidades que sigues** (si defines `ENTIDADES`): todo lo que tienen abierto, sin filtrar por
   palabra clave.
4. **Coincidencias por palabra clave**: una tabla por cada palabra clave con los procesos de todas
   las fuentes, ordenados por fecha de cierre, con etiquetas NUEVO / CIERRA PRONTO / fuente, el
   enlace a la ficha oficial y a las bases. **Si el perfil define `regiones`, las palabras clave se
   buscan solo ahí**; sin regiones, en todo el país. Si una palabra clave trae 60 resultados o más,
   el informe te sugiere afinarla.
5. **Regiones que sigues** (si defines `REGIONES`): todo lo abierto en esas regiones o provincias,
   sin repetir lo que ya salió en las secciones anteriores.
6. **Fuentes**: estado de cada fuente.

Por defecto (`INFORME_COMPLETO=si`) todo sale en detalle cada día, aunque el correo sea largo.
Gmail solo muestra los primeros ~102 KB del cuerpo y esconde el resto detrás de "Ver mensaje
completo", así que el informe se protege de tres formas:

- **Índice al inicio** ("Resultados por búsqueda"): cada palabra clave, entidad y región con cuántos
  resultados dio y cuántos son nuevos. Siempre está en la parte visible, así se ve que todas las
  búsquedas se hicieron aunque el detalle de las últimas quede recortado.
- **Aviso** arriba cuando el correo pasa del límite.
- **Adjunto** (`informe-AAAA-MM-DD.html`) con el informe entero, que Gmail no recorta; se abre en
  el navegador.

Lo buscado específicamente (UNIQ, entidades, palabras clave) va arriba y las regiones, que son lo
más largo, después. Con `INFORME_COMPLETO=no` el informe se mantiene bajo el límite de Gmail: lo ya
informado sale en una línea.

**Ubicación:** cada proceso de SEACE muestra región › provincia › distrito (por ejemplo, *Cusco ›
La Convención › Santa Ana*): el lugar de entrega de sus ítems y, si falta, el de la entidad. Se
consulta una vez por proceso y queda guardada en `data/estado.json`, así que cada día solo se
consulta lo nuevo (la primera vez tarda unos 40 segundos).

Fuentes, todas públicas, oficiales y sin login ni captcha:

| Fuente | Qué trae | Actualización |
|---|---|---|
| UNIQ · [Cotizaciones en línea](https://cotizaciones.uniq.edu.pe/cotizaciones/ver_cotizaciones) | todas las cotizaciones activas y su TDR/EETT | tiempo real |
| SEACE · [Contrataciones menores](https://prod6.seace.gob.pe/buscador-publico/contrataciones) | hasta 8 UIT, cotización abierta o por abrir | tiempo real |
| SEACE · [Oportunidades de Negocio](https://prod4.seace.gob.pe/openegocio/) | licitaciones, concursos, subastas y comparación de precios con el **registro de participantes abierto**, con cronograma y bases | lo que está abierto hoy |

El buscador clásico de SEACE 3.0 tiene reCAPTCHA, así que no se usa.

Si una fuente no responde, el informe sale igual con un aviso de "informe incompleto". Si no
responde ninguna, llega un correo de **alerta**. Si un día no hay nada, igual llega el informe.

Marca: el informe lleva el logo de NEOESTADO (`assets/logo.png`, se incrusta en el correo) y una
paleta violeta que combina con él. Para cambiar el logo, reemplaza ese archivo (PNG cuadrado, unos
360 px); si falta, el informe sale igual, sin logo.

Diseño: informe institucional (encabezado, secciones numeradas, tablas de datos, etiquetas de
estado) con la paleta de Tailwind (violeta y gris, contraste AA) e iconos Lucide, los mismos de
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

## Un informe distinto por persona (perfiles)

Por defecto todos los correos de `MAIL_TO` reciben el mismo informe. Si quieres que cada uno reciba
cosas distintas, copia `perfiles.ini.example` como `perfiles.ini` y define un bloque por persona o grupo:

```ini
[redy]
correos = redy.delgado@gmail.com
palabras_clave = software,"sistema académico",sistema de seguridad ciudadana
entidades = UNIQ,LA CONVENCION,MUNICIPALIDAD DISTRITAL DE ECHARATI
regiones = CUSCO
completo = si

[grupo indescar]
correos = Grupoindescar@gmail.com
palabras_clave = cemento,fierro,maíz
regiones = CUSCO,MADRE DE DIOS
completo = no
```

La UNIQ es una entidad más: **solo quien la escribe en `entidades` recibe sus cotizaciones en línea**
(además de lo que tenga abierto en SEACE). En el ejemplo, `redy` la recibe y `grupo indescar` no.

| Clave | Qué hace |
|---|---|
| `correos` | uno o varios destinatarios del bloque, separados por coma (obligatoria) |
| `palabras_clave`, `entidades`, `regiones` | lo que sigue ese bloque, con la misma sintaxis de arriba; todas opcionales. **Las palabras clave se buscan solo en las `regiones` del bloque**; si no tiene regiones, en todo el país |
| `uniq` | (opcional) `si`: recibir las cotizaciones de la UNIQ sin ponerla en `entidades`. Por defecto `no` |
| `completo` | `si` (por defecto) o `no`: informe entero cada día, o lo ya informado resumido |
| `pausado` | `si`: no se le envía nada hasta que lo quites (por defecto `no`) |
| `nota` | texto libre para ti; no sale en el correo |
| `empleo_palabras`, `empleo_regiones`, `empleo_sueldo_min` | ofertas de empleo, ver [Ofertas de empleo](#ofertas-de-empleo) |

- **Lo NUEVO es propio de cada bloque:** a cada uno se le marca lo que no vio en su último correo.
- **Las fuentes se consultan una sola vez** aunque haya varios bloques: agregar personas no suma carga
  a los portales ni al VPS.
- **Un bloque que falla no impide los demás.** El aviso técnico va a `MAIL_ALERTAS` (o a `MAIL_TO`, o al
  primer bloque si no defines ninguno).
- **El archivo se valida:** una clave mal escrita, un correo inválido o un bloque que no sigue nada
  dan un error claro en el log y en el aviso.
- **Con `perfiles.ini`**, `MAIL_TO`, `PALABRAS_CLAVE`, `ENTIDADES`, `REGIONES` e `INFORME_COMPLETO` del
  `.env` dejan de usarse. La cuenta que envía (`SMTP_USER`, `SMTP_PASS`) sigue ahí. Sin `perfiles.ini`
  todo funciona como antes.
- El archivo lleva correos personales: **no se versiona** (está en `.gitignore`). En el VPS se crea a
  partir del ejemplo: `cp /opt/cotizaciones-uniq/perfiles.ini.example /opt/cotizaciones-uniq/perfiles.ini`
  y se edita con `nano`; el instalador no lo pisa.

## Ofertas de empleo

Además de las contrataciones, un bloque puede recibir ofertas de trabajo de dos portales oficiales:
**Empleos Perú** (MTPE, sector privado y público) y **Talento Perú** (SERVIR, sector público). Se activan con
cualquiera de estas claves del bloque:

```ini
[maria]
correos = maria@example.com
empleo_palabras = ingeniero,"asistente administrativo",abogado
empleo_regiones = CUSCO,APURIMAC/ABANCAY
empleo_sueldo_min = 3000
```

- `empleo_palabras` se busca en el **título** de la oferta (mismas reglas y comillas que `palabras_clave`).
  Sin palabras, recibe todas las ofertas de sus regiones.
- `empleo_regiones`: si falta, se usan las `regiones` del bloque; si tampoco hay, todo el país.
- `empleo_sueldo_min`: quita lo que paga menos. Las ofertas que no publican sueldo se siguen mostrando
  ("Sueldo no indicado"). Empleos Perú publica rangos (2,500–2,999): se compara con el tope del rango.
- En el correo sale la sección **Ofertas de empleo** (una tabla por palabra o por región), con lugar
  (región › provincia › distrito), sueldo, entidad, fecha de cierre (SERVIR) o de publicación, y lo nuevo marcado.
- Sin regiones, SERVIR se consulta por palabra clave (por país serían 387 páginas); con regiones se recorre
  cada departamento (Cusco, unas 19 páginas). SERVIR no tiene enlace por oferta: el enlace abre su buscador.
- Cada grupo trae el enlace **"Buscar en Empleos Perú"** con la búsqueda ya hecha (puesto y lugar). SERVIR no lo
  permite: su enlace abre el buscador y se elige el departamento.
- Cada portal que no responda queda anotado en **Fuentes** sin tumbar el resto del informe.
- Todo esto también se maneja desde la pestaña **Empleos** del panel de suscriptores.

## Panel de administración (Laravel)

`panel/` es una aplicación Laravel (SQLite, sin MySQL: no toca otras aplicaciones) donde **registras qué quiere cada
suscriptor**: correos, regiones, palabras clave, entidades, UNIQ, empleos y sueldo mínimo; con pausa, duplicar y búsqueda.

- **Web** (sesión): `/login`, `/subscribers`. Tu usuario sale de `ADMIN_EMAIL` / `ADMIN_PASSWORD` (`php artisan db:seed`).
- **API** (tokens Sanctum, `php artisan panel:token NOMBRE --abilities=subscribers|bot`):
  `GET|POST /api/subscribers`, `GET|PUT|DELETE /api/subscribers/{id}`, `PATCH /api/subscribers/{id}/pause`;
  para el bot: `GET /api/bot/profiles` (activos, en el formato de `perfiles.ini`) y `POST /api/bot/sent`.
- **El bot lo lee solo:** con `PANEL_URL` y `PANEL_TOKEN` en el `.env`, `bot.py` toma los suscriptores del panel
  (los pausados no salen) y avisa lo que envió. Si el panel no responde, usa `perfiles.ini`.
- **Renombrar es seguro:** cada suscriptor lleva una `clave` fija con la que el bot guarda "lo ya informado".
- **Sin HTTP en el servidor:** `php artisan panel:export-perfiles /ruta/perfiles.ini` escribe los suscriptores activos
  como `perfiles.ini` (el bot lo lee igual). Útil en el VPS: no hace falta abrir ningún puerto ni dejar un servicio.
- Los estilos (Tailwind) se compilan con Vite (`npm run build`; el Dockerfile ya lo hace).
- Validación en `app/Http/Requests`, respuestas en `app/Http/Resources`; pruebas con `php artisan test`
  (en Docker: `docker run --rm neoestado-panel sh -c "cp .env.example .env && php artisan test"`).

## Probarlo en local con Docker

Sirve para ver el panel y los correos sin tocar el VPS ni enviar nada real (el VPS no usa Docker: sigue con `install.sh`).

```bash
docker compose up -d --build          # panel + Mailpit (bandeja de prueba)
docker compose run --rm bot           # genera los informes sin enviar (--dry-run)
docker compose run --rm bot python bot.py   # los "envía": caen en Mailpit
docker compose down                   # apaga todo (los datos quedan en ./docker-data)
```

- **Panel Laravel:** <http://127.0.0.1:8000> (usuario `admin@neoestado.test`, contraseña `cambiar-esto-local`; solo tu equipo).
  **Correos recibidos:** <http://127.0.0.1:8025>. El panel anterior en Python: `docker compose --profile python up -d panel-python`.
- El primer arranque crea dos suscriptores de demostración (correos `example.com`); el bot los toma del panel.
- Se consultan los portales públicos reales (SEACE, UNIQ, Empleos Perú, SERVIR); la primera corrida tarda 1-2 minutos por el
  ritmo de consultas. Estado, logs y perfiles quedan en `./docker-data` (no se sube a GitHub).
- Para usar otra clave del panel: `PANEL_CLAVE=otra docker compose up -d`.

## Límite de consultas del portal de contrataciones menores

El portal de las contrataciones menores (`prod6.seace.gob.pe`) bloquea unos 10 minutos a quien le pide muy
rápido (responde HTTP 403 `{"message":"Forbidden"}`); medido: 2,5 consultas por segundo bloquean, 1 por
segundo no. Por eso el bot:

- pide la ubicación y el requerimiento de cada contratación **a 1 por segundo**, con un tope de 200 consultas
  por ejecución; lo que falte se completa al día siguiente (lo leído queda guardado en `data/estado.json`);
- si aun así llega un 403, **deja de pedir** hasta la próxima ejecución y lo anota en *Fuentes*;
- guarda la última lista de departamentos y provincias y trae una copia (`maestras.json`) por si el portal la rechaza.

La primera ejecución tras instalar puede tardar unos minutos más; las siguientes solo piden lo nuevo.

## Panel de suscriptores

Agrega, edita, pausa y elimina suscriptores desde una página, sin tocar `perfiles.ini` a mano. Es la misma
configuración que lee el bot: lo que guardas ahí vale desde el siguiente envío.

**Seguridad (no afecta a R-Uno):** no es un servicio. Se enciende cuando lo pides, escucha **solo en
`127.0.0.1`** (nunca en la red; no abre puertos), pide una clave distinta en cada sesión y se apaga solo
tras 60 minutos sin uso. Corre como `cotizbot`, con su propio `venv`.

1. En tu PC abre un túnel SSH (en PuTTY: *Connection > SSH > Tunnels*, puerto de origen `8787`, destino
   `127.0.0.1:8787`, **Add**, y conéctate como siempre; o desde una terminal con
   `ssh -L 8787:127.0.0.1:8787 usuario@IP_DEL_VPS`).
2. En esa sesión del VPS:

   ```bash
   sudo -u cotizbot /opt/cotizaciones-uniq/venv/bin/python /opt/cotizaciones-uniq/admin.py
   ```

3. Abre en tu navegador la dirección que imprime (`http://127.0.0.1:8787/?c=…`). `Ctrl+C` lo cierra.

Qué ofrece:

- **Lista de suscriptores** con buscador, estado (Activo / En pausa), último envío y un interruptor para pausar.
- **Crear o editar** en tres pestañas: *Datos* (nombre, nota, correos, formato, UNIQ), *Intereses* (regiones y
  provincias elegidas de la lista real del SEACE, palabras clave en etiquetas con opción de frase exacta y
  aviso si son muy generales, entidades con autocompletado de las que tienen procesos hoy) y *Vista previa*
  (el correo tal como lo recibiría hoy, sin enviar nada).
- **Enviar ahora** el informe de un suscriptor, **duplicar** y **eliminar**.
- **Deshacer** en cada cambio y **Historial** con los últimos respaldos y la actividad reciente del bot.
- **Nunca deja el archivo roto:** valida con las mismas reglas del bot antes de guardar, comprueba que las
  regiones existan y guarda una copia en `data/respaldos/` (40 como máximo) antes de cada cambio. Si cambias
  el nombre de alguien, su historial de "lo ya informado" lo sigue.

Los comentarios escritos a mano en `perfiles.ini` no se conservan al guardar desde el panel (la copia anterior
sí los tiene en `data/respaldos/`). Opciones: `--puerto N`, `--minutos N` (0 = no apagarse nunca).

## Archivos

| | |
|---|---|
| `bot.py` | orquesta: lee las fuentes, arma un informe por perfil y lo envía |
| `maestras.json` | copia de departamentos y provincias del SEACE, por si el portal rechaza la consulta |
| `empleos.py` | ofertas de empleo: Empleos Perú (API JSON) y Talento Perú/SERVIR (página JSF) |
| `admin.py` + `admin.html` | panel local de suscriptores (agregar, editar, pausar, vista previa); ver [Panel de suscriptores](#panel-de-suscriptores) |
| `uniq.py` | cotizaciones UNIQ y lectura del TDR/EETT |
| `seace.py` | búsquedas en SEACE (contrataciones menores y Oportunidades de Negocio) y la regla de coincidencia |
| `informe.py` | diseño del correo (HTML y texto) |
| `test_bot.py` | autoprueba sin red: `python test_bot.py` |
| `.env` | credenciales, palabras clave, entidades y regiones (a partir de `.env.example`); permisos 600, **no se versiona** |
| `perfiles.ini` | (opcional) un bloque por persona; se crea a partir de `perfiles.ini.example`; **no se versiona** |
| `data/estado.json` | lo que recibió cada perfil en su último informe (para marcar lo nuevo) y la provincia de cada distrito ya consultado |
| `logs/bot.log` | log con rotación (1 MB × 3); `logs/cron.err` solo si Python se cae |

Opciones: `--dry-run` imprime los informes en consola sin enviar; `--html-preview` los guarda en
`preview.html` (`preview_<perfil>.html` si hay varios); `--perfil NOMBRE` genera solo ese perfil.
Ninguna actualiza el estado ni envía correos.

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
