"""
test_logica.py — Tests de verificación de la lógica.

    python -m unittest test_logica.py -v
"""

import random
import unittest

import logica
from logica import Parametros, mapear, TABLA_TA, TABLA_M


class TestDistribuciones(unittest.TestCase):
    def test_mapeo_ta(self):
        # Verifica que el aleatorio se traduzca al tiempo entre arribos correcto
        # según la tabla de probabilidad acumulada (extremos y límite de tramo).
        self.assertEqual(mapear(0.00, TABLA_TA), 3.0)
        self.assertEqual(mapear(0.10, TABLA_TA), 5.0)   # límite exacto -> siguiente tramo
        self.assertEqual(mapear(0.99, TABLA_TA), 32.0)

    def test_mapeo_m(self):
        # Verifica el mapeo de la cantidad de milanesas pedidas (M) en sus extremos.
        self.assertEqual(mapear(0.0, TABLA_M), 2)
        self.assertEqual(mapear(0.999, TABLA_M), 48)

    def test_r_uno_no_rompe(self):
        # Caso borde: un aleatorio = 1.0 no debe salirse de la tabla; cae en el último tramo.
        self.assertEqual(mapear(1.0, TABLA_TA), 32.0)


class TestMaxHLTL(unittest.TestCase):
    def test_hi_es_max_y_te_no_negativo(self):
        # Coherencia temporal: el inicio de atención (HI) nunca es anterior a la
        # llegada del cliente (HL), y el tiempo de espera (TE) jamás es negativo.
        res = logica.simular_jornada(Parametros(), stock_inicial=0, rng=random.Random(1234))
        for f in res.filas:
            if f["HI"] is not None:
                self.assertGreaterEqual(f["HI"] + 1e-9, f["HL"])
                self.assertGreaterEqual(f["TE"] + 1e-9, 0.0)


class TestStock(unittest.TestCase):
    def test_stock_grande_tp_cero_y_sin_perdidas(self):
        # Con stock prácticamente infinito no hace falta preparar (TP=0) y no quedan
        # milanesas sin vender: valida el camino "todo se sirve desde stock".
        res = logica.simular_jornada(Parametros(), stock_inicial=10_000, rng=random.Random(7))
        self.assertEqual(res.milanesas_no_vendidas, 0)
        for f in res.filas:
            if f["estado"] == "Atendido":
                self.assertEqual(f["TP"], 0.0)

    def test_stock_parcial_prepara_lo_que_falta(self):
        # Con stock parcial solo se prepara la diferencia faltante (M - stock):
        # el tiempo de preparación (TP) debe reflejar únicamente lo que no había.
        res = logica.simular_jornada(Parametros(alpha=1.5), stock_inicial=5, rng=random.Random(99))
        primera = res.filas[0]
        if primera["estado"] == "Atendido":
            self.assertAlmostEqual(primera["TP"], max(0, primera["M"] - 5) * 1.5)

    def test_sin_stock_prepara_todo(self):
        # Sin stock inicial se prepara el pedido completo: TP = M * tiempo unitario (alpha).
        res = logica.simular_jornada(Parametros(alpha=1.5), stock_inicial=0, rng=random.Random(3))
        for f in res.filas:
            if f["estado"] == "Atendido":
                self.assertAlmostEqual(f["TP"], f["M"] * 1.5)


class TestCorteIngreso(unittest.TestCase):
    def test_nadie_ingresa_despues_de_ti(self):
        # Regla de cierre: ningún cliente llega (HL) después del horario de corte TI.
        p = Parametros()
        res = logica.simular_jornada(p, stock_inicial=0, rng=random.Random(42))
        for f in res.filas:
            self.assertLessEqual(f["HL"], p.TI)


class TestAbandono(unittest.TestCase):
    def test_base_sin_abandono(self):
        # Con el abandono desactivado nadie se va por esperar de más: 0 pérdidas por tolerancia.
        rep = logica.correr_replicas(Parametros(abandono_por_tolerancia=False),
                                     stock_inicial=0, corridas=50, rng=random.Random(2024))
        self.assertEqual(rep.perdidos_tolerancia, 0)

    def test_abandono_genera_perdidas(self):
        # Con abandono activo y tolerancia muy baja, sí deben aparecer clientes perdidos:
        # confirma que el mecanismo de abandono efectivamente actúa.
        rep = logica.correr_replicas(Parametros(abandono_por_tolerancia=True, tolerancia=0.5),
                                     stock_inicial=0, corridas=100, rng=random.Random(11))
        self.assertGreater(rep.perdidos_tolerancia, 0)


class TestEconomia(unittest.TestCase):
    def test_ganancia_neta_descuenta_costo(self):
        # La ganancia neta es el ingreso menos los tres costos: oportunidad (ventas
        # perdidas), materia prima de lo vendido y materia prima del sobrante.
        res = logica.simular_jornada(Parametros(costo_milanesa=700.0, abandono_por_tolerancia=True,
                                                tolerancia=5.0), stock_inicial=20, rng=random.Random(8))
        self.assertAlmostEqual(
            res.ganancia_neta,
            res.ganancia_bruta - res.perdida_oportunidad - res.costo_total - res.desperdicio)

    def test_precio_milanesa_derivado(self):
        # El precio por milanesa se deriva del precio del medio kilo dividido la cantidad por medio kilo.
        self.assertAlmostEqual(Parametros(precio_medio_kg=6500, milanesas_por_medio_kg=6).precio_milanesa, 6500 / 6)


class TestValidacionHistorica(unittest.TestCase):
    def test_semana_base_en_rango(self):
        # Validación contra la realidad: con el escenario base el promedio de clientes
        # atendidos debe caer en un rango razonable observado históricamente.
        rep = logica.correr_replicas(Parametros(), stock_inicial=0, corridas=300, rng=random.Random(2025))
        self.assertGreater(rep.atendidos, 8)
        self.assertLess(rep.atendidos, 20)


class TestIntervalosConfianza(unittest.TestCase):
    def test_estadistica_basica(self):
        # Sobre una muestra conocida: media correcta, desvío muestral (N-1) e
        # intervalo simétrico (media ± semiancho) con semiancho positivo.
        est = logica.estadistica([10, 12, 14, 16, 18])
        self.assertAlmostEqual(est.media, 14.0)
        self.assertAlmostEqual(est.desvio, 3.1622776, places=5)  # stdev muestral
        self.assertGreater(est.semiancho, 0)
        self.assertAlmostEqual(est.ic_bajo, est.media - est.semiancho)
        self.assertAlmostEqual(est.ic_alto, est.media + est.semiancho)

    def test_t_grande_usa_normal(self):
        # Muestra grande (df >= 30, o sea N >= 31) -> aproximación normal z = 1.96.
        self.assertEqual(logica.t_critico_95(200), 1.96)
        # Muestra chica -> t de Student de la tabla.
        self.assertEqual(logica.t_critico_95(5), 2.776)    # df = 4
        self.assertEqual(logica.t_critico_95(30), 2.045)   # df = 29 (aún t)

    def test_replicas_reportan_intervalos(self):
        # correr_replicas debe entregar un IC por cada variable de respuesta,
        # con la media dentro del intervalo y coherente con el promedio plano.
        rep = logica.correr_replicas(Parametros(), stock_inicial=40,
                                     corridas=120, rng=random.Random(77))
        for var in logica.VARIABLES_IC:
            est = rep.intervalos[var]
            self.assertEqual(est.n, 120)
            self.assertLessEqual(est.ic_bajo, est.media)
            self.assertLessEqual(est.media, est.ic_alto)
        # La media del IC de atendidos coincide con el promedio plano reportado.
        self.assertAlmostEqual(rep.intervalos["atendidos"].media, rep.atendidos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
