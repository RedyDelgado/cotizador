# Imagen para probar NEOESTADO en local (ver docker-compose.yml). El VPS no usa Docker: usa install.sh.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py admin.py admin.html empleos.py informe.py seace.py uniq.py maestras.json test_bot.py perfiles.ini.example ./
COPY assets ./assets
COPY docker/entrada.sh /entrada.sh

# Sin root: el estado, los logs y la configuración viven en volúmenes (docker-compose.yml).
RUN useradd --create-home --uid 1000 neo && mkdir -p /app/data /app/logs /config && chown -R neo /app /config && chmod +x /entrada.sh
USER neo

ENTRYPOINT ["/entrada.sh"]
CMD ["python", "bot.py", "--dry-run"]
