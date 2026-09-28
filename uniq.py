"""Cotizaciones de la UNIQ: listado público y lectura del TDR/EETT (PDF público).

Usa el mismo endpoint que la página "ver_cotizaciones" y del PDF extrae las secciones que
sirven para decidir si cotizar. Devuelve el texto tal como viene: el formato es cosa de informe.py.
"""
import logging
import re
from datetime import datetime, timedelta, timezone

import pymupdf

BASE = "https://cotizaciones.uniq.edu.pe"
URL_PAGINA = f"{BASE}/cotizaciones/ver_cotizaciones"
URL_LISTADO = f"{BASE}/cotizaciones/servicio_listar_publicadas"
URL_TDR = f"{BASE}/cotizaciones/imprimir?id_requerimiento={{}}"
URL_LOGIN = f"{BASE}/login"

# Perú no usa horario de verano desde 1994: UTC-5 fijo, sin depender de tzdata.
LIMA = timezone(timedelta(hours=-5), "America/Lima")
DIAS_ATRAS = 30   # entre publicación y fecha límite pasan <= 7 días; 30 cubre de sobra

log = logging.getLogger("cotizbot")

# Secciones del TDR/EETT que se muestran: (clave, título en el informe, patrón del
# encabezado en el PDF, máx. caracteres). Cada encabezado va a la primera que coincida.
# ponytail: Gmail recorta el HTML arriba de ~102 KB. Una ficha completa pesa ~8 KB y solo
# la llevan las nuevas (mediana 6 al día, p90 13): los días de muchas nuevas Gmail muestra
# "Ver mensaje completo" al final; el resumen y las tablas de arriba siempre se ven.
SECCIONES = [
    ("objetivo", "Objetivo", r"OBJETIVO|DESCRIPCI[OÓ]N GENERAL", 400),
    ("requisitos", "Requisitos del proveedor", r"REQUISITO", 1200),
    ("plazo", "Plazo y lugar", r"PLAZO(?!.*RESPUESTA)|LUGAR", 600),
    ("pago", "Forma de pago", r"PAGO", 400),
    ("adelanto", "Adelantos", r"ADELANTO", 200),
    ("garantia", "Garantías", r"GARANT", 250),
    ("penalidad", "Penalidades", r"PENALIDAD", 200),
    ("tecnico", "Características técnicas",
     r"CARACTER[IÍ]STICAS|ESPECIFICACIONES T|ALCANCE|T[EÉ]RMINOS DE REFERENCIA", 400),
]
ENCABEZADO = re.compile(r"^\s*(\d{1,2})\s*\.\s+(.+?)\s*$")               # "10 . LUGAR Y PLAZO ..."
ITEM = re.compile(r"^\s*\d+\.\d+\s*-\s*(.+?)\s*\n\s*CANTIDAD:\s*([\d.,]+)", re.M)  # "3.1 - GASOHOL\nCANTIDAD: 300.00"
# Solo ligaduras: NFKC también convertiría "Nº" en "No".
LIGADURAS = {0xFB00: "ff", 0xFB01: "fi", 0xFB02: "fl", 0xFB03: "ffi", 0xFB04: "ffl"}
PIE_PAGINA = re.compile(r"^(Usuario:|Impresi[oó]n:|Fecha de (creaci[oó]n|impresi[oó]n):).*\n?", re.M)
DESIERTA = re.compile(r"\s*-\s*(NO SE ALCANZ[OÓ] EL N[UÚ]MERO M[IÍ]NIMO DE POSTORES|FALTA DE POSTORES)\s*$", re.I)


def recortar(texto, n):
    if len(texto) <= n:
        return texto
    return texto[:n].rsplit(" ", 1)[0] + " […]"


# ------------------------------------------------------------------- listado

def obtener_convocatorias(s, ahora):
    """Convocatorias "Actuales", con el mismo criterio que usa el JS de la página."""
    pagina = s.get(URL_PAGINA, timeout=30)
    pagina.raise_for_status()
    token = re.search(r"_token_\s*=\s*'([^']+)'", pagina.text)
    if not token:
        raise RuntimeError("No se encontró el token CSRF en la página (¿cambió el sitio?)")

    r = s.post(URL_LISTADO, timeout=30, headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
               data={"_token": token.group(1), "nro_solicitud": -1, "tipo": "*", "descripcion": "",
                     "fecha_inicial": f"{ahora - timedelta(days=DIAS_ATRAS):%Y-%m-%d}",
                     "fecha_final": f"{ahora:%Y-%m-%d}"})
    r.raise_for_status()
    respuesta = r.json()
    if respuesta.get("rsta") != "ok":
        raise RuntimeError(f"El servicio respondió: {respuesta.get('message') or respuesta}")

    activas = []
    for x in respuesta["data"]:
        limite = datetime.strptime(x["fecha_limite"][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=LIMA)
        # "Actuales" = sin cuadro comparativo (idcuadro -1) y dentro de la fecha límite.
        if str(x["idcuadro"]) != "-1" or ahora > limite:
            continue
        bien = x["tipo_bien"] == "B"
        descripcion = (x["descripcion"] or x["objeto"] or "").strip()
        activas.append({
            "id": x["id"],  # único por publicación: una 2da convocatoria trae id nuevo
            "tipo": "Bien" if bien else "Servicio",
            "doc": "EETT" if bien else "TDR",
            "numero": abs(int(x["nro_solicitud"])),
            "convocatoria": int(x["nro_convocatoria"] or 1),
            "titulo": DESIERTA.sub("", descripcion),
            "desierta": bool(DESIERTA.search(descripcion)),  # la convocatoria anterior no tuvo postores suficientes
            "dependencia": x.get("dependencia") or "",
            "correo": x.get("correo_area_usuaria") or "",
            "fuente": x.get("fuente_financiamiento") or "",
            "plazo_entrega": x.get("plazo_entrega"),
            "limite": limite,
            "tdr_url": URL_TDR.format(x["id_requerimiento"]) if x.get("tiene_tdr") else None,
        })
    activas.sort(key=lambda c: (c["limite"], c["numero"]))
    return activas


# ----------------------------------------------------------------- PDF TDR/EETT

def unir_renglones(lineas):
    """Une los renglones que el PDF cortó a media frase: el siguiente empieza en minúscula, o
    el anterior llegó al ancho de la página (>= 80 caracteres) sin cerrar con . : ;
    ponytail: un ítem de lista largo y sin punto final se pega al siguiente; sube el umbral si molesta."""
    salida, previo = [], ""
    for linea in lineas:
        corte = linea[:1].islower() or linea[:1] in "(,;" or (len(previo) >= 80 and previo[-1] not in ".:;")
        if salida and corte:
            salida[-1] += " " + linea
        else:
            salida.append(linea)
        previo = linea
    return salida


def leer_pdf(contenido):
    """Devuelve ({clave: texto}, [(ítem, cantidad)]) a partir del PDF del TDR/EETT."""
    with pymupdf.open(stream=contenido, filetype="pdf") as doc:
        texto = "\n".join(pagina.get_text() for pagina in doc)
    texto = texto.translate(LIGADURAS)                    # "ﬁnalidad" -> "finalidad"
    texto = PIE_PAGINA.sub("", texto)                     # pie de página repetido
    texto = re.sub(r"[ \t]+", " ", texto)

    partes, actual, ultimo = {}, None, 0
    for linea in texto.splitlines():
        m = ENCABEZADO.match(linea)
        # Encabezado real: todo en mayúsculas y numeración creciente
        # (así "5 . MONTAJE" dentro de la sección 13 queda como parte de la 13).
        if m and m.group(2).isupper() and int(m.group(1)) > ultimo:
            ultimo = int(m.group(1))
            actual = next((clave for clave, _, patron, _ in SECCIONES if re.search(patron, m.group(2))), None)
            if actual in partes:  # segunda sección con la misma clave: se rotula
                partes[actual].append(f"— {m.group(2)} —")
            continue
        if actual and linea.strip():
            partes.setdefault(actual, []).append(linea.strip())

    limites = {clave: n for clave, _, _, n in SECCIONES}
    secciones = {clave: recortar("\n".join(unir_renglones(lineas)), limites[clave]) for clave, lineas in partes.items()}

    items = []
    for nombre, cantidad in ITEM.findall(texto):
        if "." in cantidad:
            cantidad = cantidad.rstrip("0").rstrip(".")
        items.append((nombre.strip(), cantidad))
    return secciones, items


def leer_tdr(s, c):
    """Completa la convocatoria con lo extraído del PDF; si falla, lo anota y sigue."""
    c["secciones"], c["items"], c["error_pdf"] = {}, [], None
    if not c["tdr_url"]:
        return
    try:
        r = s.get(c["tdr_url"], timeout=30)
        r.raise_for_status()
        if r.content[:4] != b"%PDF":
            raise ValueError("la respuesta no es un PDF")
        c["secciones"], c["items"] = leer_pdf(r.content)
    except Exception as e:
        log.warning("No se pudo leer el %s de la cotización %s: %s", c["doc"], c["numero"], e)
        c["error_pdf"] = str(e)
