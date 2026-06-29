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
        self.assertEqual(mapear(0.00, TABLA_TA), 3.0)
        self.assertEqual(mapear(0.10, TABLA_TA), 5.0)   # límite exacto -> siguiente tramo
        self.assertEqual(mapear(0.99, TABLA_TA), 32.0)

    def test_mapeo_m(self):
        self.assertEqual(mapear(0.0, TABLA_M), 2)
        self.assertEqual(mapear(0.999, TABLA_M), 48)

    def test_r_uno_no_rompe(self):
        self.assertEqual(mapear(1.0, TABLA_TA), 32.0)


class TestFA(unittest.TestCase):
    def test_fa_multiplica_resultado(self):
        # FA multiplica el TA mapeado, no el aleatorio.
        self.assertEqual(mapear(0.50, TABLA_TA) * 0.70, 15.0 * 0.70)


class TestMaxHLTL(unittest.TestCase):
    def test_hi_es_max_y_te_no_negativo(self):
        res = logica.simular_jornada(Parametros(), stock_inicial=0, rng=random.Random(1234))
        for f in res.filas:
            if f["HI"] is not None:
                self.assertGreaterEqual(f["HI"] + 1e-9, f["HL"])
                self.assertGreaterEqual(f["TE"] + 1e-9, 0.0)


class TestStock(unittest.TestCase):
    def test_stock_grande_tp_cero_y_sin_perdidas(self):
        res = logica.simular_jornada(Parametros(), stock_inicial=10_000, rng=random.Random(7))
        self.assertEqual(res.milanesas_no_vendidas, 0)
        for f in res.filas:
            if f["estado"] == "Atendido":
                self.assertEqual(f["TP"], 0.0)

    def test_stock_parcial_prepara_lo_que_falta(self):
        res = logica.simular_jornada(Parametros(alpha=1.5), stock_inicial=5, rng=random.Random(99))
        primera = res.filas[0]
        if primera["estado"] == "Atendido":
            self.assertAlmostEqual(primera["TP"], max(0, primera["M"] - 5) * 1.5)

    def test_sin_stock_prepara_todo(self):
        res = logica.simular_jornada(Parametros(alpha=1.5), stock_inicial=0, rng=random.Random(3))
        for f in res.filas:
            if f["estado"] == "Atendido":
                self.assertAlmostEqual(f["TP"], f["M"] * 1.5)


class TestCorteIngreso(unittest.TestCase):
    def test_nadie_ingresa_despues_de_ti(self):
        p = Parametros()
        res = logica.simular_jornada(p, stock_inicial=0, rng=random.Random(42))
        for f in res.filas:
            self.assertLessEqual(f["HL"], p.TI)


class TestAbandono(unittest.TestCase):
    def test_base_sin_abandono(self):
        rep = logica.correr_replicas(Parametros(abandono_por_tolerancia=False),
                                     stock_inicial=0, corridas=50, rng=random.Random(2024))
        self.assertEqual(rep.perdidos_tolerancia, 0)

    def test_abandono_genera_perdidas(self):
        rep = logica.correr_replicas(Parametros(abandono_por_tolerancia=True, tolerancia=0.5),
                                     stock_inicial=0, corridas=100, rng=random.Random(11))
        self.assertGreater(rep.perdidos_tolerancia, 0)


class TestEconomia(unittest.TestCase):
    def test_ganancia_neta_descuenta_costo(self):
        res = logica.simular_jornada(Parametros(costo_milanesa=700.0), stock_inicial=0, rng=random.Random(8))
        self.assertAlmostEqual(res.ganancia_neta, res.ganancia_bruta - res.costo_total)

    def test_precio_milanesa_derivado(self):
        self.assertAlmostEqual(Parametros(precio_medio_kg=6500, milanesas_por_medio_kg=6).precio_milanesa, 6500 / 6)


class TestValidacionHistorica(unittest.TestCase):
    def test_semana_base_en_rango(self):
        rep = logica.correr_replicas(Parametros(FA=1.0), stock_inicial=0, corridas=300, rng=random.Random(2025))
        self.assertGreater(rep.atendidos, 8)
        self.assertLess(rep.atendidos, 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
