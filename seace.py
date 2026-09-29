"""Búsqueda en SEACE, solo con fuentes públicas oficiales (sin login ni captcha).

- Contrataciones menores (hasta 8 UIT): buscador público de prod6.seace.gob.pe, en tiempo real.
- Procedimientos de selección (licitaciones, concursos, subastas, comparación de precios...):
  "Oportunidades de Negocio" del SEACE (prod4.seace.gob.pe/openegocio), que lista los
  procedimientos con el registro de participantes abierto, con su cronograma y sus bases.
El buscador clásico de SEACE 3.0 (prod2) está protegido con reCAPTCHA: no se usa.

Cómo se busca una frase como "sistema de seguridad ciudadana":
- los buscadores no sirven para frases (buscan el texto exacto) y distinguen tildes;
- así que a cada fuente se le pide la raíz de la palabra más larga ("seguridad"), con y sin
  tildes, y aquí se queda solo lo que contiene TODAS las palabras de la frase, por raíz y
  sin distinguir tildes ni mayúsculas ("sistema académico" encuentra "SISTEMA DE GESTIÓN ACADÉMICA");
- una frase entre comillas exige además que las palabras vayan juntas (ver coincide()).
"""
import itertools
import re
import unicodedata
from datetime import datetime
from urllib.parse import quote

URL_MENORES = "https://prod6.seace.gob.pe/v1/s8uit-services/buscadorpublico/contrataciones/buscador"
FICHA_MENOR = "https://prod6.seace.gob.pe/buscador-publico/contrataciones/{}"
PORTAL_MENORES = "https://prod6.seace.gob.pe/buscador-publico/contrataciones"
# Oportunidades de Negocio: objeto / departamento / texto / tipo de proceso ("0" = todos).
URL_OPORTUNIDADES = ("https://prod4.seace.gob.pe:8086/api/oportunidades/codObjeto/codDepartamento/"
                     "sintesisProceso/codTipoProceso/0/0/{}/0")
FICHA_PROCESO = "https://prod4.seace.gob.pe/openegocio/#/ficha/idProceso/{}"
URL_BASES = "https://prod1.seace.gob.pe/SeaceWeb-PRO/SdescargarArchivoAlfresco?fileCode={}"
PORTAL_OPORTUNIDADES = "https://prod4.seace.gob.pe/openegocio/"
VACIAS ={"de", "del", "la", "las", "el", "los", "y", "e", "o", "u", "para", "por", "en", "con", "a", "al", "un", "una"}


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
# Todas devuelven el mismo formato de proceso:
# {id, fuente, tipo, titulo, entidad, codigo, url, cierre, abierta, inicio, convocatoria, monto}
# y, si aplica, "bases" (enlace al documento) y "pie_cierre" (qué es la fecha de cierre).

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


def _fecha(texto, zona):
    return datetime.strptime(texto, "%d/%m/%Y %H:%M:%S").replace(tzinfo=zona) if texto else None


def _monto(texto):
    try:
        return float(texto)
    except (TypeError, ValueError):
        return 0  # "---": valor referencial reservado


def procesos_oportunidades(filas, ahora):
    """Filas de Oportunidades de Negocio (una por ítem) -> un proceso por idProcedimiento, solo los
    que tienen el registro de participantes abierto o por abrir."""
    por_proceso = {}
    for fila in filas:
        por_proceso.setdefault(fila["idProcedimiento"], []).append(fila)
    salida = []
    for id_proceso, items in por_proceso.items():
        x = items[0]
        cierre = _fecha(x.get("fecFinParticipantes") or x.get("fechaFin"), ahora.tzinfo)
        if not cierre or cierre < ahora:
            continue
        inicio = _fecha(x.get("fecInicioParticipantes") or x.get("fechaInicio"), ahora.tzinfo)
        salida.append({
            "id": f"p-{id_proceso}", "fuente": "SEACE", "tipo": x.get("detTipoProceso") or "Procedimiento",
            "titulo": limpio(x.get("sintesisProceso") or x.get("detItem")), "entidad": limpio(x.get("detEntidad")),
            "codigo": x.get("nomenclatura") or "", "url": FICHA_PROCESO.format(id_proceso),
            "bases": URL_BASES.format(x["documentoBase"]) if x.get("documentoBase") else None,
            "cierre": cierre, "abierta": not inicio or inicio <= ahora, "inicio": inicio, "pie_cierre": "fin de registro",
            "convocatoria": _fecha(x.get("fechaConvocatoria"), ahora.tzinfo), "monto": _monto(x.get("valorReferencial")),
            # la búsqueda mira la descripción del proceso y la de todos sus ítems
            "texto": " ".join([x.get("sintesisProceso") or ""] + [i.get("detItem") or "" for i in items]),
        })
    return salida


def procedimientos(s, frase, ahora):
    """Procedimientos de selección con registro abierto que calzan con la frase."""
    salida = {}
    for termino in consulta(frase):
        r = s.get(URL_OPORTUNIDADES.format(quote(termino, safe="")), timeout=90)
        r.raise_for_status()
        for x in procesos_oportunidades(r.json() or [], ahora):
            if coincide(x["texto"], frase):
                salida[x["id"]] = x
    return list(salida.values())


def procedimientos_de_entidades(s, entidades, ahora):
    """{entidad: [procesos con registro abierto]} para las entidades que sigues (parte de su nombre,
    sin distinguir tildes ni mayúsculas). Descarga el listado completo una sola vez (~3.000 filas)."""
    r = s.get(URL_OPORTUNIDADES.format("0"), timeout=180)
    r.raise_for_status()
    procesos = procesos_oportunidades(r.json() or [], ahora)
    normal = lambda t: " ".join(sin_tildes(t).upper().split())
    return {e: [x for x in procesos if normal(e) in normal(x["entidad"])] for e in entidades}
