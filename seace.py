"""Búsqueda por palabras clave en SEACE, solo con fuentes públicas (sin login ni captcha).

- Contrataciones menores (hasta 8 UIT): buscador público de prod6.seace.gob.pe, en tiempo real.
- Procedimientos de selección (licitaciones, subastas, adjudicaciones...): API de Contrataciones
  Abiertas del OECE (estándar OCDS), que llega con 3 a 4 días de retraso.
El buscador clásico de SEACE 3.0 (prod2) está protegido con reCAPTCHA: no se usa.

Cómo se busca una frase como "sistema de seguridad ciudadana":
- ninguno de los dos buscadores sirve para frases (uno busca el texto exacto, el otro cualquier
  palabra suelta) y los dos distinguen tildes;
- así que a cada fuente se le pide la raíz de la palabra más larga ("seguridad"), con y sin
  tildes, y aquí se queda solo lo que contiene TODAS las palabras de la frase, por raíz y
  sin distinguir tildes ni mayúsculas ("sistema académico" encuentra "SISTEMA DE GESTIÓN ACADÉMICA");
- una frase entre comillas exige además que las palabras vayan juntas (ver coincide()).
"""
import itertools
import re
import unicodedata
from datetime import datetime, timedelta

URL_MENORES = "https://prod6.seace.gob.pe/v1/s8uit-services/buscadorpublico/contrataciones/buscador"
FICHA_MENOR = "https://prod6.seace.gob.pe/buscador-publico/contrataciones/{}"
PORTAL_MENORES = "https://prod6.seace.gob.pe/buscador-publico/contrataciones"
URL_OCDS = "https://contratacionesabiertas.oece.gob.pe/api/v1/search"
FICHA_OCDS = "https://contratacionesabiertas.oece.gob.pe/proceso/{}"
BUSQUEDA_OCDS = "https://contratacionesabiertas.oece.gob.pe/busqueda?search={}"
PORTAL_OCDS = "https://contratacionesabiertas.oece.gob.pe"
DIAS_OCDS = 30          # procedimientos convocados en los últimos 30 días
VACIAS = {"de", "del", "la", "las", "el", "los", "y", "e", "o", "u", "para", "por", "en", "con", "a", "al", "un", "una"}


# ------------------------------------------------------------ palabras clave

def sin_tildes(texto):
    return "".join(ch for ch in unicodedata.normalize("NFD", texto) if unicodedata.category(ch) != "Mn")


def limpio(texto):
    """Espacios dobles fuera y "¿" de vuelta a lo que era: SEACE guarda así las comillas y rayas
    tipográficas ("¿mejoramiento del estadio¿", "Cajabamba ¿ Huamachuco").
    ponytail: una pregunta real con "¿" saldría con comillas; en descripciones de compras no aparecen."""
    texto = " ".join((texto or "").split()).replace(" ¿ ", " – ")
    return texto.replace("¿", '"')


def raiz(palabra):
    """"académico" -> "académic", "sistemas" -> "sistem": así calza con académica, sistema..."""
    if len(palabra) >= 6:
        palabra = palabra[:-1] if palabra.endswith("s") else palabra
        palabra = palabra[:-1] if palabra[-1] in "aeoáéó" else palabra
    return palabra


def terminos(frase):
    return [raiz(p) for p in re.findall(r"\w+", frase.lower()) if p not in VACIAS]


def es_exacta(frase):
    return len(frase) > 1 and frase[0] == frase[-1] == '"'


def coincide(texto, frase):
    """True si el texto tiene todas las palabras de la frase (por raíz, sin tildes ni mayúsculas).
    Entre comillas, además tienen que ir juntas: dentro de una ventana de (palabras de la frase + 3).
    - sistema de seguridad ciudadana: "SISTEMA DE CÁMARAS ... SERVICIO DE SEGURIDAD CIUDADANA" sí;
    - "sistema académico": "SISTEMA DE GESTIÓN ACADÉMICA" sí, "sistema de aire ... servicios académicos" no.
    ponytail: prueba todas las combinaciones de posiciones; va sobrado para descripciones de ~100 palabras."""
    palabras = re.findall(r"\w+", sin_tildes(texto).lower())
    raices = [sin_tildes(r) for r in terminos(frase)]
    posiciones = [[i for i, p in enumerate(palabras) if p.startswith(r)] for r in raices]
    if not raices or not all(posiciones):
        return False
    if not es_exacta(frase):
        return True
    ventana = len(raices) + 3
    return any(max(combo) - min(combo) < ventana for combo in itertools.product(*posiciones))


def consulta(frase):
    """Qué se le pide a cada buscador: la raíz más larga de la frase (la más selectiva; si
    empatan, la última), con y sin tildes. "maíz" -> ["maíz", "maiz"]."""
    ts = terminos(frase)
    if not ts:
        return []
    mejor = max(reversed(ts), key=len)
    return list(dict.fromkeys([mejor, sin_tildes(mejor)]))


# ------------------------------------------------------------------- fuentes
# Las dos devuelven el mismo formato de proceso:
# {id, fuente, tipo, titulo, entidad, codigo, url, cierre, abierta, convocatoria, monto}

def menores(s, frase, ahora):
    """Contrataciones menores vigentes que calzan con la frase y cuya cotización no ha cerrado."""
    salida = {}
    for termino in consulta(frase):
        pagina = 1
        while True:
            r = s.get(URL_MENORES, timeout=30, params={
                "palabra_clave": termino, "anio": ahora.year, "lista_estado_contrato": 2,  # 2 = Vigente
                "page": pagina, "page_size": 100, "campo_orden": 1, "orden": 2})
            r.raise_for_status()
            datos = r.json()
            for x in datos.get("data") or []:
                if not x.get("fecFinCotizacion") or not coincide(x.get("desObjetoContrato") or "", frase):
                    continue
                cierre = datetime.strptime(x["fecFinCotizacion"], "%d/%m/%Y %H:%M:%S").replace(tzinfo=ahora.tzinfo)
                if cierre < ahora:  # "Vigente" sigue así un tiempo después de cerrar la cotización
                    continue
                inicio = datetime.strptime(x["fecIniCotizacion"], "%d/%m/%Y %H:%M:%S").replace(tzinfo=ahora.tzinfo)
                salida[x["idContrato"]] = {
                    "id": f"m-{x['idContrato']}", "fuente": "SEACE", "tipo": "Contratación menor",
                    "titulo": limpio(x["desObjetoContrato"]), "entidad": limpio(x["nomEntidad"]),
                    "codigo": x["desContratacion"], "url": FICHA_MENOR.format(x["idContrato"]),
                    "cierre": cierre, "abierta": inicio <= ahora, "inicio": inicio, "convocatoria": None, "monto": 0,
                }
            if pagina * 100 >= (datos.get("pageable") or {}).get("totalElements", 0):
                break
            pagina += 1
    return list(salida.values())


def procedimientos(s, frase, ahora):
    """Procedimientos de selección que calzan con la frase, convocados en los últimos DIAS_OCDS días."""
    desde = (ahora - timedelta(days=DIAS_OCDS)).date()
    meses = sorted({(desde.year, desde.month), (ahora.year, ahora.month)})
    salida = {}
    for termino in consulta(frase):
        for anio, mes in meses:
            pagina = 1
            while True:
                r = s.get(URL_OCDS, timeout=60, params={
                    "search": termino, "year": anio, "month": mes, "page": pagina, "paginateBy": 100, "format": "json"})
                r.raise_for_status()
                datos = r.json()
                for resultado in datos.get("results") or []:
                    c = resultado.get("compiledRelease") or {}
                    t = c.get("tender") or {}
                    inicio = (t.get("tenderPeriod") or {}).get("startDate")
                    if (not inicio or datetime.fromisoformat(inicio).date() < desde
                            or not coincide(t.get("description") or "", frase)):
                        continue
                    salida[c["ocid"]] = {
                        "id": c["ocid"], "fuente": "SEACE", "tipo": t.get("procurementMethodDetails") or "Procedimiento",
                        "titulo": limpio(t.get("description")), "entidad": limpio((c.get("buyer") or {}).get("name")),
                        "codigo": t.get("title") or "", "url": FICHA_OCDS.format(c["ocid"]),
                        "cierre": None, "abierta": False, "inicio": None, "convocatoria": datetime.fromisoformat(inicio),
                        "monto": (t.get("value") or {}).get("amount") or 0,  # 0 si el valor referencial es reservado
                    }
                if not (datos.get("pagination") or {}).get("has_next"):
                    break
                pagina += 1
    return list(salida.values())
