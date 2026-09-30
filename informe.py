"""Diseño del informe diario: HTML para correo y su versión en texto plano.

Formato de informe profesional: encabezado institucional, resumen ejecutivo con indicadores,
tablas de datos con cabecera, etiquetas de estado y fichas técnicas. Paleta de Tailwind CSS
(navy/blue para el acento, gray para neutros), iconos Lucide (los mismos de lucide-react) y
nada de emojis. Todo va en línea: Gmail descarta <style>, clases y SVG, por eso los iconos
viajan como PNG adjuntos.
"""
import base64
import functools
import html
import re
import pymupdf

import seace
import uniq

DIAS_ALERTA = 2   # "cierra pronto" si quedan 2 días o menos
MAX_ITEMS = 15    # ítems del TDR por ficha
MAX_FILAS = 15    # filas por palabra clave o entidad
# Gmail recorta el HTML arriba de ~102 KB y lo que queda abajo solo se ve con "Ver mensaje completo".
LIMITE_HTML = 95_000   # margen para el envoltorio del correo
CUPO_COMPLETAS = 15    # filas completas (lo nuevo) entre TODAS las palabras clave
CUPO_BREVES = 20       # recordatorios de una línea entre todas las palabras clave
MUY_GENERAL = 60       # desde cuántos resultados se sugiere afinar una palabra clave

FUENTE = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
# Contraste WCAG sobre blanco: texto 17:1, cuerpo 10:1, suave 4.8:1, enlace 8.6:1, rojo 6.5:1.
C = {
    "navy": "#0B2545",        # títulos y barra superior
    "azul": "#1D4ED8",        # blue-700: botones, iconos de ficha
    "enlace": "#1E40AF",      # blue-800: enlaces y etiquetas
    "azul_tinta": "#EFF6FF",  # blue-50
    "azul_borde": "#BFDBFE",  # blue-200
    "texto": "#111827",       # gray-900
    "cuerpo": "#374151",      # gray-700
    "suave": "#6B7280",       # gray-500
    "linea": "#E5E7EB",       # gray-200
    "cabecera": "#F9FAFB",    # gray-50: cabeceras de tabla
    "fondo": "#F3F4F6",       # gray-100: fondo del correo
    "rojo": "#B91C1C",        # red-700: solo lo que cierra en <= 2 días y las fallas
    "rojo_tinta": "#FEF2F2",
    "rojo_borde": "#FECACA",
}
BLANCO = "#FFFFFF"

# Iconos Lucide (licencia ISC, https://lucide.dev): contenido del <svg> de 24x24.
GLIFOS = {
    "chart-column": '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "landmark": '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    "file-text": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>',
    "map-pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "building-2": '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
    "external-link": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3"/>',
    "triangle-alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "package": '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    "list-checks": '<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/>',
    "truck": '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>',
    "credit-card": '<rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/>',
    "banknote": '<rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>',
    "shield-check": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "scale": '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
    "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
}
# nombre de uso: (glifo, color)
ICONOS = {
    "s_resumen": ("chart-column", C["navy"]),
    "s_coinc": ("search", C["navy"]),
    "s_entidades": ("building-2", C["navy"]),
    "s_regiones": ("map-pin", C["navy"]),
    "s_uniq": ("landmark", C["navy"]),
    "s_fichas": ("file-text", C["navy"]),
    "s_fuentes": ("database", C["navy"]),
    "aviso": ("triangle-alert", C["rojo"]),
    "abrir": ("external-link", BLANCO),
    "pdf": ("file-text", BLANCO),
    "objetivo": ("target", C["azul"]),
    "items": ("package", C["azul"]),
    "requisitos": ("list-checks", C["azul"]),
    "plazo": ("truck", C["azul"]),
    "pago": ("credit-card", C["azul"]),
    "adelanto": ("banknote", C["azul"]),
    "garantia": ("shield-check", C["azul"]),
    "penalidad": ("scale", C["azul"]),
    "tecnico": ("layers", C["azul"]),
    "error_pdf": ("triangle-alert", C["rojo"]),
}


@functools.lru_cache(maxsize=None)
def png_icono(nombre):
    """PNG a 3x (nítido en pantallas retina) del icono Lucide, fondo transparente."""
    glifo, color = ICONOS[nombre]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{GLIFOS[glifo]}</svg>')
    with pymupdf.open(stream=svg.encode(), filetype="svg") as doc:
        return doc[0].get_pixmap(matrix=pymupdf.Matrix(3, 3), alpha=True).tobytes("png")


def img(nombre, px, estilo="display:block"):
    # alt vacío: son decorativos, el texto de al lado ya dice lo mismo (lectores de pantalla los saltan).
    return f'<img src="cid:ico-{nombre}" width="{px}" height="{px}" alt="" style="{estilo};border:0">'


def con_data_uri(cuerpo_html):
    """Para preview.html: el navegador no entiende cid:, se incrustan los PNG en base64."""
    return re.sub(r"cid:ico-([\w-]+)", lambda m: "data:image/png;base64," +
                  base64.b64encode(png_icono(m.group(1))).decode(), cuerpo_html)


# -------------------------------------------------------------------- texto

# Siglas que se conservan al pasar a minúsculas un texto que viene TODO EN MAYÚSCULAS.
# ponytail: una sigla que no esté aquí queda en minúscula; se agrega a la lista y listo.
SIGLAS = {"UNIQ", "TDR", "EETT", "RNP", "RUC", "CCI", "UEI", "UIT", "DIGEMID", "OSINERGMIN", "SUNAT",
          "MINEM", "SAC", "EIRL", "PVC", "LED", "UV", "UI", "GPS", "CPU", "PC", "TI", "TIC", "CUI",
          "I", "II", "III", "IV"}
MENORES_NOMBRE = {"de", "del", "la", "las", "los", "el", "y", "e", "en", "para", "por", "con", "a", "al"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def h(valor):
    return html.escape(str(valor))


def recortar(texto, n):
    return uniq.recortar(texto, n)


def en_mayusculas(texto):
    letras = [ch for ch in texto if ch.isalpha()]
    return bool(letras) and sum(ch.isupper() for ch in letras) >= 0.8 * len(letras)


def oracion(texto):
    """"ADQUISICIÓN DE GASOHOL - UNIQ" -> "Adquisición de gasohol - UNIQ". Deja igual lo que ya
    viene en minúsculas; conserva siglas conocidas y palabras con números ("S10", "01-A")."""
    if not en_mayusculas(texto):
        return texto
    palabras = [p if p.strip(".,;:()\"'“”-–") in SIGLAS or any(ch.isdigit() for ch in p) else p.lower()
                for p in texto.split(" ")]
    s = " ".join(palabras)
    i = next((k for k, ch in enumerate(s) if ch.isalpha()), 0)
    return s[:i] + s[i:i + 1].upper() + s[i + 1:]


def nombre_propio(texto):
    """Nombres de entidades en MAYÚSCULAS -> "Municipalidad Provincial de La Convención".
    Conserva siglas conocidas y las que no tienen vocales ("MTC", "DRTC")."""
    if not en_mayusculas(texto):
        return texto

    def parte(p, primera):
        base = p.strip(".,;:()\"'“”")
        if base in SIGLAS or (len(base) > 1 and base.isalpha() and not any(v in base for v in "AEIOUÁÉÍÓÚ")):
            return p
        return p.lower() if p.lower() in MENORES_NOMBRE and not primera else p.capitalize()

    return " ".join("-".join(parte(q, i == 0 and j == 0) for j, q in enumerate(p.split("-")))
                    for i, p in enumerate(texto.split()))


def fecha_larga(d):
    return f"{DIAS_SEMANA[d.weekday()].capitalize()} {d.day} de {MESES[d.month - 1]} de {d.year}"


def dia_mes(d):
    return f"{d.day} {MESES[d.month - 1][:3]}"


def fecha_corta(d):
    return f"{dia_mes(d)} · {d:%H:%M}"


def dias_hasta(d, ahora):
    return (d.date() - ahora.date()).days


def cuando(d, ahora):
    """"Hoy 23:00", "Mañana 16:00" o "30 sep"."""
    dias = dias_hasta(d, ahora)
    return f"Hoy {d:%H:%M}" if dias == 0 else f"Mañana {d:%H:%M}" if dias == 1 else dia_mes(d)


def vence(dias):
    return "vence hoy" if dias == 0 else "vence mañana" if dias == 1 else f"quedan {dias} días"


def plural(n, uno, varios):
    return f"{n} {uno if n == 1 else varios}"


def mostrar(frase):
    """software -> «software»; "sistema académico" (frase exacta) -> “sistema académico”."""
    return f"“{frase[1:-1]}”" if seace.es_exacta(frase) else f"«{frase}»"


# -------------------------------------------------------------- componentes

def etiqueta(texto, tono="gris"):
    """Etiqueta de estado rectangular (NUEVO, CIERRA HOY, fuente, palabra clave)."""
    color, fondo, borde = {
        "azul": (C["enlace"], C["azul_tinta"], C["azul_borde"]),
        "rojo": (C["rojo"], C["rojo_tinta"], C["rojo_borde"]),
        "gris": (C["cuerpo"], C["fondo"], C["linea"]),
        "contorno": (C["enlace"], BLANCO, C["azul_borde"]),
    }[tono]
    return (f'<span style="display:inline-block;margin:0 4px 4px 0;padding:1px 6px;border:1px solid {borde};'
            f'border-radius:4px;background:{fondo};color:{color};font-size:11px;line-height:16px;font-weight:600;'
            f'letter-spacing:0.02em">{h(texto)}</span>')


def boton(url, texto, icono="abrir"):
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:16px"><tr>'
            f'<td style="background:{C["azul"]};border-radius:6px">'
            f'<a href="{h(url)}" style="display:inline-block;padding:9px 14px;color:{BLANCO};text-decoration:none;'
            f'font-size:13px;line-height:18px;font-weight:600">'
            f'{img(icono, 14, "display:inline-block;vertical-align:-2px;margin-right:6px")}{h(texto)}</a>'
            f'</td></tr></table>')


def seccion(numero, icono, titulo, nota=""):
    """Encabezado numerado de sección, con regla inferior."""
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:36px 0 14px">'
            f'<tr><td style="border-bottom:2px solid {C["navy"]};padding-bottom:8px">'
            f'<div style="font-size:11px;line-height:16px;font-weight:600;letter-spacing:0.08em;color:{C["suave"]}">'
            f'SECCIÓN {numero}</div>'
            f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:2px"><tr>'
            f'<td valign="middle" style="padding-right:8px">{img(icono, 18)}</td>'
            f'<td valign="middle" style="font-size:18px;line-height:24px;font-weight:700;color:{C["navy"]}">{h(titulo)}</td>'
            f'</tr></table></td></tr></table>'
            + (f'<p style="margin:-4px 0 14px;font-size:13px;line-height:19px;color:{C["suave"]}">{h(nota)}</p>'
               if nota else ""))


def tabla(cabeceras, filas):
    """Tabla de datos con borde y cabecera gris. cabeceras = [(texto, alineación)]."""
    th = "".join(f'<th align="{al}" style="padding:8px 12px;background:{C["cabecera"]};border-bottom:1px solid {C["linea"]};'
                 f'font-size:11px;line-height:16px;font-weight:600;letter-spacing:0.06em;color:{C["suave"]};'
                 f'text-transform:uppercase;text-align:{al}">{h(t)}</th>' for t, al in cabeceras)
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {C["linea"]};'
            f'border-radius:8px;border-collapse:separate;border-spacing:0;overflow:hidden;margin:0 0 12px">'
            + (f'<tr>{th}</tr>' if th else "") + f'{filas}</table>')


def fila(i, titulo, url, etiquetas, detalle, fecha, pie_fecha, urgente=False, extra=""):
    """Fila de oportunidad: título (enlace), etiquetas y detalle; a la derecha la fecha."""
    borde = f"border-top:1px solid {C['linea']};" if i else ""
    enlace = (f'<a href="{h(url)}" style="color:{C["texto"]};text-decoration:none">{h(titulo)}</a>' if url else h(titulo))
    color = C["rojo"] if urgente else C["texto"]
    return (f'<tr><td valign="top" style="{borde}padding:12px">'
            f'<div style="font-size:14px;line-height:20px;font-weight:600;color:{C["texto"]}">{enlace}</div>'
            f'<div style="margin-top:6px">{etiquetas}</div>'
            f'<div style="font-size:12px;line-height:18px;color:{C["suave"]}">{h(detalle)}</div>{extra}</td>'
            f'<td valign="top" align="right" style="{borde}padding:12px;white-space:nowrap;text-align:right">'
            f'<div style="font-size:13px;line-height:20px;font-weight:600;color:{color}">{h(fecha)}</div>'
            f'<div style="font-size:11px;line-height:16px;color:{C["suave"]}">{h(pie_fecha)}</div></td></tr>')


def fila_nota(texto, url=None, enlace="", primera=False):
    extra = (f' <a href="{h(url)}" style="color:{C["enlace"]};text-decoration:none;font-weight:600">{h(enlace)}</a>'
             if url else "")
    borde = "" if primera else f"border-top:1px solid {C['linea']};"
    return (f'<tr><td colspan="2" style="{borde}padding:12px;font-size:13px;line-height:19px;'
            f'color:{C["suave"]}">{h(texto)}{extra}</td></tr>')


def subtitulo(texto, detalle, url=None, enlace=""):
    derecha = (f'<a href="{h(url)}" style="color:{C["enlace"]};text-decoration:none;font-weight:600">{h(enlace)}</a>'
               if url else "")
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0 8px"><tr>'
            f'<td style="font-size:15px;line-height:20px;font-weight:700;color:{C["texto"]}">{h(texto)}'
            f'<span style="font-weight:400;color:{C["suave"]}"> · {h(detalle)}</span></td>'
            f'<td align="right" style="font-size:13px;line-height:20px;text-align:right;white-space:nowrap">{derecha}</td>'
            f'</tr></table>')


def envolver(cuerpo, titulo):
    return (f'<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">'
            f'<title>{h(titulo)}</title></head>'
            f'<body style="margin:0;padding:0;background:{C["fondo"]};-webkit-text-size-adjust:100%">'
            f'<div style="background:{C["fondo"]};padding:24px 10px;font-family:{FUENTE};color:{C["texto"]}">'
            f'<div style="max-width:680px;margin:0 auto;background:{BLANCO};border:1px solid {C["linea"]};'
            f'border-radius:8px;overflow:hidden">'
            f'<div style="height:5px;background:{C["navy"]}"></div>'
            f'<div style="padding:26px 24px 28px">{cuerpo}</div></div></div></body></html>')


# ---------------------------------------------------------- partes del informe

def marca(titulo, ahora):
    """Encabezado institucional: nombre del producto, título del documento y fecha de emisión."""
    return (f'<div style="font-size:11px;line-height:16px;font-weight:700;letter-spacing:0.12em;color:{C["azul"]}">'
            f'MONITOR DE CONTRATACIONES PÚBLICAS</div>'
            f'<div style="font-size:24px;line-height:30px;font-weight:700;letter-spacing:-0.3px;color:{C["navy"]};'
            f'margin-top:6px">{h(titulo)}</div>'
            f'<div style="font-size:13px;line-height:19px;color:{C["suave"]};margin-top:4px">'
            f'{h(fecha_larga(ahora))} · Emitido a las {ahora:%H:%M} (hora de Lima)</div>')


def encabezado(ahora, palabras, entidades, zonas=()):
    chips = "".join(etiqueta(mostrar(p) if seace.es_exacta(p) else p, "contorno") for p in palabras) or (
        f'<span style="font-size:13px;color:{C["suave"]}">ninguna (define PALABRAS_CLAVE en .env)</span>')
    filas = [("Palabras clave:", chips)]
    if zonas:
        filas.append(("Regiones:", "".join(etiqueta(nombre_zona(z), "gris") for z in zonas)))
    if entidades:
        filas.append(("Entidades:", "".join(etiqueta(nombre_propio(e), "gris") for e in entidades)))
    celdas = "".join(f'<tr><td valign="top" style="padding:1px 8px 0 0;font-size:12px;line-height:18px;font-weight:600;'
                     f'color:{C["cuerpo"]};white-space:nowrap">{rotulo}</td><td>{valor}</td></tr>' for rotulo, valor in filas)
    return (marca("Informe diario de oportunidades", ahora) +
            f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:16px">{celdas}</table>')


def aviso_fuentes(fuentes):
    caidas = [nombre for nombre, ok, _, _ in fuentes if not ok]
    if not caidas:
        return ""
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;'
            f'background:{C["rojo_tinta"]};border:1px solid {C["rojo_borde"]};border-radius:6px"><tr>'
            f'<td width="30" valign="top" style="padding:12px 0 0 12px">{img("aviso", 16)}</td>'
            f'<td style="padding:11px 12px;font-size:13px;line-height:19px;color:{C["rojo"]}">'
            f'<b>Informe incompleto.</b> No respondió: {h(", ".join(caidas))}. El detalle está en la sección de fuentes.'
            f'</td></tr></table>')


def indicadores(cifras):
    """Fila de indicadores del resumen ejecutivo: [(número, etiqueta, urgente)]."""
    celdas = ""
    for i, (n, texto, urgente) in enumerate(cifras):
        borde = f"border-left:1px solid {C['linea']};" if i else ""
        color = C["rojo"] if urgente and n else C["navy"]
        celdas += (f'<td width="{100 // len(cifras)}%" valign="top" style="{borde}padding:14px 12px">'
                   f'<div style="font-size:26px;line-height:30px;font-weight:700;color:{color}">{n}</div>'
                   f'<div style="font-size:11px;line-height:15px;font-weight:600;letter-spacing:0.04em;color:{C["suave"]};'
                   f'margin-top:4px;text-transform:uppercase">{h(texto)}</div></td>')
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {C["linea"]};'
            f'border-radius:8px;border-collapse:separate;border-spacing:0">'
            f'<tr>{celdas}</tr></table>')


def fecha_proceso(x, ahora):
    """(fecha, texto de abajo, urgente) para la columna derecha de un proceso."""
    if x["cierre"]:
        if not x["abierta"]:
            return dia_mes(x["inicio"]), "abre el registro" if x.get("pie_cierre") else "abre la cotización", False
        return cuando(x["cierre"], ahora), x.get("pie_cierre", "cierre"), dias_hasta(x["cierre"], ahora) <= DIAS_ALERTA
    return dia_mes(x["convocatoria"]), "convocatoria", False


def etiquetas_proceso(x, ahora):
    marcas = etiqueta("NUEVO", "azul") if x["nuevo"] else ""
    if x["cierre"] and x["abierta"] and dias_hasta(x["cierre"], ahora) <= DIAS_ALERTA:
        marcas += etiqueta("CIERRA PRONTO", "rojo")
    return marcas + etiqueta(f'{x["fuente"]} · {x["tipo"]}', "gris")


def detalle_proceso(x):
    return " · ".join(filter(None, [nombre_propio(x["entidad"]), x["codigo"],
                                    f'S/ {x["monto"]:,.0f}' if x["monto"] else ""]))


def enlace_bases(x):
    if not x.get("bases"):
        return ""
    return (f'<div style="margin-top:4px;font-size:12px;line-height:18px"><a href="{h(x["bases"])}" '
            f'style="color:{C["enlace"]};text-decoration:none;font-weight:600">Descargar bases</a></div>')


def repartir(items, ahora):
    """(nuevos, recordatorios, resto). Un proceso queda abierto una o dos semanas: se lista completo el día
    que aparece; después solo se recuerda, en una línea, cuando está por cerrar; el resto se cuenta."""
    nuevos = [x for x in items if x["nuevo"]]
    pronto = [x for x in items if not x["nuevo"] and x["cierre"] and dias_hasta(x["cierre"], ahora) <= DIAS_ALERTA]
    return nuevos, pronto, len(items) - len(nuevos) - len(pronto)


def fila_breve(x, ahora, primera=False):
    """Una línea: título enlazado (con NUEVO si lo es), la entidad debajo y la fecha de cierre."""
    fecha, _, urgente = fecha_proceso(x, ahora)
    borde = "" if primera else f"border-top:1px solid {C['linea']};"
    marca = etiqueta("NUEVO", "azul") if x["nuevo"] else ""
    return (f'<tr><td style="{borde}padding:8px 12px;font-size:13px;line-height:18px">{marca}'
            f'<a href="{h(x["url"])}" style="color:{C["texto"]};text-decoration:none">{h(recortar(oracion(x["titulo"]), 90))}</a>'
            f'<div style="font-size:12px;line-height:16px;color:{C["suave"]}">{h(nombre_propio(x["entidad"]))}</div></td>'
            f'<td align="right" valign="top" style="{borde}padding:8px 12px;white-space:nowrap;text-align:right;font-size:13px;'
            f'line-height:18px;font-weight:600;color:{C["rojo"] if urgente else C["texto"]}">{h(fecha)}</td></tr>')


def rotulo_tabla(texto, primera):
    borde = "" if primera else f"border-top:1px solid {C['linea']};"
    return (f'<tr><td colspan="2" style="{borde}background:{C["cabecera"]};padding:6px 12px;font-size:11px;'
            f'line-height:16px;font-weight:600;letter-spacing:0.06em;color:{C["suave"]}">{h(texto)}</td></tr>')


def html_grupos_completo(grupos, ahora, titulo, vacio, amplia=None):
    """Modo completo: cada proceso abierto en fila completa, todos los días (NUEVO marca lo que aparece
    por primera vez). El correo puede pasar los ~102 KB: Gmail muestra "Ver mensaje completo"."""
    salida = ""
    for nombre, items in grupos:
        filas = "".join(fila(i, recortar(oracion(x["titulo"]), 140), x["url"], etiquetas_proceso(x, ahora),
                             detalle_proceso(x), *fecha_proceso(x, ahora), extra=enlace_bases(x))
                        for i, x in enumerate(items))
        if amplia and len(items) >= amplia:
            filas += fila_nota(f"Esta palabra clave es muy general ({len(items)} resultados): hazla más específica "
                               f"o ponla entre comillas junto a otra palabra.")
        if not items:
            filas = fila_nota(vacio, primera=True)
        salida += subtitulo(titulo(nombre), plural(len(items), "abierto", "abiertos"))
        salida += tabla([("Oportunidad", "left"), ("Cierre", "right")] if items else [], filas)
    return salida


def html_grupos(grupos, ahora, titulo, vacio, cupo=None, amplia=None, max_bytes=None):
    """Una tabla por grupo (palabra clave, entidad o región), ordenada por fecha de cierre.
    - Lo nuevo va en fila completa hasta cupo["completas"]; el resto de lo nuevo, en una línea
      hasta cupo["nuevas_breves"]; lo ya informado que cierra pronto, en una línea hasta cupo["breves"].
    - max_bytes: tope de la sección entera, para que Gmail no corte el correo.
    - amplia: desde cuántos resultados se sugiere afinar la palabra clave.
    Lo que no entra se cuenta en una línea con el enlace al portal."""
    cupo = {"completas": 10 ** 6, "breves": 10 ** 6, "nuevas_breves": 0, **(cupo or {})}
    limite = max_bytes if max_bytes is not None else 10 ** 9
    usados, salida = 0, ""
    RESERVA_GRUPO = 1_500  # título, recuadro y notas de cada grupo

    def cabe(html_fila):
        return len(salida.encode()) + usados + len(html_fila.encode()) + RESERVA_GRUPO <= limite

    for nombre, items in grupos:
        usados = 0  # filas de este grupo que todavía no están en `salida`
        nuevos, pronto, resto = repartir(items, ahora)
        filas, completas, breves_nuevas, recordatorios = "", 0, 0, 0
        for x in nuevos:
            if completas >= min(MAX_FILAS, cupo["completas"]):
                break
            f = fila(completas, recortar(oracion(x["titulo"]), 140), x["url"], etiquetas_proceso(x, ahora),
                     detalle_proceso(x), *fecha_proceso(x, ahora), extra=enlace_bases(x))
            if not cabe(f):
                break
            filas, usados, completas = filas + f, usados + len(f.encode()), completas + 1
        for x in nuevos[completas:]:
            if breves_nuevas >= cupo["nuevas_breves"]:
                break
            f = fila_breve(x, ahora, primera=not filas)
            if not cabe(f):
                break
            filas, usados, breves_nuevas = filas + f, usados + len(f.encode()), breves_nuevas + 1
        cupo["completas"] -= completas
        cupo["nuevas_breves"] -= breves_nuevas
        faltan = len(nuevos) - completas - breves_nuevas
        if faltan:
            filas += fila_nota(f"y {plural(faltan, 'nuevo más', 'nuevos más')} (no entraron en el correo).",
                               seace.PORTAL_OPORTUNIDADES, "Ver en el portal", primera=not filas)
        for x in pronto:
            if recordatorios >= min(MAX_FILAS, cupo["breves"]):
                break
            rotulo = rotulo_tabla("YA INFORMADOS · CIERRAN PRONTO", primera=not filas) if not recordatorios else ""
            f = rotulo + fila_breve(x, ahora)
            if not cabe(f):
                break
            filas, usados, recordatorios = filas + f, usados + len(f.encode()), recordatorios + 1
        cupo["breves"] -= recordatorios
        resto += len(pronto) - recordatorios
        if resto:
            filas += fila_nota(plural(resto, "proceso ya informado sigue abierto.", "procesos ya informados siguen abiertos."),
                               seace.PORTAL_OPORTUNIDADES, "Ver en el portal", primera=not filas)
        if amplia and len(items) >= amplia:
            filas += fila_nota(f"Esta palabra clave es muy general ({len(items)} resultados): hazla más específica "
                               f"o ponla entre comillas junto a otra palabra.", primera=not filas)
        if not items:
            filas = fila_nota(vacio, primera=True)
        salida += subtitulo(titulo(nombre), plural(len(items), "abierto", "abiertos"))
        # Sin filas completas, la cabecera de columnas sobra: basta el recuadro con las líneas.
        salida += tabla([("Oportunidad", "left"), ("Cierre", "right")] if completas else [], filas)
    return salida


def nombre_zona(zona):
    return nombre_propio(zona["region"]) + (f" · {nombre_propio(zona['provincia'])}" if zona["provincia"] else "")


def html_uniq(convs, ahora, completo=True):
    """Modo completo: todas en fila completa. Modo resumido: las ya informadas en una línea."""
    filas = ""
    for c in convs:
        dias = dias_hasta(c["limite"], ahora)
        if not completo and not c["nueva"]:
            filas += fila_breve({"url": c["tdr_url"] or uniq.URL_PAGINA, "titulo": c["titulo"], "nuevo": False,
                                 "entidad": f'N° {c["numero"]} · {nombre_propio(c["dependencia"])}', "cierre": c["limite"],
                                 "abierta": True, "inicio": None, "convocatoria": None}, ahora, primera=not filas)
            continue
        marcas = etiqueta("NUEVA", "azul") if c["nueva"] else ""
        if dias <= DIAS_ALERTA:
            marcas += etiqueta("CIERRA PRONTO", "rojo")
        if c.get("coincide"):
            marcas += etiqueta(f'Coincide: {c["coincide"]}', "contorno")
        if c["desierta"]:
            marcas += etiqueta("Sin postores en la anterior", "gris")
        conv = f' · {c["convocatoria"]}ª convocatoria' if c["convocatoria"] > 1 else ""
        detalle = f'{c["tipo"]} · N° {c["numero"]}{conv} · {nombre_propio(c["dependencia"])}'
        filas += fila(1 if filas else 0, recortar(oracion(c["titulo"]), 140), c["tdr_url"] or uniq.URL_PAGINA, marcas,
                      detalle, cuando(c["limite"], ahora), "fecha límite", dias <= DIAS_ALERTA)
    return tabla([("Cotización", "left"), ("Vence", "right")], filas)


def html_parrafos(texto):
    """Texto del PDF -> HTML: los renglones cortos en mayúsculas pasan a subtítulo."""
    partes = []
    for linea in texto.split("\n"):
        rotulo = linea.startswith("— ") and linea.endswith(" —")
        if rotulo or (linea.isupper() and len(linea) <= 60):
            partes.append(f'<div style="font-weight:600;color:{C["texto"]};margin-top:8px">'
                          f'{h(oracion(linea.strip("— ")))}</div>')
        else:
            if partes and not partes[-1].endswith("</div>"):
                partes.append("<br>")
            partes.append(h(oracion(linea)))
    return "".join(partes)


def bloque_ficha(icono, titulo, contenido):
    return (f'<tr><td style="padding:14px 16px 0">'
            f'<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
            f'<td valign="middle" style="padding-right:6px">{img(icono, 14)}</td>'
            f'<td valign="middle" style="font-size:11px;line-height:16px;font-weight:700;letter-spacing:0.06em;'
            f'color:{C["enlace"]}">{h(titulo.upper())}</td></tr></table>'
            f'<div style="margin-top:4px;font-size:13px;line-height:20px;color:{C["cuerpo"]}">{contenido}</div>'
            f'</td></tr>')


def html_ficha(c, ahora):
    """Ficha técnica de una cotización UNIQ nueva: datos del sistema + extracto del TDR/EETT."""
    dias = dias_hasta(c["limite"], ahora)
    conv = f' · {c["convocatoria"]}ª convocatoria' if c["convocatoria"] > 1 else ""
    marcas = etiqueta("NUEVA", "azul") if c["nueva"] else ""
    if dias <= DIAS_ALERTA:
        marcas += etiqueta("CIERRA PRONTO", "rojo")
    if c.get("coincide"):
        marcas += etiqueta(f'Coincide: {c["coincide"]}', "contorno")
    if c["desierta"]:
        marcas += etiqueta("Sin postores en la anterior", "gris")

    datos = [("Fecha límite", f'{fecha_corta(c["limite"])} ({vence(dias)})'),
             ("Dependencia", nombre_propio(c["dependencia"])), ("Área usuaria", c["correo"]),
             ("Financiamiento", nombre_propio(c["fuente"])),
             ("Plazo de entrega", f'{c["plazo_entrega"]} días' if c["plazo_entrega"] else "")]
    filas = "".join(f'<tr><td width="36%" valign="top" style="padding:6px 12px 6px 0;border-bottom:1px solid {C["linea"]};'
                    f'font-size:12px;line-height:18px;color:{C["suave"]}">{h(k)}</td>'
                    f'<td valign="top" style="padding:6px 0;border-bottom:1px solid {C["linea"]};font-size:13px;'
                    f'line-height:18px;color:{C["texto"]}">{h(v)}</td></tr>' for k, v in datos if v)
    cuerpo = (f'<tr><td style="padding:6px 16px 0"><table role="presentation" width="100%" cellpadding="0" '
              f'cellspacing="0">{filas}</table></td></tr>')

    if c["items"]:
        lis = "".join(f'<tr><td style="padding:4px 10px 4px 0;border-bottom:1px solid {C["linea"]}">{h(oracion(n))}</td>'
                      f'<td align="right" style="padding:4px 0;border-bottom:1px solid {C["linea"]};text-align:right;'
                      f'white-space:nowrap;font-weight:600;color:{C["texto"]}">{h(q)}</td></tr>'
                      for n, q in c["items"][:MAX_ITEMS])
        if len(c["items"]) > MAX_ITEMS:
            lis += f'<tr><td colspan="2" style="padding:4px 0">y {len(c["items"]) - MAX_ITEMS} ítems más en el PDF</td></tr>'
        cuerpo += bloque_ficha("items", f"Ítems ({len(c['items'])})",
                               f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{lis}</table>')
    for clave, titulo, _, _ in uniq.SECCIONES:
        if c["secciones"].get(clave):
            cuerpo += bloque_ficha(clave, titulo, html_parrafos(c["secciones"][clave]))
    if c["error_pdf"]:
        cuerpo += bloque_ficha("error_pdf", f'No se pudo leer el {c["doc"]}', h(c["error_pdf"]))
    if c["tdr_url"]:
        abrir = boton(c["tdr_url"], f'Abrir {c["doc"]} completo (PDF)', "pdf")
        cuerpo += f'<tr><td style="padding:0 16px 16px">{abrir}</td></tr>'

    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {C["linea"]};'
            f'border-radius:8px;border-collapse:separate;border-spacing:0;margin:0 0 16px">'
            f'<tr><td style="background:{C["cabecera"]};border-bottom:1px solid {C["linea"]};padding:14px 16px;'
            f'border-radius:8px 8px 0 0">'
            f'<div style="font-size:11px;line-height:16px;font-weight:600;letter-spacing:0.06em;color:{C["suave"]}">'
            f'UNIQ · {h(c["tipo"].upper())} · N° {c["numero"]}{h(conv.upper())}</div>'
            f'<div style="font-size:16px;line-height:22px;font-weight:700;color:{C["navy"]};margin:4px 0 8px">'
            f'{h(oracion(c["titulo"]))}</div>{marcas}</td></tr>{cuerpo}</table>')


def html_fuentes(fuentes):
    filas = ""
    for i, (nombre, ok, detalle, cobertura) in enumerate(fuentes):
        borde = f"border-top:1px solid {C['linea']};" if i else ""
        estado = etiqueta("OPERATIVA", "azul") if ok else etiqueta("SIN RESPUESTA", "rojo")
        filas += (f'<tr><td valign="top" style="{borde}padding:10px 12px;font-size:13px;line-height:19px">'
                  f'<div style="font-weight:600;color:{C["texto"]}">{h(nombre)}</div>'
                  f'<div style="font-size:12px;color:{C["suave"]}">{h(cobertura)}</div></td>'
                  f'<td valign="top" align="right" style="{borde}padding:10px 12px;text-align:right">{estado}'
                  f'<div style="font-size:12px;line-height:17px;color:{C["suave"]}">{h(detalle)}</div></td></tr>')
    return tabla([("Fuente", "left"), ("Estado", "right")], filas)


# ------------------------------------------------------------------ informe

def construir_informe(ahora, palabras, convs, grupos, fuentes, seguidas=(), zonas=(), completo=True):
    """convs: cotizaciones UNIQ (None si la fuente falló). grupos: [(frase, [procesos])].
    fuentes: [(nombre, ok, detalle, cobertura)]. seguidas: [(entidad, [procesos])].
    zonas: [(zona, [procesos])] de REGIONES.
    completo: todo en detalle cada día, aunque el correo sea largo (Gmail muestra "Ver mensaje completo");
    si es False, lo ya informado se resume y el correo se mantiene bajo el límite de Gmail.
    Devuelve (asunto, texto, html)."""
    todos = [x for _, items in grupos for x in items]
    nuevos = sum(x["nuevo"] for x in todos)
    pronto = sum(1 for x in todos if x["cierre"] and x["abierta"] and dias_hasta(x["cierre"], ahora) <= DIAS_ALERTA)
    uniq_nuevas = [c for c in convs or [] if c["nueva"]]

    asunto = (f"Informe de oportunidades – {ahora:%d/%m/%Y} · {plural(len(todos), 'coincidencia', 'coincidencias')}"
              f" ({nuevos} nuevas)" + (f" · UNIQ: {len(convs)} activas" if convs is not None else ""))

    if not palabras:
        frase = "No hay palabras clave configuradas: define PALABRAS_CLAVE en el archivo .env."
    elif not todos:
        frase = "Hoy no hay procesos que coincidan con tus palabras clave."
    else:
        frase = (f"Hay {plural(len(todos), 'proceso que coincide', 'procesos que coinciden')} con tus palabras clave"
                 + (f"; {plural(nuevos, 'es nuevo', 'son nuevos')}" if nuevos else "")
                 + (f" y {plural(pronto, 'cierra', 'cierran')} en 2 días o menos" if pronto else "") + ".")
    for entidad, items in seguidas:
        frase += (f" {nombre_propio(entidad)} tiene "
                  f"{plural(len(items), 'proceso abierto', 'procesos abiertos')}.")
    if zonas:
        en_zonas = [x for _, items in zonas for x in items]
        frase += (f" En tus regiones hay {plural(len(en_zonas), 'otro proceso abierto', 'otros procesos abiertos')}"
                  f" ({plural(sum(x['nuevo'] for x in en_zonas), 'nuevo', 'nuevos')}).")
    if convs is None:
        frase += " La página de cotizaciones de la UNIQ no respondió hoy."
    else:
        frase += (f" En la UNIQ hay {plural(len(convs), 'cotización activa', 'cotizaciones activas')}"
                  f" ({plural(len(uniq_nuevas), 'nueva', 'nuevas')}).")

    numero = iter(range(1, 10))  # las secciones opcionales no dejan huecos en la numeración
    cuerpo = encabezado(ahora, palabras, [e for e, _ in seguidas], [z for z, _ in zonas]) + aviso_fuentes(fuentes)
    cuerpo += seccion(next(numero), "s_resumen", "Resumen ejecutivo")
    cuerpo += indicadores([(len(todos), "Coincidencias", False), (nuevos, "Nuevas", False),
                           (pronto, "Por cerrar", True), (len(convs or []), "UNIQ activas", False)])
    cuerpo += f'<p style="margin:14px 0 0;font-size:14px;line-height:22px;color:{C["cuerpo"]}">{h(frase)}</p>'

    # Primero lo corto y siempre importante (UNIQ y entidades); después lo que puede crecer mucho
    # (coincidencias y fichas), así lo que Gmail llegara a cortar es lo menos urgente.
    cuerpo += seccion(next(numero), "s_uniq", "Cotizaciones UNIQ activas", "Todas las convocatorias vigentes, por fecha límite.")
    if convs is None:
        cuerpo += f'<p style="font-size:14px;color:{C["rojo"]}">La fuente no respondió hoy.</p>'
    elif not convs:
        cuerpo += f'<p style="font-size:14px;color:{C["suave"]}">No hay convocatorias activas hoy.</p>'
    else:
        cuerpo += html_uniq(convs, ahora, completo)

    # Modo resumido: cada sección larga usa una parte de lo que QUEDA bajo el límite de Gmail (lo que no
    # gasta pasa a la siguiente); las fichas llenan el resto. En modo completo no hay tope.
    reserva = len((seccion(9, "s_fuentes", "Fuentes") + html_fuentes(fuentes)).encode()) + 1_000

    def queda(fraccion):
        return max(0, int((LIMITE_HTML - len(cuerpo.encode()) - reserva) * fraccion))

    if seguidas:
        cuerpo += seccion(next(numero), "s_entidades", "Entidades que sigues",
                          "Todo lo que tienen abierto (procedimientos y contrataciones menores), sin filtrar por palabra clave.")
        vacio = "Sin procesos abiertos en este momento."
        cuerpo += (html_grupos_completo(seguidas, ahora, nombre_propio, vacio) if completo else
                   html_grupos(seguidas, ahora, nombre_propio, vacio, cupo={"nuevas_breves": 30}, max_bytes=queda(0.30)))

    cuerpo += seccion(next(numero), "s_coinc", "Coincidencias por palabra clave",
                      "SEACE (contrataciones menores y procedimientos de selección con el registro abierto) "
                      "y cotizaciones de la UNIQ. Ordenadas por fecha de cierre.")
    if not palabras:
        cuerpo += f'<p style="font-size:14px;color:{C["suave"]}">Define PALABRAS_CLAVE en el archivo .env para activar esta sección.</p>'
    elif completo:
        cuerpo += html_grupos_completo(grupos, ahora, mostrar, "Sin coincidencias en este momento.", amplia=MUY_GENERAL)
    else:
        cuerpo += html_grupos(grupos, ahora, mostrar, "Sin coincidencias en este momento.",
                              cupo={"completas": CUPO_COMPLETAS, "breves": CUPO_BREVES}, amplia=MUY_GENERAL,
                              max_bytes=queda(0.45))

    # Las regiones van después de las palabras clave: son lo más largo (cientos de procesos) y lo
    # buscado específicamente tiene que quedar arriba, en la parte que Gmail muestra sin hacer clic.
    if zonas:
        cuerpo += seccion(next(numero), "s_regiones", "Regiones que sigues",
                          "Todo lo abierto en esas regiones y provincias (gobierno regional, municipalidades, redes de "
                          "salud, UGEL, universidades...), que no esté ya en las secciones anteriores.")
        vacio = "Sin procesos abiertos en este momento."
        cuerpo += (html_grupos_completo(zonas, ahora, nombre_zona, vacio) if completo else
                   html_grupos(zonas, ahora, nombre_zona, vacio, cupo={"completas": 10, "nuevas_breves": 40, "breves": 15},
                               max_bytes=queda(0.80)))

    # Completo: ficha de todas las cotizaciones UNIQ activas. Resumido: solo las nuevas, mientras quepan
    # bajo el límite de Gmail; las demás quedan enlazadas desde la tabla de cotizaciones UNIQ.
    con_ficha = list(convs or []) if completo else uniq_nuevas
    fichas, omitidas = "", 0
    for c in con_ficha:
        ficha = html_ficha(c, ahora)
        if not completo and len((cuerpo + fichas + ficha).encode()) + reserva > LIMITE_HTML:
            omitidas += 1
        else:
            fichas += ficha
    if con_ficha:
        cuerpo += seccion(next(numero), "s_fichas", "Fichas técnicas de las cotizaciones UNIQ" + ("" if completo else " nuevas"),
                          "Extracto del TDR/EETT: lo necesario para decidir si cotizar.") + fichas
        if omitidas:
            cuerpo += (f'<p style="margin:0 0 12px;font-size:13px;line-height:19px;color:{C["suave"]}">'
                       f'{plural(omitidas, "ficha más no entró", "fichas más no entraron")} en este correo para que Gmail '
                       f'no lo corte: su TDR/EETT está enlazado en la tabla de cotizaciones UNIQ.</p>')

    cuerpo += seccion(next(numero), "s_fuentes", "Fuentes")
    cuerpo += html_fuentes(fuentes)

    texto = texto_informe(ahora, palabras, convs, grupos, fuentes, frase, seguidas, zonas, completo)
    return asunto, texto, envolver(cuerpo, "Informe de oportunidades")


def texto_grupos(grupos, ahora, titulo, completo=True):
    lineas = []
    for nombre, items in grupos:
        lineas.append(f"\n{titulo(nombre)} · {plural(len(items), 'abierto', 'abiertos')}")
        # completo: todo como si fuera nuevo (lista entera, sin resumir lo ya informado)
        nuevos, pronto, resto = (items, [], 0) if completo else repartir(items, ahora)
        for x in pronto[:MAX_FILAS]:
            lineas.append(f"  [YA INFORMADO, CIERRA {fecha_proceso(x, ahora)[0].upper()}] {recortar(oracion(x['titulo']), 90)}")
        if resto:
            lineas.append(f"  ({plural(resto, 'proceso ya informado sigue abierto', 'procesos ya informados siguen abiertos')})")
        for x in (nuevos if completo else nuevos[:MAX_FILAS]):
            fecha, pie, _ = fecha_proceso(x, ahora)
            lineas += [f"  {'[NUEVO] ' if x['nuevo'] else ''}{oracion(x['titulo'])}",
                       f"    {x['fuente']} · {x['tipo']} · {detalle_proceso(x)} · {pie}: {fecha}", f"    {x['url']}"]
            if x.get("bases"):
                lineas.append(f"    Bases: {x['bases']}")
    return lineas


def texto_informe(ahora, palabras, convs, grupos, fuentes, frase, seguidas=(), zonas=(), completo=True):
    """Versión en texto plano (clientes sin HTML y vista previa del --dry-run)."""
    numero = iter(range(1, 10))
    lineas = ["MONITOR DE CONTRATACIONES PÚBLICAS", "Informe diario de oportunidades",
              f"{fecha_larga(ahora)} · emitido a las {ahora:%H:%M}",
              f"Palabras clave: {', '.join(palabras) or 'ninguna'}"]
    if zonas:
        lineas.append(f"Regiones: {', '.join(nombre_zona(z) for z, _ in zonas)}")
    if seguidas:
        lineas.append(f"Entidades: {', '.join(nombre_propio(e) for e, _ in seguidas)}")
    lineas += ["", f"{next(numero)}. RESUMEN EJECUTIVO", frase, "", f"{next(numero)}. COTIZACIONES UNIQ ACTIVAS"]
    if convs is None:
        lineas.append("La fuente no respondió hoy.")
    for c in convs or []:
        lineas += [f"  {'[NUEVA] ' if c['nueva'] else ''}{oracion(c['titulo'])}",
                   f"    {c['tipo']} · N° {c['numero']} · {nombre_propio(c['dependencia'])} · "
                   f"vence {fecha_corta(c['limite'])}", f"    {c['tdr_url'] or uniq.URL_PAGINA}"]
    if seguidas:
        lineas += ["", f"{next(numero)}. ENTIDADES QUE SIGUES"] + texto_grupos(seguidas, ahora, nombre_propio, completo)
    lineas += ["", f"{next(numero)}. COINCIDENCIAS POR PALABRA CLAVE"] + texto_grupos(grupos, ahora, mostrar, completo)
    if zonas:
        lineas += ["", f"{next(numero)}. REGIONES QUE SIGUES"] + texto_grupos(zonas, ahora, nombre_zona, completo)
    con_ficha = list(convs or []) if completo else [c for c in convs or [] if c["nueva"]]
    if con_ficha:
        lineas += ["", f"{next(numero)}. FICHAS TÉCNICAS (UNIQ{'' if completo else ', NUEVAS'})"]
        for c in con_ficha:
            lineas += ["", "-" * 60, f"{c['tipo']} · N° {c['numero']} · {oracion(c['titulo'])}",
                       f"Fecha límite: {fecha_corta(c['limite'])} · Dependencia: {nombre_propio(c['dependencia'])}"]
            if c["items"]:
                lineas += ["Ítems:"] + [f"  - {oracion(n)}: {q}" for n, q in c["items"][:MAX_ITEMS]]
            for clave, titulo, _, _ in uniq.SECCIONES:
                if c["secciones"].get(clave):
                    lineas += [f"{titulo}:", c["secciones"][clave]]
    lineas += ["", "FUENTES"] + [f"  {n}: {'operativa' if ok else 'SIN RESPUESTA'} · {d} · {cob}" for n, ok, d, cob in fuentes]
    return "\n".join(lineas)


def construir_alerta(detalle, ahora):
    """Correo de falla total: ninguna fuente respondió."""
    asunto = f"Monitor de contrataciones: no se pudo generar el informe – {ahora:%d/%m/%Y %H:%M}"
    texto = f"No se pudo generar el informe de hoy: ninguna fuente respondió.\n\n{detalle}"
    cuerpo = (marca("No se pudo generar el informe", ahora)
              + f'<p style="margin:18px 0 10px;font-size:14px;line-height:22px;color:{C["cuerpo"]}">'
                f'Ninguna de las fuentes respondió. Revisa si las páginas cambiaron o están caídas. Detalle técnico:</p>'
              + f'<pre style="white-space:pre-wrap;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;'
                f'line-height:17px;background:{C["cabecera"]};border:1px solid {C["linea"]};border-radius:6px;'
                f'padding:12px;margin:0">{h(detalle)}</pre>')
    return asunto, texto, envolver(cuerpo, "Error del monitor")
