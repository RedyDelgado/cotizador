"""Autoprueba sin red: lector de TDR/EETT, formato de textos, búsqueda por frase y perfiles.
Uso: python test_bot.py"""
import pymupdf

import bot
import informe
import seace
import uniq

LINEAS = [
    "1 . FINALIDAD PUBLICA", "Texto que no se muestra.",
    "2 . OBJETIVO DE LA CONTRATACION", "Adquirir sillas para", "las aulas.",
    "3 . CARACTERISTICAS TECNICAS", "3.1 - SILLA APILABLE", "CANTIDAD: 40.00",
    "Usuario: jperez", "Fecha de impresion: 2026-09-28 12:00:00",   # pie de página
    "4 . REQUISITOS DE CALIFICACION", "RNP vigente.",
    "1 . EXPERIENCIA DEL POSTOR", "S/ 50,000 facturados.",          # subtítulo: sigue en la 4
    "5 . PLAZO DE ENTREGA", "10 dias calendario.",
    "LA ENTREGA SE REALIZARA EN EL ALMACEN CENTRAL DE LA UNIVERSIDAD DENTRO DEL PLAZO", "INDICADO.",  # corte por ancho
    "6 . PLAZO PARA RESPUESTAS ENTRE LAS PARTES", "No debe salir.",
    "7 . LUGAR DE ENTREGA", "Almacen central.",
]

doc = pymupdf.open()
pagina = doc.new_page()
for i, linea in enumerate(LINEAS):
    pagina.insert_text((50, 50 + i * 14), linea, fontsize=10)
secciones, items = uniq.leer_pdf(doc.tobytes())

assert secciones["objetivo"] == "Adquirir sillas para las aulas.", secciones["objetivo"]
assert "S/ 50,000" in secciones["requisitos"] and "EXPERIENCIA" in secciones["requisitos"]
assert "10 dias" in secciones["plazo"] and "Almacen central." in secciones["plazo"]
assert "No debe salir" not in secciones["plazo"]
assert "DEL PLAZO INDICADO." in secciones["plazo"], secciones["plazo"]
assert "calendario.\nLA ENTREGA" in secciones["plazo"]  # tras un punto no se une
assert not any("Usuario" in t or "impresion" in t for t in secciones.values())
assert items == [("SILLA APILABLE", "40")], items
assert "finalidad" not in secciones

# Formato: mayúsculas -> oración / nombre propio, conservando siglas y códigos.
assert informe.oracion("ADQUISICIÓN DE PERGOLA TIPO 01-A PARA LA UNIQ") == "Adquisición de pergola tipo 01-A para la UNIQ"
assert informe.oracion("El proveedor con RNP vigente") == "El proveedor con RNP vigente"
assert informe.nombre_propio("MUNICIPALIDAD PROVINCIAL DE LA CONVENCION - SANTA ANA") == \
    "Municipalidad Provincial de la Convencion - Santa Ana"
assert informe.nombre_propio("MTC-PROYECTO ESPECIAL DE LA UNIQ") == "MTC-Proyecto Especial de la UNIQ"
assert informe.nombre_propio("CANON Y SOBRECANON, RENTA DE ADUANAS Y PARTICIPACIONES") == \
    "Canon y Sobrecanon, Renta de Aduanas y Participaciones"  # la "y" no es una sigla
assert informe.png_icono("requisitos")[:4] == b"\x89PNG"  # el SVG de Lucide se rasteriza en este servidor

# Búsqueda por frase: todas las palabras, por raíz, sin distinguir tildes ni mayúsculas.
assert seace.coincide("ADQUISICIÓN DEL SISTEMA DE GESTIÓN ACADÉMICA", "sistema académico")
assert seace.coincide("IMPLEMENTACION DE SOFTWARES DE GESTION", "software")
assert seace.coincide("SISTEMA DE VIDEOVIGILANCIA PARA SEGURIDAD CIUDADANA", "sistema de seguridad ciudadana")
assert not seace.coincide("COMBUSTIBLE PARA LA GERENCIA DE SEGURIDAD CIUDADANA", "sistema de seguridad ciudadana")
assert not seace.coincide("MANTENIMIENTO DEL EDIFICIO ACADEMICO", "sistema académico")
LEJANAS = "ADQUISICIÓN DE SISTEMA DE ENFRIAMIENTO - AIRE ACONDICIONADO PARA LA OBRA: MEJORAMIENTO DE LOS SERVICIOS ACADÉMICOS"
assert seace.coincide(LEJANAS, "sistema académico")          # sin comillas: todas las palabras, en cualquier parte
assert not seace.coincide(LEJANAS, '"sistema académico"')     # entre comillas: tienen que ir juntas
assert seace.coincide("ADQUISICIÓN DEL SISTEMA DE GESTIÓN ACADÉMICA", '"sistema académico"')
assert seace.coincide("MATERIALES PARA EL SISTEMA DE CAMARAS DE VIDEOVIGILANCIA PARA OBRA: MEJORAMIENTO DEL SERVICIO "
                      "DE SEGURIDAD CIUDADANA", "sistema de seguridad ciudadana")
assert seace.consulta('"sistema académico"') == ["académic", "academic"]
assert seace.consulta("sistema de seguridad ciudadana") == ["seguridad"]
assert seace.consulta("maíz") == ["maíz", "maiz"] and seace.consulta("sistema académico") == ["académic", "academic"]
assert seace.limpio("PROYECTO  ¿ESTADIO¿ DV CAJABAMBA ¿ HUAMACHUCO") == 'PROYECTO "ESTADIO" DV CAJABAMBA – HUAMACHUCO'
# Oportunidades de Negocio: una fila por ítem -> un proceso; los de registro cerrado no salen.
from datetime import datetime
ahora = datetime(2026, 9, 28, 12, 0, tzinfo=uniq.LIMA)
fila = {"idProcedimiento": 7, "detTipoProceso": "Subasta Inversa Electrónica", "nomenclatura": "SIE-SIE-1-2026-X-1",
        "sintesisProceso": "ADQUISICIÓN DE CEMENTO", "detEntidad": "MUNICIPALIDAD PROVINCIAL DE LA CONVENCION",
        "detItem": "CEMENTO PORTLAND TIPO IP", "fecInicioParticipantes": "24/09/2026 00:01:00",
        "fecFinParticipantes": "01/10/2026 23:59:00", "fechaConvocatoria": "23/09/2026 22:29:00",
        "valorReferencial": "---", "documentoBase": "abc"}
procesos = seace.procesos_oportunidades([fila, dict(fila, detItem="AGREGADO FINO"),
                                         dict(fila, idProcedimiento=8, fecFinParticipantes="27/09/2026 23:59:00")], ahora)
assert len(procesos) == 1 and procesos[0]["id"] == "p-7" and procesos[0]["monto"] == 0, procesos
assert "AGREGADO FINO" in procesos[0]["texto"] and procesos[0]["bases"].endswith("fileCode=abc")
assert seace.coincide(procesos[0]["texto"], "agregado fino")  # busca también en los ítems

# Tope de tamaño por sección: con muchos procesos nuevos, lo que no entra se cuenta, no se pierde en silencio.
muchos = [dict(procesos[0], id=f"p-{i}", nuevo=True) for i in range(60)]
html_chico = informe.html_grupos([("cemento", muchos)], ahora, informe.mostrar, "", cupo={"nuevas_breves": 60},
                                 max_bytes=8_000)
assert len(html_chico.encode()) < 12_000 and "nuevos más" in html_chico, len(html_chico)
assert informe.png_icono("s_regiones")[:4] == b"\x89PNG"

# Perfiles: perfiles.ini de prueba en una carpeta temporal.
import os, tempfile
from pathlib import Path


def con_ini(texto):
    carpeta = Path(tempfile.mkdtemp())
    (carpeta / "perfiles.ini").write_text(texto, "utf-8")
    bot.DIR = carpeta
    return bot.cargar_perfiles


def debe_fallar(texto, contiene):
    try:
        con_ini(texto)()
    except ValueError as e:
        assert contiene in str(e), (contiene, str(e))
    else:
        raise AssertionError(f"no falló: {texto!r}")


carga = con_ini('[ana]\ncorreos = a@x.com, b@y.org\npalabras_clave = software,"sistema académico",cemento\n'
                'regiones = CUSCO,APURIMAC/ABANCAY\nuniq = no\ncompleto = NO\n\n[luis]\ncorreos = l@x.com\nentidades = LA CONVENCION\n')
perfiles = carga()
ana, luis = perfiles
assert [p["nombre"] for p in perfiles] == ["ana", "luis"]
assert ana["correos"] == ["a@x.com", "b@y.org"] and ana["palabras"] == ["software", '"sistema académico"', "cemento"]
assert ana["uniq"] is False and ana["completo"] is False and luis["uniq"] is True and luis["completo"] is True
assert ana["regiones"] == ["CUSCO", "APURIMAC/ABANCAY"] and luis["palabras"] == [] and luis["entidades"] == ["LA CONVENCION"]
debe_fallar("[x]\npalabras_clave = software\n", "falta 'correos'")
debe_fallar("[x]\ncorreos = no-es-correo\n", "correo no válido")
debe_fallar("[x]\ncorreos = a@x.com\npalabra_clave = software\n", "clave desconocida 'palabra_clave'")
debe_fallar("[x]\ncorreos = a@x.com\nuniq = no\n", "no sigue nada")
debe_fallar("[x]\ncorreos = a@x.com\nuniq = si\n[x]\ncorreos = b@x.com\n", "x")  # sección duplicada
debe_fallar("# vacío\n", "ningún perfil")

# Sin perfiles.ini: un perfil con lo que diga el .env.
bot.DIR = Path(tempfile.mkdtemp())
os.environ.update(MAIL_TO="m@x.com", PALABRAS_CLAVE="cemento", ENTIDADES="", REGIONES="CUSCO")
solo, = bot.cargar_perfiles()
assert solo["legacy"] and solo["correos"] == ["m@x.com"] and solo["palabras"] == ["cemento"] and solo["uniq"]

# Lo NUEVO es propio de cada perfil; el del .env conserva las claves de siempre.
estado = {"vistos": [1], "seace": ["p-1"]}
assert bot.estado_de(estado, solo) is estado
bot.estado_de(estado, ana)["vistos"] = [9]
assert bot.estado_de(estado, luis) == {} and estado["perfiles"]["ana"]["vistos"] == [9] and estado["vistos"] == [1]

# La sesión descarga una sola vez cada URL, y una falla tampoco se reintenta por cada perfil.
llamadas = []


def get_falso(self, url, **kw):
    llamadas.append(url)
    if "cae" in url:
        raise bot.requests.ConnectionError("sin red")
    return "respuesta"


get_real = bot.requests.Session.get
bot.requests.Session.get = get_falso  # la caché se prueba sobre el GET de la clase base
try:
    cs = bot.SesionConCache()
    assert cs.get("https://a", params={"q": 1}) == cs.get("https://a", params={"q": 1}) == "respuesta"
    assert cs.get("https://a", params={"q": 2}) == "respuesta" and llamadas == ["https://a", "https://a"]
    for _ in range(2):
        try:
            cs.get("https://cae")
        except bot.requests.ConnectionError:
            pass
    assert llamadas.count("https://cae") == 1
finally:
    bot.requests.Session.get = get_real

# Ubicación: formato, consulta por ítem, caché (no repite lo visto), poda y fallas sin romper el informe.
assert informe.nombre_lugar("CUSCO/LA CONVENCION/SANTA ANA") == "Cusco › La Convencion › Santa Ana"
assert informe.nombre_lugar("CUSCO/CUSCO/CUSCO | APURIMAC/ABANCAY/ABANCAY") == "Cusco › Cusco › Cusco | Apurimac › Abancay › Abancay"
assert informe.nombre_lugar("") == "" and informe.nombre_lugar(None) == ""


class Resp:
    def __init__(self, datos):
        self.datos = datos

    def raise_for_status(self):
        pass

    def json(self):
        return self.datos


consultas = []


class SesionFalsa:
    def get(self, url, params=None, **kw):
        consultas.append(url)
        if "listar-completo" in url:
            if str(params["id_contrato"]) == "666":
                raise RuntimeError("portal caído")
            return Resp({"uitContratoItemProjectionList": [{"nomDistrito": "CUSCO/LA CONVENCION/SANTA ANA"},
                                                            {"nomDistrito": "CUSCO/LA CONVENCION/SANTA ANA"}]})
        return Resp({"listaItems": [{"departamento": "APURIMAC", "provincia": "ANDAHUAYLAS", "distrito": "SAN JERONIMO"}],
                     "listaCronograma": [{"nombreDepartamento": "APURIMAC", "nombreProvincia": "ABANCAY", "nombreDistrito": "ABANCAY"}]})


def p(id_, fuente="SEACE"):
    return {"id": id_, "fuente": fuente}


cache = {"p-viejo": {"l": "X/Y/Z", "v": "2026-01-01"}, "m-5": {"l": "PUNO/PUNO/PUNO", "v": "2026-09-01"}}
lista = [p("m-1"), p("p-2"), p("m-5"), p("m-666"), p("u-9", "UNIQ")]
seace.completar_lugares(SesionFalsa(), lista, cache, ahora)
assert lista[0]["lugar"] == "CUSCO/LA CONVENCION/SANTA ANA"            # varios ítems del mismo lugar: uno solo
assert lista[1]["lugar"] == "APURIMAC/ANDAHUAYLAS/SAN JERONIMO"        # procesos: el lugar del ítem, no el de la entidad
assert lista[2]["lugar"] == "PUNO/PUNO/PUNO" and cache["m-5"]["v"] == "2026-09-28"  # desde la caché, sin consultar
assert lista[3]["lugar"] == "" and "m-666" not in cache                 # falla: sin lugar y sin guardarlo
assert "lugar" not in lista[4] and "p-viejo" not in cache and len(consultas) == 3  # UNIQ no se toca; poda >45 días
consultas.clear()
seace.completar_lugares(SesionFalsa(), [p("m-1"), p("p-2")], cache, ahora)
assert consultas == [] and set(cache) == {"m-1", "p-2", "m-5"}

# Índice por búsqueda y aviso de correo largo.
casos = [("cemento", [dict(procesos[0], nuevo=True), dict(procesos[0], id="p-2", nuevo=False)]), ("fierro", [])]
indice = informe.html_indice([("Palabras clave", casos), ("Entidades", [])])
assert "Resultados por búsqueda" in indice and ">cemento<" in indice and ">fierro<" in indice and "ENTIDADES" not in indice
assert informe.html_indice([("Palabras clave", [])]) == ""

# Enlaces de cada fila: bases y buscador de SEACE 3.0 solo en procedimientos (no en contrataciones menores).
enlaces = informe.enlace_bases(procesos[0])
assert "Descargar bases" in enlaces and "Buscar SIE-SIE-1-2026-X-1 en SEACE 3.0" in enlaces and "prod2.seace" in enlaces
assert "SEACE 3.0" not in informe.enlace_bases(dict(procesos[0], id="m-5")) and informe.enlace_bases(dict(procesos[0], id="m-5", bases=None)) == ""

# El correo largo lleva el informe entero como adjunto; el corto, no.
enviados = []


class SMTPFalso:
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def starttls(self): pass
    def login(self, u, c): pass
    def send_message(self, m): enviados.append(m)


bot.smtplib.SMTP = SMTPFalso
os.environ.update(SMTP_USER="u@gmail.com", SMTP_PASS="a b")
bot.enviar("asunto", "texto", '<p>hola <img src="cid:ico-pin"></p>', ["a@x.com"])
bot.enviar("asunto", "texto", '<p>hola <img src="cid:ico-pin"></p>', ["a@x.com"], "<html>entero</html>", "informe-2026-09-28.html")
corto, largo = enviados
assert [x.get_filename() for x in corto.iter_attachments()] == []
assert [x.get_filename() for x in largo.iter_attachments()] == ["informe-2026-09-28.html"]
assert largo.get_body(("html",)).get_content().startswith("<p>hola")  # el cuerpo sigue siendo el HTML con iconos

# Informe sin UNIQ ni palabras clave (alguien que solo sigue una entidad): sin secciones vacías.
proceso = {"id": "p-1", "fuente": "SEACE", "tipo": "Licitación Pública", "titulo": "ADQUISICION DE CEMENTO", "entidad": "MUNICIPALIDAD DISTRITAL DE ECHARATI",
           "codigo": "LP-1", "url": "https://x/1", "bases": None, "cierre": datetime(2026, 10, 5, 23, 59, tzinfo=uniq.LIMA),
           "abierta": True, "inicio": None, "convocatoria": None, "monto": 0, "nuevo": True, "pie_cierre": "fin de registro"}
asunto, texto, html = informe.construir_informe(ahora, [], [], [], [("SEACE · Entidades que sigues", True, "1", "x")],
                                                [("MUNICIPALIDAD DISTRITAL DE ECHARATI", [proceso])], [], True, False)
assert "1 proceso nuevo" in asunto and "UNIQ" not in asunto, asunto
assert "Cotizaciones UNIQ" not in html and "Coincidencias por palabra clave" not in html and "Palabras clave" not in html
assert "Entidades que sigues" in html and "UNIQ" not in texto and "COINCIDENCIAS" not in texto
print("OK")
