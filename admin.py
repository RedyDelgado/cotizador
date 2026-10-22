#!/usr/bin/env python3
"""Panel de suscriptores de NEOESTADO: agrega, edita y pausa perfiles sin tocar perfiles.ini a mano.

Es una página local: escucha SOLO en 127.0.0.1 (nunca en la red), pide una clave distinta en cada sesión y se
apaga sola tras un rato sin uso. Se entra desde tu PC con un túnel SSH (ver README). Lee y escribe el mismo
perfiles.ini que usa el bot, valida con las mismas reglas y guarda un respaldo antes de cada cambio.
"""
import argparse
import copy
import json
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from collections import Counter
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import bot
import informe
import seace
import uniq

INI = bot.DIR / "perfiles.ini"
RESPALDOS = bot.DIR / "data" / "respaldos"
HTML = bot.DIR / "admin.html"
MAX_RESPALDOS = 40
MAX_CUERPO = 200_000
NOMBRE_RESPALDO = re.compile(r"perfiles-\d{8}-\d{6}(-\d+)?\.ini")
CABECERA = ("# Administrado desde el panel (admin.py). Puedes editarlo a mano; antes de cada cambio del panel\n"
            "# queda un respaldo en data/respaldos/. Claves: ver perfiles.ini.example.\n\n")

log = bot.log
trabajo = threading.Lock()  # vista previa y envío son pesados: uno a la vez


# ------------------------------------------------------------------ perfiles
# El panel maneja cada perfil como {nombre, nota, correos[], palabras[], entidades[], regiones[], uniq,
# completo, pausado}; la UNIQ va aparte (es un interruptor) y se escribe como entidad "UNIQ".

def texto(valor):
    return " ".join(str(valor or "").split())


def elementos(valor):
    """Lista de textos sin vacíos, repetidos ni comas (la coma separa elementos en perfiles.ini)."""
    return list(dict.fromkeys(t for t in (texto(str(x).replace(",", " ")) for x in valor or []) if t))


def a_seccion(p):
    """Perfil del panel -> bloque de perfiles.ini (claves y valores de texto), solo lo que tiene valor."""
    entidades = (["UNIQ"] if p.get("uniq") else []) + [e for e in elementos(p.get("entidades"))
                                                       if seace.normal(e) not in uniq.ALIAS]
    seccion = {"nota": texto(p.get("nota")), "correos": ", ".join(elementos(p.get("correos"))),
               "palabras_clave": ",".join(elementos(p.get("palabras"))), "entidades": ",".join(entidades),
               "regiones": ",".join(elementos(p.get("regiones"))), "completo": "si" if p.get("completo", True) else "no",
               "pausado": "si" if p.get("pausado") else "",
               "empleo_palabras": ",".join(elementos(p.get("empleo_palabras"))),
               "empleo_regiones": ",".join(elementos(p.get("empleo_regiones"))),
               "empleo_sueldo_min": str(int(p["empleo_sueldo"])) if p.get("empleo_sueldo") else ""}
    return {k: v for k, v in seccion.items() if v}


def nombre_valido(nombre):
    if not nombre or len(nombre) > 60 or re.search(r"[\[\]\r\n]", nombre) or nombre.upper() == "DEFAULT":
        raise ValueError("El nombre no puede estar vacío, ni tener corchetes, ni pasar de 60 letras")


def publico(perfil, estado):
    """Perfil de bot.cargar_perfiles() -> forma del panel, con el último envío."""
    return {"nombre": perfil["nombre"], "nota": perfil["nota"], "correos": perfil["correos"],
            "palabras": perfil["palabras"], "regiones": perfil["regiones"], "uniq": perfil["uniq"],
            "entidades": [e for e in perfil["entidades"] if e != uniq.NOMBRE],
            "completo": perfil["completo"], "pausado": perfil["pausado"], "empleo_palabras": perfil["empleo_palabras"],
            "empleo_regiones": perfil["empleo_regiones"], "empleo_sueldo": perfil["empleo_sueldo"],
            "enviado": bot.estado_de(estado, perfil).get("enviado")}


def leer():
    """(perfiles en forma del panel, error). Sin perfiles.ini la lista está vacía: se crea al guardar el primero."""
    if not INI.exists():
        return [], None
    try:
        estado = bot.cargar_estado()
        return [publico(p, estado) for p in bot.cargar_perfiles()], None
    except ValueError as e:
        return [], str(e)


def serializar(perfiles):
    bloques = []
    for p in perfiles:
        filas = a_seccion(p)
        bloques.append(f"[{p['nombre']}]\n" + "".join(f"{k} = {v}\n" for k, v in filas.items()))
    return CABECERA + "\n".join(bloques)


def validar(perfiles):
    """ValueError con el motivo si alguno no es válido (mismas reglas que el bot)."""
    vistos = set()
    for p in perfiles:
        p["nombre"] = texto(p.get("nombre"))
        nombre_valido(p["nombre"])
        if p["nombre"].lower() in vistos:
            raise ValueError(f"Ya existe un suscriptor llamado {p['nombre']!r}")
        vistos.add(p["nombre"].lower())
        bot.perfil_de_seccion(p["nombre"], a_seccion(p))


# ------------------------------------------------------------------ respaldos

def respaldar():
    """Copia perfiles.ini a data/respaldos/ y devuelve su nombre (None si aún no existe)."""
    if not INI.exists():
        return None
    RESPALDOS.mkdir(parents=True, exist_ok=True)
    base = f"perfiles-{datetime.now():%Y%m%d-%H%M%S}"
    destino, n = RESPALDOS / f"{base}.ini", 0
    while destino.exists():
        n += 1
        destino = RESPALDOS / f"{base}-{n}.ini"
    shutil.copy2(INI, destino)
    for viejo in sorted(RESPALDOS.glob("perfiles-*.ini"))[:-MAX_RESPALDOS]:
        viejo.unlink()
    return destino.name


def instalar(contenido):
    """Guarda `contenido` como perfiles.ini y comprueba que el bot lo lee; si no, deja el anterior. Devuelve
    el nombre del respaldo del estado previo (para deshacer)."""
    anterior = INI.read_text("utf-8") if INI.exists() else None
    respaldo = respaldar()
    INI.write_text(contenido, "utf-8")  # en el sitio: conserva dueño y permisos del archivo
    try:
        bot.cargar_perfiles()
    except ValueError:
        if anterior is None:
            INI.unlink()
        else:
            INI.write_text(anterior, "utf-8")
        raise
    return respaldo


def lista_respaldos():
    salida = []
    for f in sorted(RESPALDOS.glob("perfiles-*.ini"), reverse=True):
        t = f.read_text("utf-8", errors="replace")
        salida.append({"archivo": f.name, "fecha": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                       "perfiles": re.findall(r"^\[([^\]]+)\]", t, re.M)})
    return salida


def restaurar(archivo):
    if not NOMBRE_RESPALDO.fullmatch(archivo or "") or not (RESPALDOS / archivo).exists():
        raise ValueError("Ese respaldo no existe")
    return instalar((RESPALDOS / archivo).read_text("utf-8"))


# --------------------------------------------------------------- operaciones

def renombrar_estado(viejo, nuevo):
    """Lo ya informado a un suscriptor sigue siendo suyo aunque cambie de nombre."""
    estado = bot.cargar_estado()
    propios = estado.get("perfiles", {})
    if viejo in propios and nuevo not in propios:
        propios[nuevo] = propios.pop(viejo)
        bot.guardar_estado(estado, datetime.now(uniq.LIMA))


def guardar(original, perfil):
    """Crea (original vacío) o reemplaza al suscriptor `original`. Devuelve el respaldo previo."""
    perfiles, error = leer()
    if error:
        raise ValueError("perfiles.ini tiene un error y hay que corregirlo o restaurar un respaldo primero")
    perfil = dict(perfil, nombre=texto(perfil.get("nombre")))
    if original:
        indice = next((i for i, p in enumerate(perfiles) if p["nombre"] == original), None)
        if indice is None:
            raise ValueError(f"No existe el suscriptor {original!r}")
        perfiles[indice] = perfil
    else:
        perfiles.append(perfil)
    validar(perfiles)
    regiones = elementos(perfil.get("regiones")) + elementos(perfil.get("empleo_regiones"))
    if regiones:  # un nombre mal escrito no debe llegar al archivo
        try:
            seace.resolver_zonas(bot.sesion(), regiones)
        except ValueError:
            raise
        except Exception as e:  # sin red no se puede comprobar: el bot lo avisará
            log.warning("No se pudo comprobar las regiones: %s", e)
    respaldo = instalar(serializar(perfiles))
    if original and original != perfil["nombre"]:
        renombrar_estado(original, perfil["nombre"])
    return respaldo


def cambiar(nombre, **campos):
    perfiles, error = leer()
    if error:
        raise ValueError("perfiles.ini tiene un error y hay que corregirlo o restaurar un respaldo primero")
    if nombre not in [p["nombre"] for p in perfiles]:
        raise ValueError(f"No existe el suscriptor {nombre!r}")
    actuales = [dict(p, **campos) if p["nombre"] == nombre else p for p in perfiles]
    validar(actuales)
    return instalar(serializar(actuales))


def eliminar(nombre):
    perfiles, error = leer()
    if error:
        raise ValueError("perfiles.ini tiene un error y hay que corregirlo o restaurar un respaldo primero")
    restantes = [p for p in perfiles if p["nombre"] != nombre]
    if len(restantes) == len(perfiles):
        raise ValueError(f"No existe el suscriptor {nombre!r}")
    if not restantes:
        raise ValueError("Tiene que quedar al menos un suscriptor; el bot no se ejecuta con el archivo vacío")
    return instalar(serializar(restantes))


# ------------------------------------------------------------------ catálogos

catalogo = {"regiones": None, "entidades": None, "error": None}
provincias_cache = {}


def cargar_entidades():
    """Entidades con procesos abiertos hoy (para autocompletar), con cuántos tienen."""
    try:
        s = bot.sesion()
        r = s.get(seace.URL_OPORTUNIDADES.format(dep="0", texto="0"), timeout=180)
        r.raise_for_status()
        procesos = seace.procesos_oportunidades(r.json() or [], datetime.now(uniq.LIMA))
        catalogo["entidades"] = sorted(Counter(x["entidad"] for x in procesos).items())
    except Exception as e:
        catalogo["entidades"] = []
        catalogo["error"] = bot.error_corto(e)


def regiones():
    if catalogo["regiones"] is None:
        try:
            filas = seace.maestra(bot.sesion(), f"{seace.URL_MAESTRAS}/listar-departamento", catalogo.setdefault("maestras", {}), "dep")
            catalogo["regiones"] = sorted(({"nom": d["nom"], "id": d["id"]} for d in filas), key=lambda d: d["nom"])
        except Exception as e:
            log.warning("No se pudo leer las regiones: %s", e)
            return []
    return catalogo["regiones"]


def provincias(nombre):
    clave = seace.normal(nombre)
    dep = next((d for d in regiones() if seace.normal(d["nom"]) == clave), None)
    if not dep:
        return []
    if clave not in provincias_cache:
        filas = seace.maestra(bot.sesion(), f"{seace.URL_MAESTRAS}/listar-provincia/{dep['id']}", catalogo.setdefault("maestras", {}),
                              f"prov{dep['id']}")
        provincias_cache[clave] = sorted(p["nom"] for p in filas)
    return provincias_cache[clave]


# --------------------------------------------------- vista previa y envío

def vista_previa(perfil):
    """Genera el informe de ese perfil con datos de hoy, sin enviar ni guardar nada."""
    nombre = texto(perfil.get("nombre")) or "Sin nombre"
    p = bot.perfil_de_seccion(nombre, a_seccion(perfil))
    ahora = datetime.now(uniq.LIMA)
    s = bot.sesion()
    estado = copy.deepcopy(bot.cargar_estado())
    base, error = bot.descargar_uniq(s, ahora) if p["uniq"] else (None, None)
    asunto, _, cuerpo, *_ = bot.generar(p, s, ahora, estado, base, error)
    return {"asunto": asunto, "html": '<base target="_blank">' + informe.con_data_uri(cuerpo)}


def enviar_ahora(nombre):
    """Corre el bot para ese suscriptor (el mismo camino del envío diario)."""
    r = subprocess.run([sys.executable, str(bot.DIR / "bot.py"), "--perfil", nombre], cwd=bot.DIR,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    return {"ok": r.returncode == 0, "salida": (r.stdout + r.stderr).strip()[-1500:]}


def cola_del_log(n=40):
    try:
        return bot.LOG.read_text("utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return []


# ------------------------------------------------------------------- servidor

class Panel(BaseHTTPRequestHandler):
    clave = ""
    puerto = 0
    ultimo_uso = time.time()

    def log_message(self, *args):  # sin ruido en la consola
        pass

    def responder(self, codigo, datos, tipo="application/json; charset=utf-8"):
        cuerpo = datos if isinstance(datos, bytes) else json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; "
                         "script-src 'unsafe-inline'; img-src 'self' data:; frame-src about:")
        self.end_headers()
        self.wfile.write(cuerpo)

    def permitido(self):
        """Solo desde localhost (evita DNS rebinding) y, en las llamadas, con la clave de la sesión."""
        if self.headers.get("Host") not in (f"127.0.0.1:{self.puerto}", f"localhost:{self.puerto}"):
            return False
        origen = self.headers.get("Origin")
        return not origen or urlparse(origen).netloc == self.headers.get("Host")

    def despachar(self, metodo):
        Panel.ultimo_uso = time.time()
        ruta = urlparse(self.path)
        if not self.permitido():
            return self.responder(403, {"error": "Acceso no permitido"})
        if metodo == "GET" and ruta.path == "/":
            return self.responder(200, HTML.read_bytes(), "text/html; charset=utf-8")
        if metodo == "GET" and ruta.path == "/logo.png":
            logo = informe.logo_png()
            return self.responder(200 if logo else 404, logo or b"", "image/png")
        if not ruta.path.startswith("/api/"):
            return self.responder(404, {"error": "No existe"})
        if not secrets.compare_digest(self.headers.get("X-Clave", ""), self.clave):
            return self.responder(401, {"error": "Clave inválida: abre de nuevo la dirección que mostró admin.py"})
        datos = {}
        if metodo == "POST":
            largo = int(self.headers.get("Content-Length") or 0)
            if largo > MAX_CUERPO:
                return self.responder(413, {"error": "Datos demasiado grandes"})
            datos = json.loads(self.rfile.read(largo) or b"{}")
        try:
            self.responder(200, self.api(metodo, ruta.path[5:], parse_qs(ruta.query), datos))
        except (ValueError, KeyError, TypeError) as e:
            self.responder(400, {"error": str(e) if isinstance(e, ValueError) else f"Datos incompletos: {e}"})
        except Exception as e:
            log.exception("Panel: %s %s", metodo, ruta.path)
            self.responder(500, {"error": bot.error_corto(e)})

    def api(self, metodo, nombre, consulta, datos):
        if metodo == "GET":
            if nombre == "estado":
                perfiles, error = leer()
                return {"perfiles": perfiles, "error": error, "respaldos": len(lista_respaldos())}
            if nombre == "regiones":
                return {"regiones": [d["nom"] for d in regiones()]}
            if nombre == "provincias":
                return {"provincias": provincias(consulta.get("region", [""])[0])}
            if nombre == "entidades":
                if catalogo["entidades"] is None:
                    return {"listo": False}
                return {"listo": True, "error": catalogo["error"], "entidades": catalogo["entidades"]}
            if nombre == "respaldos":
                return {"respaldos": lista_respaldos()}
            if nombre == "log":
                return {"lineas": cola_del_log()}
        else:
            if nombre == "guardar":
                return {"respaldo": guardar(datos.get("original"), datos["perfil"])}
            if nombre == "pausar":
                return {"respaldo": cambiar(datos["nombre"], pausado=bool(datos["pausado"]))}
            if nombre == "eliminar":
                return {"respaldo": eliminar(datos["nombre"])}
            if nombre == "restaurar":
                return {"respaldo": restaurar(datos["archivo"])}
            if nombre in ("vista", "enviar"):
                if not trabajo.acquire(blocking=False):
                    raise ValueError("Ya hay una vista previa o un envío en curso; espera a que termine")
                try:
                    return vista_previa(datos["perfil"]) if nombre == "vista" else enviar_ahora(datos["nombre"])
                finally:
                    trabajo.release()
        raise ValueError("Acción desconocida")

    def do_GET(self):
        self.despachar("GET")

    def do_POST(self):
        self.despachar("POST")


def main():
    p = argparse.ArgumentParser(description="Panel local de suscriptores (solo 127.0.0.1).")
    p.add_argument("--puerto", type=int, default=8787)
    p.add_argument("--minutos", type=int, default=60, help="se apaga tras estos minutos sin uso (0 = nunca)")
    args = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    bot.cargar_env()
    bot.configurar_log()

    Panel.clave, Panel.puerto = secrets.token_urlsafe(16), args.puerto
    servidor = ThreadingHTTPServer(("127.0.0.1", args.puerto), Panel)  # nunca 0.0.0.0
    threading.Thread(target=cargar_entidades, daemon=True).start()
    if args.minutos:
        def vigilar():
            while time.time() - Panel.ultimo_uso < args.minutos * 60:
                time.sleep(30)
            print("Sin uso: el panel se apagó.")
            servidor.shutdown()
        threading.Thread(target=vigilar, daemon=True).start()
    print(f"\nPanel de suscriptores listo. Ábrelo en tu navegador (con el túnel SSH activo):\n\n"
          f"    http://127.0.0.1:{args.puerto}/?c={Panel.clave}\n\nCtrl+C para cerrarlo.\n")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
