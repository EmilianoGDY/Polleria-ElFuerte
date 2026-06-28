import random

def correr_experimento(escenario, stock_inicial, cantidad_corridas=1000):
    # --- PARÁMETROS FIJOS ---
    Tf = 270.0
    alpha = 0.5
    precioMilanesa = 1500
    Tol = 15.0
    
    if escenario.upper() == "SABADO":
        FA = 0.5
    else:
        FA = 1.0

    # Variables para acumular los totales de las 1000 corridas
    acum_ganancia = 0.0
    acum_perdida = 0.0
    acum_atendidos = 0
    acum_perdidos_cola = 0
    acum_perdidos_tol = 0
    acum_perdidos_stock = 0
    acum_sobrante = 0

    # --- BUCLE DE REPETICIONES (LAS 1000 JORNADAS) ---
    for _ in range(cantidad_corridas):
        T = 0.0
        TL = 0.0
        stock_actual = stock_inicial
        tiempos_liberacion_activos = []

        # Variables internas de cada día individual
        while True:
            r1 = random.random()
            if r1 < 0.10:     ta_base = 3.0
            elif r1 < 0.30:   ta_base = 5.0
            elif r1 < 0.60:   ta_base = 15.0
            elif r1 < 0.85:   ta_base = 25.0
            else:             ta_base = 32.0
                
            TA = ta_base * FA
            HL = T + TA
            
            if HL > Tf:
                break
                
            tiempos_liberacion_activos = [t for t in tiempos_liberacion_activos if t > HL]
            NC = len(tiempos_liberacion_activos)
            
            r2 = random.random()
            if r2 < 0.0450:    M = 2
            elif r2 < 0.1240:  M = 4
            elif r2 < 0.4050:  M = 6
            elif r2 < 0.4610:  M = 8
            elif r2 < 0.5280:  M = 10
            elif r2 < 0.7750:  M = 12
            elif r2 < 0.8540:  M = 18
            elif r2 < 0.9210:  M = 24
            elif r2 < 0.9770:  M = 36
            else:              M = 48

            TP = M * alpha
            
            # Evaluación de abandono por Cola Larga
            if NC > 3:
                acum_perdida += (M * precioMilanesa)
                acum_perdidos_cola += 1
                T = HL
                continue
                
            HI = max(HL, TL)
            TE = HI - HL
            
            # Evaluación de abandono por Paciencia
            if TE >= Tol:
                acum_perdida += (M * precioMilanesa)
                acum_perdidos_tol += 1
                T = HL
                continue
                
            # Control de stock e inventario operativo
            if stock_actual >= M:
                stock_actual -= M
                HF = HI + TP
                TL = HF
                tiempos_liberacion_activos.append(TL)
                acum_ganancia += (M * precioMilanesa)
                acum_atendidos += 1
            else:
                acum_perdida += (M * precioMilanesa)
                acum_perdidos_stock += 1
                
            T = HL
            
        # Al terminar el día, sumamos el stock sobrante al acumulador
        acum_sobrante += stock_actual

    # --- CÁLCULO DE PROMEDIOS ESTADÍSTICOS ---
    print(f"| {escenario:<9} | {stock_inicial:<13} | ${acum_ganancia/cantidad_corridas:<14,.2f} | ${acum_perdida/cantidad_corridas:<13,.2f} | {acum_sobrante/cantidad_corridas:<14.1f} | {acum_perdidos_stock/cantidad_corridas:<15.1f} | {acum_perdidos_tol/cantidad_corridas:<16.1f} |")

# --- BANCO DE PRUEBAS (EXPERIMENTACIÓN AUTOMÁTICA) ---
print("\n" + "="*112)
print(f"{'ESCENARIO':<11} | {'STOCK INICIAL':<13} | {'GANANCIA PROMEDIO':<17} | {'PÉRDIDA PROMEDIO':<16} | {'SOBRANTE PROM':<14} | {'PERD_STOCK PROM':<15} | {'PERD_PACIENCIA PROM':<19}")
print("="*112)

# EXPERIMENTO 1: Días de semana con diferente stock operativo
correr_experimento(escenario="SEMANA", stock_inicial=100)
correr_experimento(escenario="SEMANA", stock_inicial=130)
correr_experimento(escenario="SEMANA", stock_inicial=160)

print("-" * 112) # Separador visual

# EXPERIMENTO 2: Sábados (afluencia rápida) con diferente stock operativo
correr_experimento(escenario="SABADO", stock_inicial=130)
correr_experimento(escenario="SABADO", stock_inicial=160)
correr_experimento(escenario="SABADO", stock_inicial=190)
print("="*112 + "\n")