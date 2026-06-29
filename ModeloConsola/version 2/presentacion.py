"""
presentacion.py — Presentación por consola (usa rich). Toda la parte visual.

    pip install rich
"""

from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text

from logica import META_PARAMETROS

console = Console()


def _hhmm(min_desde_8):
    if min_desde_8 is None:
        return "—"
    total = int(round(8 * 60 + min_desde_8))
    return f"{total // 60:02d}:{total % 60:02d}"


def _f(x, dec=2):
    return "—" if x is None else f"{x:.{dec}f}"


def banner(texto):
    console.print()
    console.rule(f"[bold cyan]{texto}[/]")


def mostrar_jornada(res, titulo):
    banner(titulo)
    tabla = Table(box=box.ROUNDED, header_style="bold white on grey23")
    for col in ["N", "r1", "TA", "Llegada", "r2", "M", "TP", "NC", "Inicio", "TE", "Fin", "Stock", "Estado"]:
        tabla.add_column(col, justify="left" if col == "Estado" else "right", no_wrap=True)
    for f in res.filas:
        atendido = f["estado"] == "Atendido"
        tabla.add_row(
            str(f["N"]), _f(f["r1"], 7), _f(f["TA"], 1), _hhmm(f["HL"]), _f(f["r2"], 7),
            str(f["M"]), _f(f["TP"], 1), str(f["NC"]), _hhmm(f["HI"]), _f(f["TE"], 1),
            _hhmm(f["HF"]), str(f["stock"]),
            Text(f["estado"], style="green" if atendido else "red"),
        )
    console.print(tabla)
    _resumen(res)


def _resumen(r):
    izq = Text()
    izq.append("Atendidos: ", style="bold"); izq.append(f"{r.atendidos}\n", style="green")
    izq.append("Se retiraron (tolerancia): ", style="bold"); izq.append(f"{r.perdidos_tolerancia}\n", style="red")
    izq.append("Espera promedio: ", style="bold"); izq.append(f"{r.espera_promedio:.1f} min   ")
    izq.append("máxima: ", style="bold"); izq.append(f"{r.espera_maxima:.1f} min\n")
    izq.append("Stock remanente: ", style="bold"); izq.append(f"{r.stock_remanente}")

    der = Text()
    der.append("Milanesas vendidas: ", style="bold"); der.append(f"{r.milanesas_vendidas}\n")
    der.append("Ganancia neta: ", style="bold"); der.append(f"${r.ganancia_neta:,.2f}\n", style="bold green")
    der.append("Costo oportunidad: ", style="bold"); der.append(f"${r.perdida_oportunidad:,.2f}", style="red")

    console.print(Panel(izq, title="[bold]Operación[/]", border_style="cyan"))
    console.print(Panel(der, title="[bold]Economía[/]", border_style="cyan"))


def mostrar_replicas(rep, titulo):
    banner(titulo)
    tabla = Table(box=box.ROUNDED, header_style="bold white on grey23")
    tabla.add_column("Indicador (promedio)", style="bold")
    tabla.add_column("Valor", justify="right")
    import math
    filas = [
        ("Corridas", f"{rep.corridas}"),
        ("Clientes atendidos", f"{math.ceil(rep.atendidos)}"),
        ("Milanesas vendidas", f"{math.ceil(rep.milanesas_vendidas)}"),
        ("Se retiraron (tolerancia)", f"{rep.perdidos_tolerancia:.2f}"),
        ("Espera promedio (min)", f"{rep.espera_promedio:.2f}"),
        ("Espera máxima (min)", f"{rep.espera_maxima:.2f}"),
        ("Stock remanente", f"{rep.stock_remanente:.2f}"),
    ]
    for k, v in filas:
        tabla.add_row(k, v)
    tabla.add_row("Ganancia neta", f"[green]${rep.ganancia_neta:,.2f}[/]")
    tabla.add_row("Costo oportunidad", f"[red]${rep.perdida_oportunidad:,.2f}[/]")
    console.print(tabla)


def mostrar_parametros(params):
    banner("Parámetros de la simulación")
    tabla = Table(box=box.ROUNDED, header_style="bold white on grey23")
    tabla.add_column("#", justify="right", style="dim")
    tabla.add_column("Parámetro")
    tabla.add_column("Valor", justify="right", style="bold cyan")
    tabla.add_column("Unidad", style="dim")
    for i, (clave, (etiqueta, _, unidad, _v)) in enumerate(META_PARAMETROS.items(), 1):
        valor = getattr(params, clave)
        tabla.add_row(str(i), etiqueta, f"{valor:g}" if isinstance(valor, float) else str(valor), unidad)
    console.print(tabla)
    info = Text()
    info.append("precio por milanesa = ", style="bold"); info.append(f"${params.precio_milanesa:,.2f}   ")
    info.append("margen neto = ", style="bold"); info.append(f"${params.margen_milanesa:,.2f}")
    console.print(Panel(info, border_style="dim"))


def mostrar_restricciones(params):
    banner("Restricciones del modelo")
    tabla = Table(box=box.ROUNDED, header_style="bold white on grey23")
    tabla.add_column("Restricción")
    tabla.add_column("Estado", justify="center")
    tabla.add_column("Detalle", style="dim")
    activa = lambda a: Text("● ACTIVA", style="bold green") if a else Text("○ desactivada", style="dim red")
    tabla.add_row("Cierre de jornada (Tf)", activa(True), f"Hasta {params.Tf:g} min (12:30)")
    tabla.add_row("Límite de ingreso (TI)", activa(True), f"Sin ingreso tras {params.TI:g} min (12:20)")
    tabla.add_row("Abandono por tolerancia", activa(params.abandono_por_tolerancia), f"Se retira si TE > {params.tolerancia:g} min")
    console.print(tabla)
    nota = Text("Con tolerancia" if params.abandono_por_tolerancia else "Sin tolerancia",
                style="green" if params.abandono_por_tolerancia else "dim")
    console.print(Panel(nota, border_style="dim"))


def mostrar_menu():
    banner("Pollería 'El Fuerte' — Simulación de colas")
    menu = Text()
    menu.append("  1) ", style="bold cyan"); menu.append("Correr CON stock inicial\n")
    menu.append("  2) ", style="bold cyan"); menu.append("Correr SIN stock inicial\n")
    menu.append("  3) ", style="bold cyan"); menu.append("Parámetros (ver / modificar)\n")
    menu.append("  4) ", style="bold cyan"); menu.append("Restricciones (ver / activar / desactivar)\n")
    menu.append("  5) ", style="bold cyan"); menu.append("Salir\n")
    console.print(Panel(menu, border_style="cyan"))


def info(msg):   console.print(f"[cyan]{msg}[/]")
def exito(msg):  console.print(f"[green]{msg}[/]")
def error(msg):  console.print(f"[bold red]{msg}[/]")


def despedida():
    console.print()
    console.print(Panel(Text("¡Gracias por ocupar la simulación!", justify="center", style="bold green"),
                        border_style="green"))
