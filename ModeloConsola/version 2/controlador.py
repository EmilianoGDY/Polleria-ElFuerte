"""
controlador.py — Menú por consola. Orquesta: pide datos, llama a logica.py y
manda a dibujar a presentacion.py. No hace cálculos.

    python controlador.py
"""

import sys
import os

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import presentacion as vista
except ImportError:
    print("Falta la librería 'rich'. Instalala con:  pip install rich")
    sys.exit(1)

import logica
from logica import Parametros, META_PARAMETROS


def leer_opcion(prompt, validas):
    while True:
        elegida = input(prompt).strip()
        if elegida in validas:
            return elegida
        vista.error(f"Opción inválida. Elegí una de: {', '.join(sorted(validas))}")


def leer_numero(prompt, tipo, validador, por_defecto):
    while True:
        crudo = input(prompt).strip()
        if crudo == "":
            return por_defecto
        crudo = crudo.replace(",", ".")
        try:
            valor = tipo(float(crudo)) if tipo is int else tipo(crudo)
        except ValueError:
            vista.error(f"Ingresá un número válido ({'entero' if tipo is int else 'decimal'}).")
            continue
        if not validador(valor):
            vista.error("El valor no cumple las restricciones del parámetro.")
            continue
        return valor


def correr(p, stock, titulo_modo):
    res = logica.simular_jornada(p, stock_inicial=stock)
    vista.mostrar_jornada(res, f"{titulo_modo} — jornada de muestra")
    rep = logica.correr_replicas(p, stock_inicial=stock)
    vista.mostrar_replicas(rep, f"{titulo_modo} — promedio de {rep.corridas} corridas")


def menu_parametros(p):
    while True:
        vista.mostrar_parametros(p)
        vista.info("Ingresá el N° de parámetro a modificar, o 0 para volver.")
        claves = list(META_PARAMETROS.keys())
        elegida = leer_opcion("> ", {"0"} | {str(i) for i in range(1, len(claves) + 1)})
        if elegida == "0":
            return
        clave = claves[int(elegida) - 1]
        etiqueta, tipo, unidad, validador = META_PARAMETROS[clave]
        actual = getattr(p, clave)
        nuevo = leer_numero(f"Nuevo valor para '{etiqueta}' [{actual}] (Enter = mantener): ",
                            tipo, validador, actual)
        if clave == "TI" and nuevo > p.Tf:
            vista.error("TI no puede superar a Tf. No se aplicó."); continue
        if clave == "Tf" and nuevo < p.TI:
            vista.error("Tf no puede ser menor a TI. No se aplicó."); continue
        setattr(p, clave, nuevo)
        vista.exito(f"'{etiqueta}' actualizado a {nuevo}.")


def menu_restricciones(p):
    while True:
        vista.mostrar_restricciones(p)
        vista.info("1) prender/apagar abandono por tolerancia   0) volver")
        elegida = leer_opcion("> ", {"0", "1"})
        if elegida == "0":
            return
        p.abandono_por_tolerancia = not p.abandono_por_tolerancia
        vista.exito("Tolerancia " + ("ACTIVADA." if p.abandono_por_tolerancia else "desactivada."))


def main():
    p = Parametros()
    while True:
        vista.mostrar_menu()
        elegida = leer_opcion("Elegí una opción (1-5): ", {"1", "2", "3", "4", "5"})
        if elegida == "1":
            correr(p, p.stock_inicial, f"CON stock (S={p.stock_inicial})")
        elif elegida == "2":
            correr(p, 0, "SIN stock (S=0)")
        elif elegida == "3":
            menu_parametros(p)
        elif elegida == "4":
            menu_restricciones(p)
        elif elegida == "5":
            vista.despedida()
            return


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        vista.despedida()
