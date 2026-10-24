"""Ofertas de empleo, solo con fuentes públicas oficiales (sin login ni captcha):

- Empleos Perú (MTPE, sector privado y público): su buscador es una API JSON abierta; se leen todas las
  ofertas vigentes (unas 1.600, en 4 páginas) y se filtran aquí por lugar, palabra clave y sueldo.
- Talento Perú (SERVIR, sector público): una página JSF (PrimeFaces) que pagina de 10 en 10. Se consulta
  por departamento (o por palabra clave si no hay regiones) y se recorren sus páginas.

Ambas devuelven el mismo formato de oferta:
{id, fuente, titulo, entidad, lugar ("CUSCO/LA CONVENCION/SANTA ANA"), sueldo_min, sueldo_max (None = no
indica), sueldo (texto), publicado, cierre (None si no se conoce), vacantes, detalle, url, convocatoria}.
"""
import hashlib
import re
from datetime import datetime
from urllib.parse import urlencode

import seace
import uniq

MTPE = "https://mtpe-candidatos.empleosperu.gob.pe"
URL_MTPE_LISTA = MTPE + "/api/jobs"
URL_MTPE_LUGARES = MTPE + "/api/taxonomies/location"
URL_MTPE_OFERTA = MTPE + "/search-jobs/description?jobId={}"
PORTAL_MTPE = MTPE + "/search-jobs"
SERVIR = "https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml"
FORM = "frmLstOfertsLabo"
POR_PAGINA = 500        # lo que admite la API de MTPE por llamada
MAX_PAGINAS_MTPE = 8    # tope de seguridad: 4.000 ofertas
MAX_PAGINAS_SERVIR = 60  # 600 ofertas por búsqueda; Cusco, p. ej., tiene unas 190 (19 páginas)
SIN_TOPE = float("inf")


def numero(texto):
    """"S/. 3,651.00" -> 3651.0; None si no hay un monto."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", texto or "")
    return float(m.group(0).replace(",", "")) if m else None


def plata(n):
    return f"S/ {n:,.0f}"


# ---------------------------------------------------------------- Empleos Perú

def lugares_mtpe(s):
    """{código INEI: nombre} de departamentos (2 dígitos), provincias (4) y distritos (6)."""
    r = s.get(URL_MTPE_LUGARES, timeout=60)
    r.raise_for_status()
    return {x["id"]: x["name"] for x in r.json() if x.get("id") and x.get("name")}


def sueldo_mtpe(fila):
    """(mínimo, máximo, texto) del paquete de remuneración; (None, None, "") si no lo muestra."""
    paquetes = fila.get("offeredRemunerationPackages") or []
    if not fila.get("displaySalary", True) or not paquetes or fila.get("negotiableSalary"):
        return None, None, ""
    p = paquetes[0]
    minimo, maximo, rango = p.get("minimumAmount") or 0, p.get("maximumAmount"), p.get("type") or ""
    if rango.startswith(">="):
        return minimo, SIN_TOPE, f"{plata(minimo)} a más"
    if rango.startswith("<="):
        return 0, maximo, f"Hasta {plata(maximo)}"
    return minimo, maximo, f"{plata(minimo)} – {plata(maximo)}" if maximo else plata(minimo)


def oferta_mtpe(fila, lugares):
    cod = fila.get("location") or {}
    lugar = "/".join(lugares.get(cod.get(k), "") for k in ("DEPARTMENT", "PROVINCE", "DISTRICT")).strip("/")
    minimo, maximo, texto = sueldo_mtpe(fila)
    detalle = " · ".join(filter(None, [(fila.get("contractType") or {}).get("name"),
                                       (fila.get("hoursPerWeek") or {}).get("name"),
                                       (fila.get("educationDegree") or {}).get("name")]))
    return {"id": f"e-{fila['id']}", "fuente": "Empleos Perú", "titulo": " ".join((fila.get("positionTitle") or "").split()),
            "entidad": fila.get("companyName") or "", "lugar": lugar, "sueldo_min": minimo, "sueldo_max": maximo,
            "sueldo": texto, "publicado": fila.get("datePosted"), "cierre": None, "vacantes": None,
            "detalle": detalle, "url": URL_MTPE_OFERTA.format(fila["id"]), "convocatoria": ""}


def ofertas_mtpe(s):
    """Todas las ofertas vigentes de Empleos Perú."""
    lugares = lugares_mtpe(s)
    ofertas, desde, total = [], 0, 1
    for _ in range(MAX_PAGINAS_MTPE):
        r = s.get(URL_MTPE_LISTA, params={"limit": POR_PAGINA, "offset": desde}, timeout=120)
        r.raise_for_status()
        datos = r.json()
        total = datos.get("totalCount") or 0
        ofertas += [oferta_mtpe(f, lugares) for f in datos.get("data") or [] if f.get("active", True)]
        desde += POR_PAGINA
        if desde >= total:
            break
    return ofertas


# --------------------------------------------------------------------- SERVIR

def _texto(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ").split())


def _campo(bloque, rotulo):
    m = re.search(rotulo.replace(" ", r"\s+") + r"[^<]*</span>(?:\s|&nbsp;)*<span class=\"detalle-sp\">(.*?)</span>", bloque, re.S)
    return _texto(m.group(1)) if m else ""


def _fecha(texto):
    try:
        return datetime.strptime(texto.strip()[:10], "%d/%m/%Y")
    except ValueError:
        return None


def ofertas_de_pagina(html):
    """Ofertas de una respuesta de SERVIR (HTML de la página o respuesta parcial de PrimeFaces)."""
    ofertas = []
    for bloque in html.split('titulo-vacante')[1:]:
        titulo = re.search(r"<label>(.*?)</label>", bloque, re.S)
        entidad = re.search(r"<b>(.*?)</b>", bloque, re.S)
        if not titulo or not entidad:
            continue
        departamento, _, distrito = (p.strip() for p in _campo(bloque, "Ubicaci.n:").partition(" - "))
        convocatoria = _campo(bloque, "N.mero de Convocatoria:")
        sueldo = numero(_campo(bloque, "Remuneraci.n:"))
        o = {"fuente": "Talento Perú (SERVIR)", "titulo": _texto(titulo.group(1)), "entidad": _texto(entidad.group(1)),
             "lugar": "/".join(p for p in (departamento, distrito) if p), "sueldo_min": sueldo, "sueldo_max": sueldo,
             "sueldo": plata(sueldo) if sueldo else "", "publicado": _fecha(_campo(bloque, "Fecha Inicio de Publicaci.n:")),
             "cierre": _fecha(_campo(bloque, "Fecha Fin de Publicaci.n:")), "convocatoria": convocatoria,
             "vacantes": _campo(bloque, "Cantidad de Vacantes:"), "detalle": f"Convocatoria {convocatoria}" if convocatoria else "",
             "url": SERVIR}
        if o["publicado"]:
            o["publicado"] = f"{o['publicado']:%Y-%m-%d}"
        if o["cierre"]:  # la oferta vale hasta el final de ese día, hora de Lima
            o["cierre"] = o["cierre"].replace(hour=23, minute=59, tzinfo=uniq.LIMA)
        clave = "|".join([o["convocatoria"], o["entidad"], o["titulo"], o["lugar"]])
        o["id"] = "s-" + hashlib.sha1(clave.encode()).hexdigest()[:12]
        ofertas.append(o)
    return ofertas


def departamentos_servir(html):
    """{NOMBRE: código} del selector de ubicación (los códigos de SERVIR no son los del INEI)."""
    select = re.search(r'cboDep_input"[^>]*>(.*?)</select>', html, re.S)
    return {seace.normal(n): v for v, n in re.findall(r'<option value="(\d+)">([^<]+)</option>', select.group(1))
            if v != "0"} if select else {}


def codigos_servir(s):
    """{DEPARTAMENTO: código de SERVIR}, del selector de la página."""
    r = s.get(SERVIR, timeout=60)
    r.raise_for_status()
    return departamentos_servir(r.content.decode("utf-8", errors="replace"))


def _estado_vista(html):
    m = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', html) or \
        re.search(r'ViewState[^>]*><!\[CDATA\[([^\]]+)\]\]>', html)
    return m.group(1) if m else ""


def _paginas(html):
    m = re.search(r"P.gina (\d+) de (\d+)", html)
    return (int(m.group(1)), int(m.group(2))) if m else (1, 1)


def _boton_siguiente(html):
    m = re.search(r'<button id="(' + FORM + r':j_idt\d+)"(?:(?!</button>).)*?btn-paginator(?:(?!</button>).)*?>'
                  r'(?:(?!</button>).)*?Sig\.', html, re.S)
    return m.group(1) if m else None


def _enviar(s, vista, fuente, campos):
    datos = {"javax.faces.partial.ajax": "true", "javax.faces.partial.execute": "@all",
             "javax.faces.partial.render": f"{FORM}:mensaje {FORM}", FORM: FORM, f"{FORM}:txtPerfil": "",
             f"{FORM}:cboDep_focus": "", f"{FORM}:cboDep_input": "0", f"{FORM}:txtPuesto": "",
             f"{FORM}:autocompletar_input": "", f"{FORM}:txtNroConv": "", "javax.faces.ViewState": vista,
             "javax.faces.source": fuente, fuente: fuente, **campos}
    r = s.post(SERVIR, data=datos, headers={"Faces-Request": "partial/ajax", "X-Requested-With": "XMLHttpRequest"}, timeout=90)
    r.raise_for_status()
    return r.content.decode("utf-8", errors="replace")


def buscar_servir(s, codigo_departamento="0", perfil="", maximo=MAX_PAGINAS_SERVIR):
    """Ofertas de SERVIR de un departamento y/o con ese texto en el perfil, recorriendo las páginas."""
    pagina = s.get(SERVIR, timeout=60)
    pagina.raise_for_status()
    html0 = pagina.content.decode("utf-8", errors="replace")
    boton = re.search(r'<button id="(' + FORM + r':j_idt\d+)"[^>]*btn-sensitive[^>]*>(?:(?!</button>).)*?Buscar', html0, re.S)
    if not boton:
        raise RuntimeError("No se encontró el botón de búsqueda de SERVIR (¿cambió el sitio?)")
    html = _enviar(s, _estado_vista(html0), boton.group(1),
                   {f"{FORM}:cboDep_input": codigo_departamento, f"{FORM}:txtPerfil": perfil})
    ofertas, (n, total) = ofertas_de_pagina(html), _paginas(html)
    while n < min(total, maximo):
        siguiente = _boton_siguiente(html)
        if not siguiente:
            break
        html = _enviar(s, _estado_vista(html), siguiente,
                       {f"{FORM}:cboDep_input": codigo_departamento, f"{FORM}:txtPerfil": perfil})
        ofertas += ofertas_de_pagina(html)
        n = _paginas(html)[0]
    return ofertas


def enlace_busqueda(palabra="", region=""):
    """Enlace al buscador de Empleos Perú con la búsqueda ya hecha (acepta ?what=puesto&where=lugar).
    SERVIR no tiene algo así: su página es JSF y no lee la dirección."""
    consulta = {k: v for k, v in (("what", palabra.strip('"')), ("where", region.partition("/")[0].title())) if v}
    return PORTAL_MTPE + ("?" + urlencode(consulta) if consulta else "")


# ------------------------------------------------------------------ selección

def _partes_lugar(oferta):
    """(departamento, provincia, distrito) normalizados; faltan los que la fuente no da."""
    p = [seace.normal(x) for x in oferta["lugar"].split("/")]
    return p[0] if p else "", p[1] if len(p) > 2 else "", p[-1] if len(p) > 1 else ""


def en_regiones(oferta, regiones, provincia_de=None):
    """¿La oferta está en alguna de las regiones? regiones = ["CUSCO", "APURIMAC/ABANCAY"]. SERVIR solo da el
    distrito: su provincia se averigua con provincia_de[(departamento, distrito)] (viene de MTPE)."""
    if not regiones:
        return True
    dep, prov, dist = _partes_lugar(oferta)
    if not prov and provincia_de:
        prov = provincia_de.get((dep, dist), "")
    for texto in regiones:
        region, _, provincia = (seace.normal(p) for p in texto.partition("/"))
        if region == dep and (not provincia or provincia in (prov, dist)):
            return True
    return False


def provincias_de_distritos(lugares):
    """{(DEPARTAMENTO, DISTRITO): PROVINCIA} a partir de los códigos de MTPE."""
    mapa = {}
    for cod, nombre in lugares.items():
        if len(cod) == 6 and cod[:4] in lugares and cod[:2] in lugares:
            mapa.setdefault((seace.normal(lugares[cod[:2]]), seace.normal(nombre)), seace.normal(lugares[cod[:4]]))
    return mapa


def sueldo_alcanza(oferta, minimo):
    """Sin sueldo mínimo pedido, o sueldo no indicado (se deja ver: puede ser a convenir), o que llegue al mínimo."""
    return not minimo or oferta["sueldo_max"] is None or oferta["sueldo_max"] >= minimo


def agrupar(ofertas, palabras, regiones, vistas, minimo, provincia_de=None):
    """Filtra y agrupa: [(rótulo, [ofertas])]. Con palabras clave, un grupo por palabra (una oferta sale solo en la
    primera que la encuentra); sin ellas, un grupo por región o uno solo. Marca x["nuevo"]."""
    candidatas = [o for o in ofertas if en_regiones(o, regiones, provincia_de) and sueldo_alcanza(o, minimo)]
    for o in candidatas:
        o["nuevo"] = o["id"] not in vistas
    candidatas.sort(key=lambda o: str(o["publicado"] or ""), reverse=True)  # lo más reciente primero...
    candidatas.sort(key=lambda o: not o["nuevo"])                           # ...y lo nuevo antes que todo (orden estable)
    if palabras:
        grupos, usados = [], set()
        for frase in palabras:
            items = [o for o in candidatas if o["id"] not in usados and seace.coincide(o["titulo"], frase)]
            usados |= {o["id"] for o in items}
            grupos.append((frase, items))
        return grupos
    if len(regiones) > 1:
        grupos, usados = [], set()
        for texto in regiones:
            items = [o for o in candidatas if o["id"] not in usados and en_regiones(o, [texto], provincia_de)]
            usados |= {o["id"] for o in items}
            grupos.append((texto, items))
        return grupos
    return [(regiones[0] if regiones else "Todo el país", candidatas)]
