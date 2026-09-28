"""Autoprueba sin red: lector de TDR/EETT, formato de textos y búsqueda por frase. Uso: python test_bot.py"""
import pymupdf

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
print("OK")
