import random

def correr_experimento_in_situ(escenario, cantidad_corridas=1000):
    Tf = 270.0
    precioMilanesa = 1500
    Tol = 15.0  # Los clientes se siguen cansando a los 15 min
    
    # NUEVOS PARÁMETROS PARA PRODUCCIÓN IN SITU
    stock_inicial = 0 
    alpha_in_situ = 2.0  # El operario tarda mucho más por unidad (2 minutos)
    tiempo_base = 2.0    # Tiempo base de cobro
    
    if escenario.upper() == "SABADO":
        FA = 0.5
    else:
        FA = 1.0

    acum_ganancia = 0.0
    acum_perdida = 0.0
    acum_atendidos = 0
    acum_perdidos_cola = 0
    acum_perdidos_tol = 0

    for _ in range(cantidad_corridas):
        T = 0.0
        TL = 0.0
        tiempos_liberacion_activos = []

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

            # TIEMPO DE PREPARACIÓN EXTENDIDO (PRODUCCIÓN EN EL MOMENTO)
            TP = tiempo_base + (M * alpha_in_situ)
            
            # Filtro 1: Cola saturada
            if NC > 3:
                acum_perdida += (M * precioMilanesa)
                acum_perdidos_cola += 1
                T = HL
                continue
                
            HI = max(HL, TL)
            TE = HI - HL
            
            # Filtro 2: El cliente no aguanta la espera
            if TE >= Tol:
                acum_perdida += (M * precioMilanesa)
                acum_perdidos_tol += 1
                T = HL
                continue
                
            # Como es in situ, la milanesa siempre se fabrica, el límite es el tiempo del cliente
            HF = HI + TP
            TL = HF
            tiempos_liberacion_activos.append(TL)
            acum_ganancia += (M * precioMilanesa)
            acum_atendidos += 1
                
            T = HL

    print(f"| {escenario:<9} | {stock_inicial:<13} | ${acum_ganancia/cantidad_corridas:<14,.2f} | ${acum_perdida/cantidad_corridas:<13,.2f} | {acum_perdidos_cola/cantidad_corridas:<15.1f} | {acum_perdidos_tol/cantidad_corridas:<16.1f} |")

print("\n" + "="*112)
print(f"{'ESCENARIO':<11} | {'STOCK INICIAL':<13} | {'GANANCIA PROM':<16} | {'PÉRDIDA PROM':<14} | {'PERD_COLA PROM':<15} | {'PERD_PACIENCIA PROM'}")
print("="*112)
correr_experimento_in_situ(escenario="SEMANA")
correr_experimento_in_situ(escenario="SABADO")
print("="*112 + "\n")