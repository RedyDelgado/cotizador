#!/usr/bin/env python3
"""Monitor de contrataciones públicas: un informe diario por correo.

Junta tres fuentes públicas en un solo informe:
- UNIQ: cotizaciones activas con el extracto de su TDR/EETT (uniq.py);
- SEACE: contrataciones menores y procedimientos de selección que coinciden con tus
  palabras clave, PALABRAS_CLAVE en .env (seace.py).
El diseño del correo está en informe.py.
"""
import argparse
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


def sesion():
    """Sesión HTTP con 3 reintentos (espera creciente) para caídas de red y errores 5xx."""
    s = requests.Session()
    s.headers["User-Agent"] = UA
    reintentos = Retry(total=3, backoff_factor=5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=None)
    s.mount("https://", HTTPAdapter(max_retries=reintentos))
    return s


def error_corto(e):
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

def leer_uniq(s, ahora, estado, fuentes):
    try:
        convs = uniq.obtener_convocatorias(s, ahora)
        for c in convs:
            uniq.leer_tdr(s, c)
    except Exception as e:
        log.exception("Falló la fuente UNIQ")
        fuentes.append(("UNIQ · Cotizaciones en línea", False, error_corto(e), "Tiempo real"))
        return None
    vistos = set(estado.get("vistos", []))
    for c in convs:
        c["nueva"] = c["id"] not in vistos
    fuentes.append(("UNIQ · Cotizaciones en línea", True, f"{len(convs)} activas", "Tiempo real"))
    log.info("UNIQ: %d convocatorias activas", len(convs))
    return convs


def proceso_uniq(c):
    """Una cotización UNIQ en el mismo formato de proceso que devuelve seace.py."""
    return {"id": f"u-{c['id']}", "fuente": "UNIQ", "tipo": f"Cotización ({c['tipo'].lower()})", "titulo": c["titulo"],
            "entidad": c["dependencia"], "codigo": f"N° {c['numero']}", "url": c["tdr_url"] or uniq.URL_PAGINA,
            "cierre": c["limite"], "abierta": True, "inicio": None, "convocatoria": None, "monto": 0, "nuevo": c["nueva"]}


def buscar_coincidencias(s, ahora, palabras, convs, estado, fuentes):
    """[(frase, [procesos])] de todas las fuentes. Un proceso que calza con dos frases sale en la primera."""
    vistos = set(estado.get("seace", []))
    busquedas = [("menores", "SEACE · Contrataciones menores", "Tiempo real · hasta 8 UIT", seace.menores),
                 ("ocds", "OECE · Contrataciones Abiertas", f"~2 días de desfase · últimos {seace.DIAS_OCDS} días",
                  seace.procedimientos)]
    errores, cuenta, grupos, listados = {}, {"menores": 0, "ocds": 0}, [], set()
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
        for c in convs or []:
            if seace.coincide(c["titulo"], frase):
                c.setdefault("coincide", frase)
                items.append(proceso_uniq(c))
        items = [x for x in items if x["id"] not in listados]
        listados |= {x["id"] for x in items}
        # Primero lo que tiene fecha de cierre (lo más próximo arriba), luego lo más recién convocado.
        items.sort(key=lambda x: (0, x["cierre"].timestamp()) if x["cierre"] else (1, -x["convocatoria"].timestamp()))
        grupos.append((frase, items))
    if palabras:
        for clave, nombre, cobertura, _ in busquedas:
            ok = clave not in errores
            fuentes.append((nombre, ok, f"{cuenta[clave]} coincidencias" if ok else error_corto(errores[clave]), cobertura))
    log.info("Coincidencias: %s", {f: len(i) for f, i in grupos})
    seace_ids = {x["id"] for _, items in grupos for x in items if x["fuente"] == "SEACE"}
    return grupos, seace_ids, bool(errores)


# --------------------------------------------------------------------- envío

def enviar(asunto, texto, cuerpo_html):
    faltan = [k for k in ("SMTP_USER", "SMTP_PASS", "MAIL_TO") if not os.environ.get(k)]
    if faltan:
        raise RuntimeError(f"Faltan variables en .env: {', '.join(faltan)}")
    usuario = os.environ["SMTP_USER"]
    destinos = [d.strip() for d in os.environ["MAIL_TO"].split(",") if d.strip()]

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

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(usuario, os.environ["SMTP_PASS"].replace(" ", ""))  # Google la muestra con espacios
        smtp.send_message(msg)
    log.info("Correo enviado a %s: %s", ", ".join(destinos), asunto)


# ---------------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description="Informe diario de oportunidades: UNIQ y SEACE por palabras clave.")
    p.add_argument("--dry-run", action="store_true", help="imprime el informe en consola; no envía ni actualiza el estado")
    p.add_argument("--html-preview", action="store_true", help="guarda el HTML en preview.html; no envía")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # tildes en la consola de Windows
    cargar_env()
    configurar_log()
    sin_envio = args.dry_run or args.html_preview
    ahora = datetime.now(uniq.LIMA)
    palabras = [x.strip() for x in os.environ.get("PALABRAS_CLAVE", "").split(",") if x.strip()]

    try:
        estado = cargar_estado()
        s = sesion()
        fuentes = []
        convs = leer_uniq(s, ahora, estado, fuentes)
        grupos, seace_ids, seace_fallo = buscar_coincidencias(s, ahora, palabras, convs, estado, fuentes)

        if all(not ok for _, ok, _, _ in fuentes):
            raise RuntimeError("Ninguna fuente respondió:\n" + "\n".join(f"- {n}: {d}" for n, _, d, _ in fuentes))

        asunto, texto, cuerpo = informe.construir_informe(ahora, palabras, convs, grupos, fuentes)
        if args.html_preview:
            (DIR / "preview.html").write_text(informe.con_data_uri(cuerpo), "utf-8")
            print(f"HTML guardado en {DIR / 'preview.html'}")
        if args.dry_run:
            print(f"{asunto}\n\n{texto}\n")
        if not sin_envio:
            enviar(asunto, texto, cuerpo)
            # Solo tras enviar: si falla, mañana siguen como nuevos. Si una fuente cayó, se conserva lo
            # visto antes para no volver a marcar como nuevo lo que ya salió.
            if convs is not None:
                estado["vistos"] = sorted(c["id"] for c in convs)
            estado["seace"] = sorted(seace_ids | (set(estado.get("seace", [])) if seace_fallo else set()))
            guardar_estado(estado, ahora)
        return 0
    except Exception:
        log.exception("No se pudo generar el informe")
        if not sin_envio:
            try:
                enviar(*informe.construir_alerta(traceback.format_exc(), ahora))
            except Exception:
                log.exception("Tampoco se pudo enviar el correo de alerta")
        return 1
    finally:
        try:
            import resource  # solo Linux
            log.info("Memoria máxima: %.1f MB", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
        except ImportError:
            pass


if __name__ == "__main__":
    sys.exit(main())
