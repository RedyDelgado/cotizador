"""Resumen de las bases de un procedimiento de selección (documento público de SEACE).

Las bases estándar traen lo que decide si conviene postular: experiencia exigida al postor, plazo de
ejecución y forma de pago. Se descargan una sola vez por proceso (DOCX, ZIP con DOCX, o PDF con texto)
y se extraen con frases fijas de las bases estándar; lo que una entidad redacte distinto no se encuentra
y se deja en blanco, nunca se inventa. Los escaneados y los .rar no se pueden leer: se avisa.
"""
import io
import re
import zipfile

MAX_MB = 20  # más que eso suelen ser escaneados; no vale la pena descargarlos

NUMEROS = r"[\d][\d.,’'´\s]*\d|\d"


def _limpiar(texto):
    return " ".join(texto.split())


def texto_de_bases(contenido):
    """Texto del documento. Devuelve (texto, motivo): motivo explica por qué no hay texto."""
    if contenido[:4] == b"%PDF":
        import pymupdf
        with pymupdf.open(stream=contenido, filetype="pdf") as doc:
            texto = "\n".join(p.get_text() for p in doc)
        return (texto, None) if len(texto) > 3000 else ("", "documento escaneado")
    if contenido[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(contenido))
        nombres = z.namelist()
        if "word/document.xml" in nombres:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
            xml = re.sub(r"</w:p>", "\n", xml)
            xml = re.sub(r"<w:(?:tab|br)\s*/>", " ", xml)
            return re.sub(r"<[^>]+>", "", xml), None
        candidatos = [n for n in nombres if n.lower().endswith((".docx", ".pdf"))]
        if candidatos:  # varios archivos: el de las bases (el que dice "base", o el más grande)
            mejor = max(candidatos, key=lambda n: ("base" in n.lower(), n.lower().endswith(".docx"), z.getinfo(n).file_size))
            return texto_de_bases(z.read(mejor))
        return "", "formato no compatible"
    return "", "formato no compatible (.rar u otro)"


def _monto(texto):
    """"S/ 1’500,000.00 (un millón...)" -> "S/ 1,500,000" """
    crudo = re.sub(r"[’'´\s]", "", texto)
    m = re.match(r"([\d.,]+)", crudo)
    if not m:
        return None
    num = m.group(1)
    if re.search(r",\d{2}$", num) and "." not in num[-3:]:  # 200 000,00 (coma decimal)
        num = num[:-3]
    num = re.sub(r"\.\d{2}$", "", num)
    digitos = re.sub(r"[.,]", "", num)
    return f"S/ {int(digitos):,}" if digitos.isdigit() else None


def experiencia(texto):
    """Experiencia del postor: monto facturado y período."""
    m = re.search(r"monto\s+facturado\s+acumulado\s+equivalente\s+a\s+(?:S/\.?|PEN)?\s*(" + NUMEROS + r")(.{0,420})",
                  texto, re.I | re.S)
    if not m:
        return None
    monto = _monto(m.group(1))
    if not monto:
        return None
    resto = _limpiar(m.group(2))
    objeto = re.search(r"\b(bienes|servicios|obras|consultor[ií]as?)\s+iguales\s+o\s+similares", resto, re.I)
    anios = re.search(r"durante\s+(?:los\s+)?(\w+)\s*(?:\((\d+)\))?\s+a[ñn]os", resto, re.I)
    pal_num = {"cinco": 5, "ocho": 8, "diez": 10, "quince": 15, "veinte": 20}
    n = anios and (anios.group(2) or pal_num.get(anios.group(1).lower()) or anios.group(1))
    partes = [f"{monto} facturados"]
    if objeto:
        partes.append(f"en {objeto.group(1).lower()} iguales o similares")
    if n:
        partes.append(f"en los últimos {n} años")
    return " ".join(partes)


def plazo(texto):
    """Plazo de ejecución o de entrega, con la frase como la redactó la entidad."""
    for m in re.finditer(r"plazo\s+de\s+(?:ejecuci[oó]n|entrega|prestaci[oó]n)[^.\n]{0,220}?"
                         r"(\d{1,4})\s*(?:\([^)]{0,25}\)\s*)?(d[ií]as|meses|semanas|horas)[^.\n]{0,70}", texto, re.I):
        frase = _limpiar(m.group(0))
        if "máximo" in frase.lower() or "será" in frase.lower() or "sera" in frase.lower() or "de " in frase.lower():
            return frase[:230]
    return None


def pago(texto):
    """Forma de pago: la oración que sigue al encabezado (no al índice del documento)."""
    for m in re.finditer(r"forma\s+de\s+pago\s*[:.\-–]?\s*\n?(.{80,700})", texto, re.I | re.S):
        cuerpo = _limpiar(m.group(1))
        if re.search(r"\bpago|abonar|cancelar", cuerpo[:300], re.I) and "....." not in cuerpo[:80]:
            oracion = re.match(r"(.{40,320}?[.;:])(?:\s|$)", cuerpo)
            return (oracion.group(1) if oracion else cuerpo[:300])
    return None


def resumir(texto):
    """{"experiencia", "plazo", "pago"}: lo que se encontró; None en lo que no."""
    return {"experiencia": experiencia(texto), "plazo": plazo(texto), "pago": pago(texto)}
