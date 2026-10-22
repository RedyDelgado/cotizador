#!/usr/bin/env python3
"""Monitor de contrataciones públicas: un informe diario por correo.

Junta fuentes públicas en un solo informe:
- UNIQ: cotizaciones activas con el extracto de su TDR/EETT (uniq.py);
- SEACE: contrataciones menores y procedimientos de selección que coinciden con tus
  palabras clave (PALABRAS_CLAVE en .env), y todo lo abierto de las entidades que sigues
  (ENTIDADES en .env) (seace.py).
El diseño del correo está en informe.py.
"""
import argparse
import configparser
import json
import logging
import os
import re
import smtplib
import sys
import traceback
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from logging.handlers import RotatingFileHandler
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import empleos
import informe
import seace
import uniq

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
DIR = Path(__file__).resolve().parent
ESTADO = DIR / "data" / "estado.json"
LOG = DIR / "logs" / "bot.log"

log = logging.getLogger("cotizbot")


# ----------------------------------------------------------------- utilidades

def cargar_env():
    """Lee .env (KEY=VALOR) sin sobrescribir variables ya definidas."""
    ruta = DIR / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text("utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            k, v = linea.split("=", 1)
            v = v.strip()
            # Solo se quitan comillas que envuelven TODO el valor: en PALABRAS_CLAVE=software,"sistema
            # académico" las comillas son parte de la sintaxis y se quedan.
            if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'" and v.count(v[0]) == 2:
                v = v[1:-1]
            os.environ.setdefault(k.strip(), v)


def configurar_log():
    LOG.parent.mkdir(exist_ok=True)
    handlers = [RotatingFileHandler(LOG, maxBytes=1_000_000, backupCount=3, encoding="utf-8")]
    if sys.stderr.isatty():  # en cron no: así logs/cron.err solo recibe caídas reales
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)


class SesionConCache(requests.Session):
    """Los GET repetidos (misma URL y parámetros) se responden desde memoria, errores incluidos: con varios
    perfiles cada fuente se descarga una sola vez y una fuente caída no se reintenta por cada perfil."""

    def __init__(self):
        super().__init__()
        self._cache = {}
        self.compartido = {}  # lo que cuesta varias llamadas (p. ej. SERVIR) y se reparte entre perfiles

    def get(self, url, params=None, **kwargs):
        clave = (url, tuple(sorted((k, str(v)) for k, v in (params or {}).items())))
        if clave not in self._cache:
            try:
                self._cache[clave] = super().get(url, params=params, **kwargs)
            except Exception as e:
                self._cache[clave] = e
        respuesta = self._cache[clave]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta


def sesion():
    """Sesión HTTP con 3 reintentos (espera creciente) para caídas de red y errores 5xx."""
    s = SesionConCache()
    s.headers["User-Agent"] = UA
    reintentos = Retry(total=3, backoff_factor=5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=None)
    s.mount("https://", HTTPAdapter(max_retries=reintentos))
    return s


def error_corto(e):
    """El error en palabras simples para la tabla de fuentes del informe (el detalle técnico va al log)."""
    if isinstance(e, requests.HTTPError) and e.response is not None:
        if e.response.status_code == 403:
            return "El portal rechaza las conexiones desde este servidor (HTTP 403)"
        return f"El portal respondió con error HTTP {e.response.status_code}"
    if isinstance(e, requests.exceptions.RetryError):
        return "El portal respondió con errores en todos los reintentos"
    if isinstance(e, requests.Timeout):
        return "El portal no respondió a tiempo"
    if isinstance(e, requests.ConnectionError):
        return "No se pudo conectar con el portal"
    return f"{type(e).__name__}: {str(e)[:140]}"


# -------------------------------------------------------------------- estado
# {"vistos": [ids UNIQ del informe anterior], "seace": [ids SEACE del informe anterior], "actualizado": "..."}

def cargar_estado():
    try:
        return json.loads(ESTADO.read_text("utf-8"))
    except FileNotFoundError:
        return {}
    except ValueError:
        log.warning("estado.json ilegible; se marcará todo como nuevo")
        return {}


def guardar_estado(estado, ahora):
    ESTADO.parent.mkdir(exist_ok=True)
    estado["actualizado"] = ahora.isoformat(timespec="seconds")
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado), "utf-8")
    tmp.replace(ESTADO)


# ------------------------------------------------------------------- fuentes

def descargar_uniq(s, ahora):
    """(convocatorias, error): se descarga una sola vez y cada perfil trabaja con su copia."""
    try:
        convs = uniq.obtener_convocatorias(s, ahora)  # cada fila del informe enlaza su TDR/EETT: no se descarga
    except Exception as e:
        log.exception("Falló la fuente UNIQ")
        return None, e
    log.info("UNIQ: %d convocatorias activas", len(convs))
    return convs, None


def leer_uniq(base, error, estado, fuentes):
    """Copia de las convocatorias para un perfil, con "nueva" según lo que ese perfil ya recibió."""
    if base is None:
        fuentes.append(("UNIQ · Cotizaciones en línea", False, error_corto(error), "Tiempo real"))
        return None
    vistos = set(estado.get("vistos", []))
    fuentes.append(("UNIQ · Cotizaciones en línea", True, f"{len(base)} activas", "Tiempo real"))
    return [dict(c, nueva=c["id"] not in vistos) for c in base]


def proceso_uniq(c):
    """Una cotización UNIQ en el mismo formato de proceso que devuelve seace.py."""
    return {"id": f"u-{c['id']}", "fuente": "UNIQ", "tipo": f"Cotización ({c['tipo'].lower()})", "titulo": c["titulo"],
            "entidad": c["dependencia"], "codigo": f"N° {c['numero']}", "url": c["tdr_url"] or uniq.URL_PAGINA,
            "cierre": c["limite"], "abierta": True, "inicio": None, "convocatoria": None, "monto": 0, "nuevo": c["nueva"]}


def cerrar_grupo(items, convs, frase, listados):
    """Suma las cotizaciones UNIQ que calzan con la frase, quita lo ya listado en una frase anterior (un
    proceso que calza con dos frases sale solo en la primera) y ordena: lo que cierra antes, arriba."""
    for c in convs or []:
        if seace.coincide(c["titulo"], frase):
            c.setdefault("coincide", frase)
            items.append(proceso_uniq(c))
    items = [x for x in items if x["id"] not in listados]
    listados |= {x["id"] for x in items}
    items.sort(key=lambda x: (0, x["cierre"].timestamp()) if x["cierre"] else (1, -x["convocatoria"].timestamp()))
    return items


def coincidencias_en_regiones(palabras, convs, candidatos, fuentes):
    """Palabras clave buscadas SOLO entre lo abierto en las regiones del perfil (candidatos: {id: proceso})."""
    grupos, listados = [], set()
    for frase in palabras:
        items = [x for x in candidatos.values() if seace.coincide(x.get("texto") or x["titulo"], frase)]
        grupos.append((frase, cerrar_grupo(items, convs, frase, listados)))
    total = sum(len(i) for _, i in grupos)
    fuentes.append(("SEACE · Palabras clave en tus regiones", True, f"{total} coincidencias",
                    "Procedimientos y contrataciones menores de las regiones del perfil"))
    log.info("Coincidencias (solo en las regiones del perfil): %s", {f: len(i) for f, i in grupos})
    return grupos, {x["id"] for _, items in grupos for x in items if x["fuente"] == "SEACE"}


def buscar_coincidencias(s, ahora, palabras, convs, estado, fuentes):
    """[(frase, [procesos])] de todo el país (para perfiles sin regiones)."""
    vistos = set(estado.get("seace", []))
    busquedas = [("menores", "SEACE · Contrataciones menores", "Tiempo real · hasta 8 UIT", seace.menores),
                 ("oportunidades", "SEACE · Oportunidades de Negocio", "Procedimientos con registro abierto",
                  seace.procedimientos)]
    errores, cuenta, grupos, listados = {}, {"menores": 0, "oportunidades": 0}, [], set()
    for frase in palabras:
        items = []
        for clave, _, _, buscar in busquedas:
            if clave in errores:
                continue
            try:
                encontrados = buscar(s, frase, ahora)
            except Exception as e:
                log.exception("Falló la búsqueda %s de %r", clave, frase)
                errores[clave] = e
                continue
            for x in encontrados:
                x["nuevo"] = x["id"] not in vistos
            cuenta[clave] += len(encontrados)
            items += encontrados
        grupos.append((frase, cerrar_grupo(items, convs, frase, listados)))
    if palabras:
        for clave, nombre, cobertura, _ in busquedas:
            ok = clave not in errores
            fuentes.append((nombre, ok, f"{cuenta[clave]} coincidencias" if ok else error_corto(errores[clave]), cobertura))
    log.info("Coincidencias: %s", {f: len(i) for f, i in grupos})
    seace_ids = {x["id"] for _, items in grupos for x in items if x["fuente"] == "SEACE"}
    return grupos, seace_ids, bool(errores)


def buscar_zonas(s, ahora, regiones, estado, fuentes, cache, maestras=None):
    """[(zona, [procesos])]: todo lo abierto en las regiones/provincias de REGIONES.
    cache: distrito de Oportunidades de Negocio -> provincia (compartido por todos los perfiles)."""
    if not regiones:
        return [], False
    vistos = set(estado.get("seace", []))
    cobertura = "Procedimientos y contrataciones menores"
    try:
        zonas = seace.resolver_zonas(s, regiones, maestras)
    except Exception as e:
        log.exception("No se pudieron resolver las REGIONES")
        fuentes.append(("SEACE · Regiones que sigues", False, str(e) if isinstance(e, ValueError) else error_corto(e), cobertura))
        return [], True
    grupos, fallas = [], []
    for zona in zonas:
        try:
            items = seace.procesos_de_zona(s, zona, ahora, cache)
        except Exception as e:
            log.exception("Falló la región %s", zona["texto"])
            fallas.append(f"{zona['texto']}: {error_corto(e)}")
            continue
        for x in items:
            x["nuevo"] = x["id"] not in vistos
        grupos.append((zona, sorted(items, key=lambda x: x["cierre"])))
    total = sum(len(i) for _, i in grupos)
    fuentes.append(("SEACE · Regiones que sigues", not fallas,
                    "; ".join(fallas) if fallas else f"{total} procesos abiertos", cobertura))
    log.info("Regiones: %s", {z["texto"]: len(i) for z, i in grupos})
    return grupos, bool(fallas)


def buscar_entidades(s, ahora, entidades, estado, fuentes):
    """[(entidad, [procesos])]: todo lo abierto de las entidades que sigues, sin filtrar por palabra clave."""
    if not entidades:
        return [], set(), False
    vistos = set(estado.get("seace", []))
    try:
        por_entidad = seace.procedimientos_de_entidades(s, entidades, ahora)
    except Exception as e:
        log.exception("Falló la búsqueda de entidades")
        fuentes.append(("SEACE · Entidades que sigues", False, error_corto(e), "Procedimientos con registro abierto"))
        return [], set(), True
    grupos = []
    for entidad in entidades:
        items = sorted(por_entidad[entidad], key=lambda x: x["cierre"])
        for x in items:
            x["nuevo"] = x["id"] not in vistos
        grupos.append((entidad, items))
    total = sum(len(i) for _, i in grupos)
    fuentes.append(("SEACE · Entidades que sigues", True, f"{total} procedimientos abiertos", "Procedimientos con registro abierto"))
    log.info("Entidades: %s", {e: len(i) for e, i in grupos})
    return grupos, {x["id"] for _, items in grupos for x in items}, False


def _servir(s, codigo, texto):
    """Ofertas de SERVIR de un departamento o de una búsqueda por texto; se piden una sola vez por ejecución."""
    clave = ("servir", codigo, texto)
    if clave not in s.compartido:
        try:
            s.compartido[clave] = empleos.buscar_servir(s, codigo, texto)
        except Exception as e:
            s.compartido[clave] = e
    if isinstance(s.compartido[clave], Exception):
        raise s.compartido[clave]
    return s.compartido[clave]


def buscar_empleos(s, perfil, estado, fuentes):
    """([(rótulo, [ofertas])], ids, fallo): ofertas de Empleos Perú (MTPE) y Talento Perú (SERVIR) en las
    regiones y con las palabras clave de empleo del perfil, y con el sueldo mínimo que pida. Sin regiones de
    empleo se usan las del perfil; sin ninguna, todo el país. Cada fuente que falla queda anotada y no tumba el resto."""
    palabras = perfil["empleo_palabras"]
    regiones = perfil["empleo_regiones"] or perfil["regiones"]
    ofertas, fallos, provincia_de = [], [], {}
    cobertura_mtpe = "Sector privado y público · todo el país"
    try:
        lugares = s.compartido.get("lugares_mtpe") or s.compartido.setdefault("lugares_mtpe", empleos.lugares_mtpe(s))
        provincia_de = s.compartido.get("provincias") or s.compartido.setdefault("provincias", empleos.provincias_de_distritos(lugares))
        mtpe = s.compartido.get("mtpe") or s.compartido.setdefault("mtpe", empleos.ofertas_mtpe(s))
        ofertas += mtpe
        fuentes.append(("Empleos Perú (MTPE)", True, f"{len(mtpe)} ofertas vigentes leídas", cobertura_mtpe))
    except Exception as e:
        log.exception("Falló Empleos Perú")
        fuentes.append(("Empleos Perú (MTPE)", False, error_corto(e), cobertura_mtpe))
        fallos.append("MTPE")
    cobertura_servir = "Sector público · convocatorias de entidades del Estado"
    try:
        codigos = empleos.codigos_servir(s)
        pedidos = []  # (código de departamento, texto del perfil)
        if regiones:
            nombres = list(dict.fromkeys(seace.normal(r.partition("/")[0]) for r in regiones))
            pedidos = [(codigos[n], "") for n in nombres if n in codigos]
            desconocidas = [n for n in nombres if n not in codigos]
            if desconocidas:
                log.warning("SERVIR no tiene la región %s", desconocidas)
        else:  # todo el país: 387 páginas serían demasiadas; se busca por cada palabra clave
            pedidos = [("0", seace.consulta(p)[0]) for p in palabras if seace.consulta(p)]
        servir = {o["id"]: o for codigo, texto in pedidos for o in _servir(s, codigo, texto)}
        ofertas += servir.values()
        fuentes.append(("Talento Perú (SERVIR)", True, f"{len(servir)} ofertas leídas", cobertura_servir))
    except Exception as e:
        log.exception("Falló Talento Perú (SERVIR)")
        fuentes.append(("Talento Perú (SERVIR)", False, error_corto(e), cobertura_servir))
        fallos.append("SERVIR")
    grupos = empleos.agrupar(ofertas, palabras, regiones, set(estado.get("empleos", [])), perfil["empleo_sueldo"], provincia_de)
    grupos = [(informe.mostrar(n) if palabras else informe.nombre_lugar(n), items) for n, items in grupos]
    log.info("Empleos: %s", {n: len(i) for n, i in grupos})
    return grupos, {x["id"] for _, items in grupos for x in items}, bool(fallos)


# --------------------------------------------------------------------- envío

def enviar(asunto, texto, cuerpo_html, destinos, adjunto_html=None, nombre_adjunto="informe.html"):
    faltan = [k for k in ("SMTP_USER", "SMTP_PASS") if not os.environ.get(k)]
    if faltan:
        raise RuntimeError(f"Faltan variables en .env: {', '.join(faltan)}")
    if not destinos:
        raise RuntimeError("No hay destinatarios: define MAIL_TO en .env o correos en perfiles.ini")
    usuario = os.environ["SMTP_USER"]

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = formataddr((os.environ.get("MAIL_FROM_NAME", "Monitor de Contrataciones"), usuario))
    msg["To"] = ", ".join(destinos)
    msg.set_content(texto)
    msg.add_alternative(cuerpo_html, subtype="html")
    parte_html = msg.get_body(("html",))
    for nombre in sorted(set(re.findall(r"cid:ico-([\w-]+)", cuerpo_html))):  # iconos usados, una vez cada uno
        parte_html.add_related(informe.png_icono(nombre), "image", "png", cid=f"<ico-{nombre}>",
                               disposition="inline", filename=f"{nombre}.png")
    logo = informe.logo_png()
    if logo and "cid:logo" in cuerpo_html:  # el logo de la marca, incrustado como los iconos
        parte_html.add_related(logo, "image", "png", cid="<logo>", disposition="inline", filename="neoestado.png")
    if adjunto_html:  # el informe entero como archivo: Gmail recorta el cuerpo del correo, no los adjuntos
        msg.add_attachment(adjunto_html.encode("utf-8"), maintype="text", subtype="html", filename=nombre_adjunto)

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.starttls()
        # Google la muestra con espacios y, al copiarla, a veces vienen espacios no separables: fuera todos.
        smtp.login(usuario, "".join(os.environ["SMTP_PASS"].split()))
        smtp.send_message(msg)
    log.info("Correo enviado a %s: %s", ", ".join(destinos), asunto)


# ------------------------------------------------------------------- perfiles
# Cada perfil es un informe distinto para unos correos: qué palabras clave, entidades y regiones sigue,
# si recibe la UNIQ y si lo quiere completo. Se definen en perfiles.ini (ver perfiles.ini.example); sin
# ese archivo hay un solo perfil con lo que diga el .env (MAIL_TO, PALABRAS_CLAVE, ENTIDADES, REGIONES).

CLAVES_PERFIL = {"correos", "palabras_clave", "entidades", "regiones", "uniq", "completo", "pausado", "nota",
                 "empleo_palabras", "empleo_regiones", "empleo_sueldo_min"}


def lista(texto):
    return [x.strip() for x in (texto or "").split(",") if x.strip()]


def es_si(texto, por_defecto=True):
    if texto is None or not texto.strip():
        return por_defecto
    return texto.strip().lower() not in ("no", "0", "false", "falso")


def separar_uniq(entidades):
    """La UNIQ es una entidad más: escribir "UNIQ" en `entidades` activa sus cotizaciones en línea. Devuelve
    (entidades con el nombre completo de la UNIQ en SEACE, ¿el perfil sigue a la UNIQ?)."""
    sigue = any(seace.normal(e) in uniq.ALIAS for e in entidades)
    return list(dict.fromkeys(uniq.NOMBRE if seace.normal(e) in uniq.ALIAS else e for e in entidades)), sigue


def cargar_perfiles():
    """[{nombre, correos, palabras, entidades, regiones, uniq, completo, legacy}]. ValueError si el
    archivo tiene un error (con el mensaje para corregirlo)."""
    ruta = DIR / "perfiles.ini"
    if not ruta.exists():
        return [{"nombre": "principal", "legacy": True, "correos": lista(os.environ.get("MAIL_TO")),
                 "palabras": lista(os.environ.get("PALABRAS_CLAVE")),
                 "entidades": separar_uniq(lista(os.environ.get("ENTIDADES")))[0],
                 "regiones": lista(os.environ.get("REGIONES")), "uniq": True,
                 "completo": es_si(os.environ.get("INFORME_COMPLETO")), "nota": "", "pausado": False,
                 "empleo_palabras": [], "empleo_regiones": [], "empleo_sueldo": None, "empleos": False}]
    ini = configparser.ConfigParser(interpolation=None)  # sin interpolación: el % es un carácter normal
    try:
        with open(ruta, encoding="utf-8") as f:  # (ini.read ignoraría en silencio un archivo sin permiso)
            ini.read_file(f)
    except PermissionError:
        raise ValueError(f"perfiles.ini: el usuario del bot no puede leerlo (permisos). Corrige con: "
                         f"sudo chown {os.environ.get('USER') or 'cotizbot'}:cotizbot {ruta} && sudo chmod 600 {ruta}")
    except (configparser.Error, UnicodeDecodeError) as e:
        raise ValueError(f"perfiles.ini: {str(e).splitlines()[0]}")
    perfiles = [perfil_de_seccion(nombre, ini[nombre]) for nombre in ini.sections()]
    if not perfiles:
        raise ValueError("perfiles.ini no tiene ningún perfil (cada uno empieza con [nombre])")
    return perfiles


def sueldo_minimo(nombre, texto):
    """"3000" o "3,000" -> 3000; None si no hay."""
    if not (texto or "").strip():
        return None
    try:
        return int(float(texto.replace(",", "").replace("S/", "").strip()))
    except ValueError:
        raise ValueError(f"perfiles.ini [{nombre}]: empleo_sueldo_min tiene que ser un número (p. ej. 3000), no {texto!r}")


def perfil_de_seccion(nombre, sec):
    """Un bloque de perfiles.ini (o un dict con las mismas claves, como lo manda el panel) -> perfil.
    ValueError si algo no es válido."""
    desconocidas = sorted(set(sec) - CLAVES_PERFIL)
    if desconocidas:
        raise ValueError(f"perfiles.ini [{nombre}]: clave desconocida {desconocidas[0]!r} "
                         f"(válidas: {', '.join(sorted(CLAVES_PERFIL))})")
    correos = lista(sec.get("correos"))
    if not correos:
        raise ValueError(f"perfiles.ini [{nombre}]: falta 'correos'")
    malos = [c for c in correos if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", c)]
    if malos:
        raise ValueError(f"perfiles.ini [{nombre}]: correo no válido: {malos[0]!r}")
    entidades, sigue_uniq = separar_uniq(lista(sec.get("entidades")))
    # La UNIQ se recibe solo si el perfil la pide: con "UNIQ" en entidades o con la clave antigua uniq = si.
    perfil = {"nombre": nombre, "legacy": False, "correos": correos, "palabras": lista(sec.get("palabras_clave")),
              "entidades": entidades, "regiones": lista(sec.get("regiones")), "nota": (sec.get("nota") or "").strip(),
              "uniq": sigue_uniq or es_si(sec.get("uniq"), por_defecto=False), "completo": es_si(sec.get("completo")),
              "pausado": es_si(sec.get("pausado"), por_defecto=False), "empleo_palabras": lista(sec.get("empleo_palabras")),
              "empleo_regiones": lista(sec.get("empleo_regiones")), "empleo_sueldo": sueldo_minimo(nombre, sec.get("empleo_sueldo_min"))}
    # Las ofertas de empleo se reciben si el bloque pide algo de ellas (palabras, regiones o un sueldo mínimo).
    perfil["empleos"] = bool(perfil["empleo_palabras"] or perfil["empleo_regiones"] or perfil["empleo_sueldo"])
    if not (perfil["uniq"] or perfil["palabras"] or perfil["entidades"] or perfil["regiones"] or perfil["empleos"]):
        raise ValueError(f"perfiles.ini [{nombre}]: no sigue nada (sin palabras_clave, entidades, regiones ni empleo_*)")
    return perfil


def estado_de(estado, perfil):
    """Lo que ese perfil ya recibió. El perfil del .env (sin perfiles.ini) sigue usando las claves de
    siempre; los de perfiles.ini guardan lo suyo aparte, así lo NUEVO es propio de cada uno."""
    if perfil["legacy"]:
        return estado
    return estado.setdefault("perfiles", {}).setdefault(perfil["nombre"], {})


def generar(perfil, s, ahora, estado, uniq_base, uniq_error):
    """Informe de un perfil: (asunto, texto, html, ids_uniq, ids_seace, seace_fallo, ids_empleos, empleos_fallo)."""
    propio = estado_de(estado, perfil)
    fuentes = []
    convs = leer_uniq(uniq_base, uniq_error, propio, fuentes) if perfil["uniq"] else None
    # Las regiones primero: son la base de las palabras clave. Con regiones, las palabras clave se buscan
    # SOLO ahí; sin regiones, en todo el país.
    zonas, zonas_fallo = buscar_zonas(s, ahora, perfil["regiones"], propio, fuentes, estado.setdefault("ubigeos", {}),
                                      estado.setdefault("maestras", {}))
    if perfil["palabras"] and perfil["regiones"]:
        if zonas:
            candidatos = {x["id"]: x for _, items in zonas for x in items}
        else:  # no se pudo leer ninguna región: mejor sin resultados que buscar en todo el país por error
            candidatos = {}
            fuentes.append(("SEACE · Palabras clave en tus regiones", False,
                            "No se pudo leer ninguna región: revisa REGIONES en perfiles.ini", "Regiones del perfil"))
        grupos, seace_ids = coincidencias_en_regiones(perfil["palabras"], convs, candidatos, fuentes)
        seace_fallo = zonas_fallo
    else:
        grupos, seace_ids, seace_fallo = buscar_coincidencias(s, ahora, perfil["palabras"], convs, propio, fuentes)
    seguidas, _, entidades_fallo = buscar_entidades(s, ahora, perfil["entidades"], propio, fuentes)
    # Las contrataciones menores de las entidades que sigues salen de lo ya descargado para sus regiones,
    # y lo que ya salió en "Entidades que sigues" o en las palabras clave no se repite en "Regiones que sigues".
    seguidas = [(e, sorted(items + [x for _, zitems in zonas for x in zitems if x["tipo"] == "Contratación menor"
                                    and seace.normal(e) in seace.normal(x["entidad"])], key=lambda x: x["cierre"]))
                for e, items in seguidas]
    arriba = {x["id"] for _, items in seguidas + grupos for x in items}
    zonas = [(z, [x for x in items if x["id"] not in arriba]) for z, items in zonas]
    seace_ids |= {x["id"] for _, items in seguidas for x in items} | {x["id"] for _, items in zonas for x in items}
    # Ubicación (región › provincia › distrito) de todo lo que sale en el informe; se guarda en el estado.
    todos = [x for _, items in grupos + seguidas + zonas for x in items]
    seace.completar_lugares(s, todos, estado.setdefault("lugares", {}), ahora, log)
    if perfil["empleos"]:
        grupos_empleo, empleo_ids, empleo_fallo = buscar_empleos(s, perfil, propio, fuentes)
    else:
        grupos_empleo, empleo_ids, empleo_fallo = None, set(), False

    if fuentes and all(not ok for _, ok, _, _ in fuentes):
        raise RuntimeError("Ninguna fuente respondió:\n" + "\n".join(f"- {n}: {d}" for n, _, d, _ in fuentes))
    asunto, texto, cuerpo = informe.construir_informe(ahora, perfil["palabras"], convs, grupos, fuentes, seguidas, zonas,
                                                      perfil["completo"], perfil["uniq"],
                                                      grupos_empleo, informe.nota_empleos(perfil))
    ids_uniq = sorted(c["id"] for c in convs) if convs is not None else None
    return (asunto, texto, cuerpo, ids_uniq, seace_ids, seace_fallo or entidades_fallo or zonas_fallo,
            empleo_ids, empleo_fallo)


def destinatarios_de_alerta(perfiles):
    """A quién van los avisos técnicos: MAIL_ALERTAS, si no MAIL_TO, si no el primer perfil."""
    return lista(os.environ.get("MAIL_ALERTAS")) or lista(os.environ.get("MAIL_TO")) or (perfiles[0]["correos"] if perfiles else [])


# ---------------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description="Informe diario de oportunidades: UNIQ y SEACE, uno por perfil.")
    p.add_argument("--dry-run", action="store_true", help="imprime los informes en consola; no envía ni actualiza el estado")
    p.add_argument("--html-preview", action="store_true",
                   help="guarda el HTML en preview.html (preview_<perfil>.html si hay varios); no envía")
    p.add_argument("--perfil", help="genera solo el perfil con ese nombre")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # tildes en la consola de Windows
    cargar_env()
    configurar_log()
    sin_envio = args.dry_run or args.html_preview
    ahora = datetime.now(uniq.LIMA)

    fallos = []  # un informe que falla no impide los demás; al final sale un solo aviso con todo

    def avisar(perfiles):
        if fallos and not sin_envio:
            try:
                enviar(*informe.construir_alerta("\n\n".join(fallos), ahora), destinatarios_de_alerta(perfiles))
            except Exception:
                log.exception("Tampoco se pudo enviar el correo de alerta")

    try:
        perfiles = cargar_perfiles()
    except ValueError as e:
        log.error("%s", e)
        print(e, file=sys.stderr)
        fallos.append(str(e))
        avisar([])
        return 1
    if args.perfil:  # pedido por nombre: sale aunque esté pausado (así el panel puede probarlo)
        perfiles = [x for x in perfiles if x["nombre"].lower() == args.perfil.lower()]
        if not perfiles:
            print(f"No existe el perfil {args.perfil!r}", file=sys.stderr)
            return 1
    else:
        perfiles = [x for x in perfiles if not x.get("pausado")]
        if not perfiles:
            log.info("Todos los perfiles están pausados; no hay nada que enviar")
            return 0

    try:
        estado = cargar_estado()
        s = sesion()
        uniq_base, uniq_error = descargar_uniq(s, ahora) if any(x["uniq"] for x in perfiles) else (None, None)
        for perfil in perfiles:
            try:
                log.info("Perfil %s", perfil["nombre"])
                asunto, texto, cuerpo, ids_uniq, seace_ids, seace_fallo, empleo_ids, empleo_fallo = generar(
                    perfil, s, ahora, estado, uniq_base, uniq_error)
                if args.html_preview:
                    ficha = re.sub(r"\W+", "_", perfil["nombre"])
                    archivo = DIR / ("preview.html" if len(perfiles) == 1 else f"preview_{ficha}.html")
                    archivo.write_text(informe.con_data_uri(cuerpo), "utf-8")
                    print(f"HTML de [{perfil['nombre']}] guardado en {archivo}")
                if args.dry_run:
                    print(f"=== PERFIL {perfil['nombre']} → {', '.join(perfil['correos'])}\n{asunto}\n\n{texto}\n")
                if not sin_envio:
                    largo = len(cuerpo.encode()) > informe.LIMITE_HTML
                    enviar(asunto, texto, cuerpo, perfil["correos"],
                           informe.con_data_uri(cuerpo) if largo else None, f"informe-{ahora:%Y-%m-%d}.html")
                    # Solo tras enviar: si falla, mañana siguen como nuevos. Si una fuente cayó, se conserva lo
                    # visto antes para no volver a marcar como nuevo lo que ya salió.
                    propio = estado_de(estado, perfil)
                    if ids_uniq is not None:
                        propio["vistos"] = ids_uniq
                    propio["seace"] = sorted(seace_ids | (set(propio.get("seace", [])) if seace_fallo else set()))
                    if perfil["empleos"]:
                        propio["empleos"] = sorted(empleo_ids | (set(propio.get("empleos", [])) if empleo_fallo else set()))
                    propio["enviado"] = ahora.isoformat(timespec="minutes")  # lo muestra el panel (admin.py)
                    guardar_estado(estado, ahora)
            except Exception:
                log.exception("No se pudo generar o enviar el informe de [%s]", perfil["nombre"])
                fallos.append(f"Perfil [{perfil['nombre']}]:\n{traceback.format_exc()}")
        avisar(perfiles)
        return 1 if fallos else 0
    finally:
        try:
            import resource  # solo Linux
            log.info("Memoria máxima: %.1f MB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
        except ImportError:
            pass


if __name__ == "__main__":
    sys.exit(main())
