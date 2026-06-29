"""
servidor.py — Puente entre la interfaz web y la lógica de simulación.

No hace cálculos: recibe pedidos del navegador, llama a logica.py y devuelve
JSON. Usa solo la librería estándar de Python (no hace falta instalar nada).

Ejecutar:  python servidor.py   ->   http://localhost:8000
"""

import json
import os
import random
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# logica.py vive en la carpeta de arriba (Modelo interfaz).
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))

import logica
from logica import Parametros, META_PARAMETROS

PUERTO = 8000
PARAMETROS = Parametros()   # estado único que se va editando

ESTATICOS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/estilo.css": ("estilo.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


def serializar_estado(p):
    parametros = [{"clave": c, "etiqueta": e, "valor": getattr(p, c), "unidad": u,
                   "tipo": "int" if t is int else "float"}
                  for c, (e, t, u, _) in META_PARAMETROS.items()]
    return {
        "parametros": parametros,
        "derivados": {"precio_milanesa": p.precio_milanesa, "margen_milanesa": p.margen_milanesa},
        "restricciones": {"Tf": p.Tf, "TI": p.TI,
                          "tolerancia_activa": p.abandono_por_tolerancia, "tolerancia": p.tolerancia},
    }


def serializar_jornada(res):
    filas = [dict(f, atendido=f["estado"] == "Atendido") for f in res.filas]
    return {
        "filas": filas,
        "resumen": {
            "atendidos": res.atendidos,
            "perdidos_tolerancia": res.perdidos_tolerancia,
            "milanesas_vendidas": res.milanesas_vendidas,
            "milanesas_no_vendidas": res.milanesas_no_vendidas,
            "espera_promedio": res.espera_promedio,
            "espera_maxima": res.espera_maxima,
            "stock_remanente": res.stock_remanente,
            "ganancia_bruta": res.ganancia_bruta,
            "costo_total": res.costo_total,
            "ganancia_neta": res.ganancia_neta,
            "perdida_oportunidad": res.perdida_oportunidad,
        },
    }


def serializar_replicas(rep):
    return {k: getattr(rep, k) for k in (
        "corridas", "atendidos", "perdidos_tolerancia", "milanesas_vendidas",
        "milanesas_no_vendidas", "ganancia_bruta", "costo_total", "ganancia_neta",
        "perdida_oportunidad", "espera_promedio", "espera_maxima", "stock_remanente")}


def actualizar_parametro(datos):
    clave = datos.get("clave")
    if clave not in META_PARAMETROS:
        return False, "Parámetro desconocido."
    etiqueta, tipo, _, validador = META_PARAMETROS[clave]
    crudo = str(datos.get("valor", "")).strip().replace(",", ".")
    try:
        valor = tipo(float(crudo)) if tipo is int else tipo(crudo)
    except (ValueError, TypeError):
        return False, f"'{etiqueta}' necesita un número válido."
    if not validador(valor):
        return False, f"El valor de '{etiqueta}' no cumple las restricciones."
    if clave == "TI" and valor > PARAMETROS.Tf:
        return False, "El límite de ingreso (TI) no puede superar al cierre (Tf)."
    if clave == "Tf" and valor < PARAMETROS.TI:
        return False, "El cierre (Tf) no puede ser menor al límite de ingreso (TI)."
    setattr(PARAMETROS, clave, valor)
    return True, f"'{etiqueta}' actualizado."


def _stock_de(modo):
    return 0 if modo == "sin" else PARAMETROS.stock_inicial


def _muestra(modo):
    """Una jornada de muestra etiquetada como la corrida N° X de las N totales."""
    stock = _stock_de(modo)
    jornada = logica.simular_jornada(PARAMETROS, stock_inicial=stock)
    nro = random.randint(1, max(1, PARAMETROS.cantidad_corridas))
    return {"modo": modo, "stock": stock, "muestra_nro": nro,
            "total_corridas": PARAMETROS.cantidad_corridas,
            "jornada": serializar_jornada(jornada)}


def correr_simulacion(datos):
    """Simulación completa: una muestra + el promedio de las N corridas."""
    modo = datos.get("modo", "sin")
    salida = _muestra(modo)
    replicas = logica.correr_replicas(PARAMETROS, stock_inicial=_stock_de(modo))
    salida["replicas"] = serializar_replicas(replicas)
    return salida


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, datos, codigo=200):
        cuerpo = json.dumps(datos).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _estatico(self, archivo, tipo):
        ruta = os.path.join(AQUI, archivo)
        if not os.path.isfile(ruta):
            return self.send_error(404)
        with open(ruta, "rb") as fh:
            cuerpo = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _cuerpo(self):
        largo = int(self.headers.get("Content-Length", 0))
        if not largo:
            return {}
        try:
            return json.loads(self.rfile.read(largo).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        if self.path in ESTATICOS:
            self._estatico(*ESTATICOS[self.path])
        elif self.path == "/api/estado":
            self._json(serializar_estado(PARAMETROS))
        else:
            self.send_error(404)

    def do_POST(self):
        datos = self._cuerpo()
        if self.path == "/api/parametros":
            ok, msg = actualizar_parametro(datos)
            self._json({"ok": ok, "mensaje": msg, "estado": serializar_estado(PARAMETROS)},
                       200 if ok else 400)
        elif self.path == "/api/restricciones":
            PARAMETROS.abandono_por_tolerancia = bool(datos.get("valor"))
            self._json({"ok": True, "estado": serializar_estado(PARAMETROS)})
        elif self.path == "/api/simular":
            self._json(correr_simulacion(datos))
        elif self.path == "/api/muestra":
            self._json(_muestra(datos.get("modo", "sin")))
        else:
            self.send_error(404)


def main():
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), Handler)
    url = f"http://localhost:{PUERTO}"
    print(f"Simulación 'El Fuerte' andando en {url}  (Ctrl+C para frenar)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n¡Gracias por ocupar la simulación!")


if __name__ == "__main__":
    main()
