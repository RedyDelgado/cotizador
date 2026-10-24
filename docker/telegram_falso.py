"""Telegram de mentira para probar en local (docker compose): atrapa lo que se "envía" y sirve mensajes de prueba.

  POST /bot<token>/sendMessage      como Telegram: guarda el mensaje
  GET  /bot<token>/getUpdates       como Telegram: entrega los mensajes en cola (con offset)
  POST /_falso/escribir             {"chat_id": 1, "text": "/start CODIGO"}: simula que alguien le escribe al bot
  GET  /_falso/enviados             lo que el bot y el panel enviaron
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

enviados, cola, siguiente = [], [], [1]


class Falso(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def responder(self, datos):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def cuerpo(self):
        largo = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(largo) or b"{}")

    def do_POST(self):
        ruta = urlparse(self.path).path
        if ruta.endswith("/sendMessage"):
            mensaje = self.cuerpo()
            enviados.append(mensaje)
            return self.responder({"ok": True, "result": {"message_id": len(enviados)}})
        if ruta == "/_falso/escribir":
            dato = self.cuerpo()
            cola.append({"update_id": siguiente[0], "message": {"chat": {"id": int(dato["chat_id"])}, "text": dato["text"]}})
            siguiente[0] += 1
            return self.responder({"ok": True})
        self.responder({"ok": False})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.endswith("/getUpdates"):
            desde = int(parse_qs(url.query).get("offset", ["0"])[0])
            return self.responder({"ok": True, "result": [u for u in cola if u["update_id"] >= desde]})
        if url.path == "/_falso/enviados":
            return self.responder(enviados)
        self.responder({"ok": False})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8081), Falso).serve_forever()
