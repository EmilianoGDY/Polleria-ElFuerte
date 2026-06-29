"""
logica.py — Núcleo de cálculo de la simulación de la Pollería "El Fuerte".

Sistema de colas con servidor único (un operario), disciplina FIFO.
Variables aleatorias por Montecarlo con distribuciones empíricas.
Este archivo solo calcula: no imprime ni pide datos por consola.
"""

from dataclasses import dataclass, field
import math
import random
import statistics


# --- Distribuciones empíricas (tablas Montecarlo de campo) ---
# Lista de (probabilidad_acumulada, valor). Se devuelve el primer valor cuyo
# tramo supera al aleatorio (igual que BUSCARV aproximado en el Excel).
TABLA_TA = [(0.10, 3.0), (0.30, 5.0), (0.60, 15.0), (0.85, 25.0), (1.00, 32.0)]
TABLA_M = [(0.0450, 2), (0.1240, 4), (0.4050, 6), (0.4610, 8), (0.5280, 10),
           (0.7750, 12), (0.8540, 18), (0.9210, 24), (0.9770, 36), (1.0000, 48)]


def mapear(aleatorio, tabla):
    """Mapea un pseudoaleatorio [0,1) contra una tabla empírica acumulada."""
    for prob, valor in tabla:
        if aleatorio < prob:
            return valor
    return tabla[-1][1]


@dataclass
class Parametros:
    """Panel de parámetros centralizado. Todos editables desde la interfaz."""
    Tf: float = 270.0                  # Cierre de jornada (12:30), en min desde las 08:00
    TI: float = 260.0                  # Límite de ingreso (12:20): después no entran clientes
    alpha: float = 1.50                # Tiempo de preparación por milanesa (min)
    precio_medio_kg: float = 6500.0    # Precio de medio kilo
    milanesas_por_medio_kg: int = 6    # Milanesas por medio kilo
    costo_milanesa: float = 700.0      # Costo de producir 1 milanesa (se resta de la ganancia)
    abandono_por_tolerancia: bool = False  # Restricción de abandono (Corrida 2)
    tolerancia: float = 20.0           # El cliente se retira si la espera supera esto
    stock_inicial: int = 40            # Milanesas pre-elaboradas para la corrida "con stock"
    cantidad_corridas: int = 100       # Réplicas para promediar

    @property
    def precio_milanesa(self):
        return self.precio_medio_kg / self.milanesas_por_medio_kg

    @property
    def margen_milanesa(self):
        return self.precio_milanesa - self.costo_milanesa


@dataclass
class ResultadoJornada:
    filas: list = field(default_factory=list)
    atendidos: int = 0
    perdidos_tolerancia: int = 0
    milanesas_vendidas: int = 0
    milanesas_no_vendidas: int = 0
    espera_total: float = 0.0
    espera_maxima: float = 0.0
    stock_remanente: int = 0
    _precio: float = 0.0
    _costo: float = 0.0

    @property
    def ganancia_bruta(self):
        return self._precio * self.milanesas_vendidas

    @property
    def costo_total(self):
        # Costo de materia prima de las milanesas que SÍ se vendieron.
        return self._costo * self.milanesas_vendidas

    @property
    def desperdicio(self):
        # Costo de las milanesas pre-elaboradas que sobraron (no se vendieron).
        return self._costo * self.stock_remanente

    @property
    def ganancia_neta(self):
        # Ingreso menos: costo de oportunidad (ventas perdidas), materia prima
        # de lo vendido y materia prima del sobrante (desperdicio).
        return (self.ganancia_bruta
                - self.perdida_oportunidad
                - self.costo_total
                - self.desperdicio)

    @property
    def perdida_oportunidad(self):
        return self._precio * self.milanesas_no_vendidas

    @property
    def espera_promedio(self):
        return self.espera_total / self.atendidos if self.atendidos else 0.0


def simular_jornada(p, stock_inicial=None, rng=None):
    """Corre una jornada y devuelve el detalle cliente por cliente + métricas."""
    if stock_inicial is None:
        stock_inicial = p.stock_inicial
    if rng is None:
        rng = random

    res = ResultadoJornada(_precio=p.precio_milanesa, _costo=p.costo_milanesa)
    T = 0.0          # reloj de simulación
    TL = 0.0         # liberación del operario (tiempo comprometido)
    N = 0
    stock = stock_inicial
    liberaciones = []   # fines de atención aún en curso, para calcular NC

    while True:
        r1 = rng.random()
        TA = mapear(r1, TABLA_TA)
        N += 1
        HL = T + TA

        if HL > p.TI:                       # después del límite de ingreso no entra nadie
            break

        liberaciones = [t for t in liberaciones if t > HL]
        NC = len(liberaciones)

        r2 = rng.random()
        M = mapear(r2, TABLA_M)

        HI = max(HL, TL)

        # El stock solo reduce el tiempo de preparación: se preparan las que faltan.
        # Se calcula SIN descontar stock todavía (por si el cliente se retira).
        a_preparar = max(0, M - stock)
        TP = a_preparar * p.alpha
        HF = HI + TP

        # Tiempo de espera TOTAL: espera en cola + preparación (= HF - HL). La
        # tolerancia se aplica sobre este total (entrar, esperar, ser atendido, salir).
        TE = HF - HL

        if p.abandono_por_tolerancia and TE > p.tolerancia:
            # Se retira: no consume stock ni ocupa al operario (TL no avanza).
            res.perdidos_tolerancia += 1
            res.milanesas_no_vendidas += M
            res.filas.append(_fila(N, r1, TA, HL, r2, M, TP, NC, HI, TE, None, "Se retiró", stock))
            T = HL
            continue

        # Atendido: ahora sí descuenta stock y ocupa al operario hasta HF.
        stock = max(0, stock - M)
        TL = HF
        liberaciones.append(TL)

        res.atendidos += 1
        res.milanesas_vendidas += M
        res.espera_total += TE
        res.espera_maxima = max(res.espera_maxima, TE)
        res.filas.append(_fila(N, r1, TA, HL, r2, M, TP, NC, HI, TE, HF, "Atendido", stock))
        T = HL

    res.stock_remanente = stock
    return res


def _fila(N, r1, TA, HL, r2, M, TP, NC, HI, TE, HF, estado, stock):
    return {"N": N, "r1": r1, "TA": TA, "HL": HL, "r2": r2, "M": M, "TP": TP,
            "NC": NC, "HI": HI, "TE": TE, "HF": HF, "estado": estado, "stock": stock}


# --- Intervalos de confianza sobre las réplicas ---
# t de Student de dos colas al 95% según grados de libertad (df = N - 1). Para
# muestras grandes (df >= 30) se usa la aproximación normal z = 1.96.
_T_95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
         8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
         14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
         20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
         26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045}


def t_critico_95(n):
    """Valor crítico t (dos colas, 95%) para una muestra de tamaño n (df = n-1)."""
    df = n - 1
    if df < 1:
        return 0.0
    if df >= 30:
        return 1.96      # muestra grande: aproximación normal
    return _T_95[df]


@dataclass
class Estadistica:
    """Resumen de una variable de respuesta sobre las N réplicas."""
    media: float = 0.0
    desvio: float = 0.0       # desviación estándar muestral (s, con N-1)
    semiancho: float = 0.0    # t * s / sqrt(N): precisión del intervalo
    ic_bajo: float = 0.0      # extremo inferior del IC 95%
    ic_alto: float = 0.0      # extremo superior del IC 95%
    n: int = 0


def estadistica(muestras):
    """Media, desvío e intervalo de confianza del 95% de una lista de valores."""
    n = len(muestras)
    if n == 0:
        return Estadistica()
    media = sum(muestras) / n
    if n < 2:
        return Estadistica(media=media, ic_bajo=media, ic_alto=media, n=n)
    s = statistics.stdev(muestras)              # desvío muestral (ddof = 1)
    h = t_critico_95(n) * s / math.sqrt(n)      # semiancho del intervalo
    return Estadistica(media=media, desvio=s, semiancho=h,
                       ic_bajo=media - h, ic_alto=media + h, n=n)


# Variables de respuesta para las que se reporta el intervalo de confianza.
VARIABLES_IC = ("ganancia_neta", "atendidos", "espera_promedio", "perdida_oportunidad")


@dataclass
class ResultadoReplicas:
    corridas: int = 0
    atendidos: float = 0.0
    perdidos_tolerancia: float = 0.0
    milanesas_vendidas: float = 0.0
    milanesas_no_vendidas: float = 0.0
    ganancia_bruta: float = 0.0
    costo_total: float = 0.0
    desperdicio: float = 0.0
    ganancia_neta: float = 0.0
    perdida_oportunidad: float = 0.0
    espera_promedio: float = 0.0
    espera_maxima: float = 0.0
    stock_remanente: float = 0.0
    intervalos: dict = field(default_factory=dict)   # variable -> Estadistica (IC 95%)


def correr_replicas(p, stock_inicial=None, corridas=None, rng=None):
    """Corre N réplicas y devuelve los promedios + intervalos de confianza (95%)."""
    if corridas is None:
        corridas = p.cantidad_corridas
    if rng is None:
        rng = random

    acum = ResultadoReplicas(corridas=corridas)
    suma_espera = 0.0
    # Guardamos el valor de cada réplica para las variables de respuesta, así
    # podemos calcular desvío e intervalo de confianza (no solo el promedio).
    muestras = {v: [] for v in VARIABLES_IC}
    for _ in range(corridas):
        r = simular_jornada(p, stock_inicial=stock_inicial, rng=rng)
        acum.atendidos += r.atendidos
        acum.perdidos_tolerancia += r.perdidos_tolerancia
        acum.milanesas_vendidas += r.milanesas_vendidas
        acum.milanesas_no_vendidas += r.milanesas_no_vendidas
        acum.ganancia_bruta += r.ganancia_bruta
        acum.costo_total += r.costo_total
        acum.desperdicio += r.desperdicio
        acum.ganancia_neta += r.ganancia_neta
        acum.perdida_oportunidad += r.perdida_oportunidad
        acum.espera_maxima += r.espera_maxima
        acum.stock_remanente += r.stock_remanente
        suma_espera += r.espera_promedio

        muestras["ganancia_neta"].append(r.ganancia_neta)
        muestras["atendidos"].append(r.atendidos)
        muestras["espera_promedio"].append(r.espera_promedio)
        muestras["perdida_oportunidad"].append(r.perdida_oportunidad)

    n = corridas if corridas else 1
    for campo in ("atendidos", "perdidos_tolerancia", "milanesas_vendidas",
                  "milanesas_no_vendidas", "ganancia_bruta", "costo_total",
                  "desperdicio", "ganancia_neta", "perdida_oportunidad",
                  "espera_maxima", "stock_remanente"):
        setattr(acum, campo, getattr(acum, campo) / n)
    acum.espera_promedio = suma_espera / n
    acum.intervalos = {v: estadistica(muestras[v]) for v in VARIABLES_IC}
    return acum


# --- Metadatos de parámetros (etiqueta, tipo, unidad, validador) para la interfaz ---
def _pos(x):    return x > 0
def _no_neg(x): return x >= 0

META_PARAMETROS = {
    "Tf":                     ("Tiempo final de jornada", float, "min", _pos),
    "TI":                     ("Tiempo límite de ingreso", float, "min", _pos),
    "alpha":                  ("Preparación por milanesa (α)", float, "min/mila", _pos),
    "precio_medio_kg":        ("Precio de medio kilo", float, "$", _pos),
    "milanesas_por_medio_kg": ("Milanesas por medio kilo", int, "u", _pos),
    "costo_milanesa":         ("Costo de producir 1 milanesa", float, "$", _no_neg),
    "tolerancia":             ("Tolerancia de espera", float, "min", _pos),
    "stock_inicial":          ("Stock inicial de milanesas", int, "u", _no_neg),
    "cantidad_corridas":      ("Cantidad de corridas", int, "u", _pos),
}
