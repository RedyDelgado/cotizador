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
assert ana["uniq"] is False and ana["completo"] is False and luis["uniq"] is False and luis["completo"] is True  # sin pedirla, no hay UNIQ

# La UNIQ es una entidad más: "UNIQ" en entidades la activa (y se busca en SEACE con su nombre completo);
# la clave antigua uniq = si sigue funcionando; sin ninguna de las dos, no se recibe.
c, d, e = con_ini('[a]\ncorreos = a@x.com\nentidades = LA CONVENCION, uniq\n'
                  '[b]\ncorreos = b@x.com\nentidades = Universidad Nacional Intercultural de Quillabamba,UNIQ\n'
                  '[c]\ncorreos = c@x.com\nuniq = si\n')()
assert c["uniq"] and c["entidades"] == ["LA CONVENCION", uniq.NOMBRE]
assert d["uniq"] and d["entidades"] == [uniq.NOMBRE]            # los dos nombres no se duplican
assert e["uniq"] and e["entidades"] == []                        # clave antigua
assert not con_ini('[x]\ncorreos = x@x.com\nentidades = LA CONVENCION\n')()[0]["uniq"]
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
        if "listar-archivos-contrato" in url:
            return Resp([{"idContratoArchivo": 7}])
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
assert lista[3]["lugar"] == "" and "l" not in cache["m-666"]          # falla: sin lugar y sin guardarlo (se reintenta mañana)
assert lista[0]["bases"].endswith("/7") and lista[2]["bases"].endswith("/7") and "bases" not in lista[1]  # requerimiento solo en menores
assert "lugar" not in lista[4] and "p-viejo" not in cache and len(consultas) == 6  # UNIQ no se toca; poda >45 días
consultas.clear()
seace.completar_lugares(SesionFalsa(), [p("m-1"), p("p-2")], cache, ahora)
assert consultas == [] and set(cache) == {"m-1", "p-2", "m-5", "m-666"}

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

# Palabras clave SOLO en las regiones del perfil: se filtran sobre lo abierto en esas regiones.
def abierto(id_, titulo, entidad="E", tipo="Licitación Pública", texto=None):
    return {"id": id_, "fuente": "SEACE", "tipo": tipo, "titulo": titulo, "entidad": entidad, "codigo": id_, "url": "u",
            "bases": None, "cierre": datetime(2026, 10, 9, 23, 59, tzinfo=uniq.LIMA), "abierta": True, "inicio": None,
            "convocatoria": None, "monto": 0, "nuevo": True, **({"texto": texto} if texto else {})}


candidatos = {x["id"]: x for x in (
    abierto("p-1", "ADQUISICION DE CEMENTO PORTLAND", texto="ADQUISICION DE CEMENTO PORTLAND TIPO I"),
    abierto("p-2", "SUMINISTRO DE COMBUSTIBLE", texto="SUMINISTRO DE COMBUSTIBLE | ademas CEMENTO ASFALTICO"),  # el ítem lo menciona
    abierto("m-3", "COMPRA DE FIERRO CORRUGADO", tipo="Contratación menor"),                                  # menor: sin "texto"
    abierto("p-4", "SERVICIO DE LIMPIEZA"))}
fuentes_t = []
g, ids = bot.coincidencias_en_regiones(["cemento", "fierro", '"sistema académico"'], [], candidatos, fuentes_t)
assert [(f, sorted(x["id"] for x in it)) for f, it in g] == [("cemento", ["p-1", "p-2"]), ("fierro", ["m-3"]), ('"sistema académico"', [])]
assert ids == {"p-1", "p-2", "m-3"} and fuentes_t[0][1] is True
g2, _ = bot.coincidencias_en_regiones(["cemento", "cemento portland"], [], candidatos, [])
assert [x["id"] for x in g2[1][1]] == []  # un proceso que calza con dos frases sale solo en la primera
g3, _ = bot.coincidencias_en_regiones(["cemento"], [], {}, [])  # sin candidatos: nada, y no se busca en todo el país
assert g3 == [("cemento", [])]

# Marca: el logo existe, el encabezado lo usa, viaja incrustado en el correo y el informe sale igual sin él.
logo = informe.logo_png()
assert logo and logo[:4] == b"\x89PNG" and len(logo) < 80_000, "assets/logo.png"
encabezado_html = informe.marca("Informe", ahora)
assert 'src="cid:logo"' in encabezado_html and 'alt="NEOESTADO"' in encabezado_html
assert "data:image/png;base64," in informe.con_data_uri(encabezado_html) and "cid:logo" not in informe.con_data_uri(encabezado_html)
enviados.clear()
bot.enviar("a", "t", encabezado_html, ["a@x.com"])
assert "logo.png" not in str(enviados[0]) and any(p.get("Content-ID") == "<logo>" for p in enviados[0].walk())
logo_real, informe.logo_png = informe.logo_png, lambda: None  # sin archivo de logo
assert "cid:logo" not in informe.marca("Informe", ahora) and "MONITOR DE CONTRATACIONES" in informe.marca("Informe", ahora)
informe.logo_png = logo_real

# Informe sin UNIQ ni palabras clave (alguien que solo sigue una entidad): sin secciones vacías.
proceso = {"id": "p-1", "fuente": "SEACE", "tipo": "Licitación Pública", "titulo": "ADQUISICION DE CEMENTO", "entidad": "MUNICIPALIDAD DISTRITAL DE ECHARATI",
           "codigo": "LP-1", "url": "https://x/1", "bases": None, "cierre": datetime(2026, 10, 5, 23, 59, tzinfo=uniq.LIMA),
           "abierta": True, "inicio": None, "convocatoria": None, "monto": 0, "nuevo": True, "pie_cierre": "fin de registro"}
asunto, texto, html = informe.construir_informe(ahora, [], [], [], [("SEACE · Entidades que sigues", True, "1", "x")],
                                                [("MUNICIPALIDAD DISTRITAL DE ECHARATI", [proceso])], [], True, False)
assert "1 proceso nuevo" in asunto and "UNIQ" not in asunto, asunto
assert "Cotizaciones UNIQ" not in html and "Coincidencias por palabra clave" not in html and "Palabras clave" not in html
assert "Entidades que sigues" in html and "UNIQ" not in texto and "COINCIDENCIAS" not in texto

# Empleos: SERVIR (HTML de la página), Empleos Perú (JSON), filtros por lugar / palabra / sueldo y el informe.
import empleos


def bloque_servir(titulo, entidad, lugar, nro, vac, sueldo, ini, fin):
    campo = '<div class="row"><span class="sub-titulo">{}:</span>&nbsp; <span class="detalle-sp">{}\n\t</span></div>'
    return ('<div class="col-sm-12 titulo-vacante"><label>' + titulo + '</label></div><span class="detalle-sp"><b>' + entidad + '</b></span>'
            + campo.format("Ubicación", lugar) + campo.format("Número de Convocatoria", nro) + campo.format("Cantidad de Vacantes", vac)
            + campo.format("Remuneración", sueldo) + campo.format("Fecha Inicio de\n\t\tPublicación", ini) + campo.format("Fecha Fin de Publicación", fin))


pagina = ('<label class="control-label btn-paginator-cnt">Página 1 de 19</label>'
          + bloque_servir("INGENIERO CIVIL IV", "MUNICIPALIDAD DISTRITAL DE ECHARATI", "CUSCO - ECHARATI", "276-6", "2", " S/. 4,500.00 ", "21/10/2026 ", "03/11/2026 ")
          + bloque_servir("ASISTENTE ADMINISTRATIVO", "UGEL LA CONVENCION", "APURIMAC - ABANCAY", "12-1", "1", "A convenir", "20/10/2026", "30/10/2026")
          + '<button id="frmLstOfertsLabo:j_idt62" class="x btn-paginator"><span>Sig.</span></button>')
servir_ofertas = empleos.ofertas_de_pagina(pagina)
assert [o["titulo"] for o in servir_ofertas] == ["INGENIERO CIVIL IV", "ASISTENTE ADMINISTRATIVO"]
civil, asistente = servir_ofertas
assert civil["lugar"] == "CUSCO/ECHARATI" and civil["sueldo_min"] == 4500 and civil["sueldo"] == "S/ 4,500" and civil["vacantes"] == "2"
assert civil["publicado"] == "2026-10-21" and civil["cierre"].day == 3 and civil["cierre"].tzinfo is not None and civil["id"].startswith("s-")
assert asistente["sueldo_max"] is None and asistente["sueldo"] == "" and civil["id"] != asistente["id"]
assert empleos._paginas(pagina) == (1, 19) and empleos._boton_siguiente(pagina) == "frmLstOfertsLabo:j_idt62"
assert empleos.numero("S/. 3,651.00") == 3651 and empleos.numero("A convenir") is None

lugares = {"08": "CUSCO", "0801": "CUSCO", "080101": "CUSCO", "0807": "LA CONVENCION", "080701": "SANTA ANA", "03": "APURIMAC",
           "0301": "ABANCAY", "030101": "ABANCAY", "080709": "ECHARATI"}
lugares["0807"] = "LA CONVENCION"
fila_mtpe = {"id": "abc", "positionTitle": "Conductor de Retroexcavadora", "location": {"DEPARTMENT": "08", "PROVINCE": "0807", "DISTRICT": "080701"},
             "companyName": "RIHOUSE S.A.C", "displaySalary": True, "datePosted": "2026-10-21", "contractType": {"name": "Plazo fijo"},
             "hoursPerWeek": {"name": "Tiempo completo"}, "educationDegree": {"name": "Secundaria completa"},
             "offeredRemunerationPackages": [{"minimumAmount": 1400, "maximumAmount": 1599, "type": "1400-1599"}]}
mtpe_oferta = empleos.oferta_mtpe(fila_mtpe, lugares)
assert mtpe_oferta["lugar"] == "CUSCO/LA CONVENCION/SANTA ANA" and mtpe_oferta["sueldo"] == "S/ 1,400 – S/ 1,599" and mtpe_oferta["sueldo_max"] == 1599
assert mtpe_oferta["url"].endswith("jobId=abc") and "Plazo fijo" in mtpe_oferta["detalle"]
assert empleos.sueldo_mtpe({"displaySalary": False, "offeredRemunerationPackages": [{"type": "A"}]}) == (None, None, "")
assert empleos.sueldo_mtpe({"offeredRemunerationPackages": [{"minimumAmount": 0, "maximumAmount": 1230, "type": "<=1230"}]})[2] == "Hasta S/ 1,230"
assert empleos.sueldo_mtpe({"offeredRemunerationPackages": [{"minimumAmount": 10000, "type": ">=10000"}]})[1] == float("inf")
provincia_de = empleos.provincias_de_distritos(lugares)
assert provincia_de[("CUSCO", "ECHARATI")] == "LA CONVENCION" and provincia_de[("APURIMAC", "ABANCAY")] == "ABANCAY"

todas = [civil, asistente, mtpe_oferta]
# región: CUSCO trae a todos los de Cusco; con provincia, SERVIR se resuelve por su distrito
assert [o["titulo"] for _, i in empleos.agrupar(todas, [], ["CUSCO"], set(), None, provincia_de) for o in i] == \
    ["INGENIERO CIVIL IV", "Conductor de Retroexcavadora"]
assert [o["titulo"] for _, i in empleos.agrupar(todas, [], ["CUSCO/LA CONVENCION"], set(), None, provincia_de) for o in i] == \
    ["INGENIERO CIVIL IV", "Conductor de Retroexcavadora"]
assert [o["titulo"] for _, i in empleos.agrupar(todas, [], ["APURIMAC/ABANCAY"], set(), None, provincia_de) for o in i] == ["ASISTENTE ADMINISTRATIVO"]
# sueldo mínimo: filtra lo que paga menos; lo que no dice sueldo se deja ver
assert [o["titulo"] for _, i in empleos.agrupar(todas, [], [], set(), 3000, provincia_de) for o in i] == ["INGENIERO CIVIL IV", "ASISTENTE ADMINISTRATIVO"]
# palabras clave sobre el título; una oferta sale solo en la primera; lo ya visto no es nuevo
g = empleos.agrupar(todas, ["ingeniero", "civil", '"asistente administrativo"'], [], {civil["id"]}, None, provincia_de)
assert [(n, [o["titulo"] for o in i]) for n, i in g] == [("ingeniero", ["INGENIERO CIVIL IV"]), ("civil", []), ('"asistente administrativo"', ["ASISTENTE ADMINISTRATIVO"])]
assert g[0][1][0]["nuevo"] is False and g[2][1][0]["nuevo"] is True
assert [n for n, _ in empleos.agrupar(todas, [], ["CUSCO", "APURIMAC"], set(), None, provincia_de)] == ["CUSCO", "APURIMAC"]

# perfiles.ini con empleos
(Path(tempfile.mkdtemp()) / "x").parent
per = con_ini("[a]\ncorreos = a@x.com\nempleo_palabras = ingeniero,\"asistente administrativo\"\nempleo_regiones = CUSCO\nempleo_sueldo_min = 3,500\n")()[0]
assert per["empleos"] and per["empleo_palabras"] == ["ingeniero", '"asistente administrativo"'] and per["empleo_sueldo"] == 3500
assert not con_ini("[a]\ncorreos = a@x.com\nregiones = CUSCO\n")()[0]["empleos"]
debe_fallar("[a]\ncorreos = a@x.com\nempleo_sueldo_min = mucho\n", "empleo_sueldo_min")
debe_fallar("[a]\ncorreos = a@x.com\nuniq = no\n", "no sigue nada")

# informe: la sección sale solo si el perfil pide empleos, el asunto y los indicadores cuentan las ofertas
grupos_empleo = [(informe.mostrar("ingeniero"), [dict(civil, nuevo=True)]), (informe.mostrar("abogado"), [])]
asunto, texto, html = informe.construir_informe(ahora, [], [], [], [("Empleos Perú (MTPE)", True, "1648 ofertas", "x")], [], [], True, False,
                                                grupos_empleo, informe.nota_empleos(per))
assert "1 oferta de empleo (1 nuevas)" in asunto and "procesos nuevos" not in asunto, asunto
assert "Ofertas de empleo" in html and "S/ 4,500" in html and "Ingeniero civil IV" in html and "Echarati" in html
assert "OFERTAS DE EMPLEO" in texto and "https://app.servir.gob.pe" in texto and "Sin ofertas que coincidan" in html
assert "Ofertas de empleo" not in informe.construir_informe(ahora, [], [], [], [("x", True, "", "")], [], [], True, False)[2]

# Maestras del SEACE: un JSON de error (HTTP 403 disfrazado) se avisa claro y se usa la última lista buena.
class RespuestaFalsa:
    def __init__(self, codigo, cuerpo):
        self.status_code, self._cuerpo, self.text = codigo, cuerpo, str(cuerpo)

    def json(self):
        return self._cuerpo


class SesionFalsa:
    def __init__(self, respuesta):
        self.respuesta = respuesta

    def get(self, url, timeout=0):
        return self.respuesta


guardadas = {}
assert seace.maestra(SesionFalsa(RespuestaFalsa(200, [{"nom": "CUSCO"}])), "u", guardadas, "dep") == [{"nom": "CUSCO"}]
assert seace.maestra(SesionFalsa(RespuestaFalsa(200, {"code": "403"})), "u", guardadas, "dep") == [{"nom": "CUSCO"}]
try:
    seace.maestra(SesionFalsa(RespuestaFalsa(200, {"code": "403", "message": "Forbidden"})), "u", {}, "dep")
    raise AssertionError("debía fallar")
except RuntimeError as e:
    assert "Forbidden" in str(e)

# Requerimiento de una contratación menor: enlace directo al archivo, guardado en el caché (una consulta por proceso).
class SesionMenor:
    def __init__(self):
        self.llamadas = []

    def get(self, url, params=None, timeout=0):
        self.llamadas.append(url)
        cuerpo = ([{"idContratoArchivo": 416522, "nombre": "EETT.pdf"}] if "listar-archivos-contrato" in url
                  else {"uitContratoItemProjectionList": [{"nomDistrito": "SANTA ANA"}]})
        return type("R", (), {"raise_for_status": lambda self: None, "json": lambda self: cuerpo})()


menor = {"id": "m-104131", "fuente": "SEACE"}
sesion_menor, cache_menor = SesionMenor(), {"m-104131": {"l": "CUSCO/LA CONVENCION/SANTA ANA", "v": "2026-10-20"}}  # entrada anterior, sin "r"
seace.completar_lugares(sesion_menor, [menor], cache_menor, ahora)
assert menor["bases"] == seace.URL_REQUERIMIENTO.format("416522") and menor["bases_etiqueta"] == "Descargar requerimiento"
assert menor["lugar"] == "CUSCO/LA CONVENCION/SANTA ANA" and cache_menor["m-104131"]["r"] == "416522" and len(sesion_menor.llamadas) == 1  # solo pidió el archivo
seace.completar_lugares(sesion_menor, [dict(menor)], cache_menor, ahora)
assert len(sesion_menor.llamadas) == 1                          # ya guardado: no vuelve a consultar
assert "Descargar requerimiento" in informe.enlace_bases(menor) and "Descargar bases" not in informe.enlace_bases(menor)

# Panel de suscriptores (admin.py): crea, edita, pausa, renombra, elimina y restaura sobre un perfiles.ini temporal.
import json
import admin
seace.resolver_zonas = lambda s, textos, maestras=None: []                     # sin red: las regiones se dan por buenas
carpeta = Path(tempfile.mkdtemp())
bot.DIR, bot.ESTADO = carpeta, carpeta / "data" / "estado.json"
admin.INI, admin.RESPALDOS = carpeta / "perfiles.ini", carpeta / "respaldos"
assert admin.leer() == ([], None)                               # sin archivo: lista vacía, no error
nuevo = {"nombre": "Ana", "nota": "Cliente", "correos": ["ana@x.com", "ana@x.com", "b@x.com"], "palabras": ['"sistema académico"', "cemento, fierro"],
         "regiones": ["CUSCO", "APURIMAC/ABANCAY"], "entidades": ["UGEL LA CONVENCION", "UNIQ"], "uniq": True, "completo": False}
assert admin.guardar(None, nuevo) is None                       # primer guardado: no había nada que respaldar
ana, = admin.leer()[0]
assert ana["correos"] == ["ana@x.com", "b@x.com"] and ana["palabras"] == ['"sistema académico"', "cemento fierro"], ana
assert ana["entidades"] == ["UGEL LA CONVENCION"] and ana["uniq"] and not ana["completo"] and not ana["pausado"]
assert "entidades = UNIQ,UGEL LA CONVENCION" in admin.INI.read_text("utf-8")
assert [p["nombre"] for p in bot.cargar_perfiles()] == ["Ana"]  # el bot lee lo que escribió el panel
for malo, motivo in [({**nuevo, "nombre": "Ana"}, "Ya existe"), ({**nuevo, "nombre": "X]"}, "corchetes"), ({**nuevo, "nombre": "Luz", "correos": ["sin-arroba"]}, "correo no válido"),
                     ({**nuevo, "nombre": "Luz", "correos": []}, "falta 'correos'"), ({**nuevo, "nombre": "Luz", "palabras": [], "regiones": [], "entidades": [], "uniq": False}, "no sigue nada")]:
    try:
        admin.guardar(None, malo)
        raise AssertionError(f"debía fallar: {motivo}")
    except ValueError as e:
        assert motivo in str(e), (motivo, e)
assert len(admin.leer()[0]) == 1                                # los rechazados no tocaron el archivo
r = admin.cambiar("Ana", pausado=True)                          # pausar deja respaldo y no cambia lo demás
assert admin.leer()[0][0]["pausado"] and (admin.RESPALDOS / r).exists()
admin.restaurar(r)                                              # deshacer
assert not admin.leer()[0][0]["pausado"]
bot.guardar_estado({"perfiles": {"Ana": {"vistos": [1], "enviado": "2026-10-21T07:00"}}}, datetime(2026, 10, 21, tzinfo=uniq.LIMA))
admin.guardar("Ana", {**nuevo, "nombre": "Ana María", "regiones": ["CUSCO"]})
assert bot.cargar_estado()["perfiles"] == {"Ana María": {"vistos": [1], "enviado": "2026-10-21T07:00"}}  # el historial la sigue
assert admin.leer()[0][0]["enviado"] == "2026-10-21T07:00"
admin.guardar(None, {**nuevo, "nombre": "Luis", "correos": ["l@x.com"], "empleo_palabras": ["abogado", "contador, público"],
                     "empleo_regiones": ["CUSCO"], "empleo_sueldo": 3000})
luis = [p for p in admin.leer()[0] if p["nombre"] == "Luis"][0]
assert luis["empleo_palabras"] == ["abogado", "contador público"] and luis["empleo_regiones"] == ["CUSCO"] and luis["empleo_sueldo"] == 3000
assert "empleo_sueldo_min = 3000" in admin.INI.read_text("utf-8")
try:
    admin.eliminar("Nadie")
    raise AssertionError("debía fallar")
except ValueError:
    pass
r = admin.eliminar("Luis")
assert [p["nombre"] for p in admin.leer()[0]] == ["Ana María"]
admin.restaurar(r)
assert [p["nombre"] for p in admin.leer()[0]] == ["Ana María", "Luis"]
try:
    admin.eliminar("Luis"); admin.eliminar("Ana María")
    raise AssertionError("no debe dejar el archivo vacío")
except ValueError:
    pass
for nombre in ("../x.ini", "perfiles-1.ini"):                   # solo se restauran respaldos propios
    try:
        admin.restaurar(nombre)
        raise AssertionError(nombre)
    except ValueError:
        pass
admin.INI.write_text("[roto\n", "utf-8")                        # un archivo roto se informa; el panel no se cae
assert admin.leer()[0] == [] and "perfiles.ini" in admin.leer()[1]
assert admin.lista_respaldos() and admin.lista_respaldos()[0]["perfiles"]
print("OK")
